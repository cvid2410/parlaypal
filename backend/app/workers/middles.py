"""Middle detector (per-fixture, cross-market).

A middle lives across two *different* totals markets (Over at a low line, Under at a high
line), so it can't be found by the per-market `detect_market`. This reads all of a fixture's
totals from Redis hot state, finds the best Over/Under per line, and emits a `middle` signal
where a gap leaves a worthwhile shot at winning both. Mechanical → runs on every league.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.config import settings
from app.models.core import Market
from app.models.signals import Signal
from app.services.cache import get_redis
from app.shared.db import get_sessionmaker
from app.shared.math import find_middle
from app.shared.metrics import emit
from app.workers.detect import _alert_allowed, _bucket, _dedup_hash

log = logging.getLogger("middles")


async def detect_middles(ctx: dict, fixture_id: str) -> dict:
    r = get_redis()
    Session = get_sessionmaker()
    stats = {"middle": 0}

    raw_mids = await r.smembers(f"fxtotals:{fixture_id}")
    mids = [int(m) for m in raw_mids]
    if len(mids) < 2:
        return stats

    async with Session() as session:
        markets = (await session.execute(select(Market).where(Market.id.in_(mids)))).scalars().all()
        line_of = {m.id: m.line for m in markets if m.type == "total" and m.line is not None}

        # best Over / Under decimal per line, across books
        best_over: dict[float, tuple[str, float]] = {}
        best_under: dict[float, tuple[str, float]] = {}
        for mid in mids:
            line = line_of.get(mid)
            if line is None:
                continue
            flat = await r.hgetall(f"odds:{fixture_id}:{mid}")
            for field, val in flat.items():
                book, _, sel = field.partition(":")
                dec = float(val)
                target = best_over if sel == "over" else best_under if sel == "under" else None
                if target is None:
                    continue
                if line not in target or dec > target[line][1]:
                    target[line] = (book, dec)

        new_signals: list[Signal] = []
        for lo, (ob, od) in best_over.items():
            for lu, (ub, ud) in best_under.items():
                if lo >= lu:
                    continue
                m = find_middle(od, lo, ud, lu)
                if m is None or m["hold"] > settings.middle_max_hold:
                    continue
                scope = f"middle:{fixture_id}:{lo}:{lu}"
                bucket = _bucket(m["middle_pnl_pct"])
                if not await _alert_allowed(r, scope, bucket):
                    continue
                over_mid = next(mid for mid, ln in line_of.items() if ln == lo)
                legs = {
                    "over": {
                        "book": ob,
                        "odds": od,
                        "line": lo,
                        "stake_frac": m["stake_over_frac"],
                    },
                    "under": {
                        "book": ub,
                        "odds": ud,
                        "line": lu,
                        "stake_frac": m["stake_under_frac"],
                    },
                }
                new_signals.append(
                    Signal(
                        fixture_id=fixture_id,
                        market_id=over_mid,
                        selection=f"O{lo}/U{lu}",
                        book="multi",
                        kind="middle",
                        offered_odds=0.0,
                        fair_prob=0.0,
                        edge_pct=m["middle_pnl_pct"],
                        kelly_frac=0.0,
                        ttl_sec=settings.signal_ttl_seconds,
                        dedup_hash=_dedup_hash(fixture_id, "middle", lo, lu, bucket),
                        status="live",
                        meta={
                            "legs": legs,
                            "window": m["window"],
                            "miss_pnl_pct": round(m["miss_pnl_pct"], 2),
                            "hold": round(m["hold"], 4),
                        },
                    )
                )
                stats["middle"] += 1

        if new_signals:
            session.add_all(new_signals)
            await session.commit()
            arq = ctx.get("redis") if isinstance(ctx, dict) else None
            for sig in new_signals:
                emit(
                    "signal.accepted",
                    signal_id=sig.id,
                    kind="middle",
                    edge_pct=round(sig.edge_pct, 3),
                )
                if arq is not None:
                    await arq.enqueue_job("route_signal", sig.id, _job_id=f"route:{sig.id}")

    emit("detect.middles", fixture_id=fixture_id, middle=stats["middle"])
    return stats
