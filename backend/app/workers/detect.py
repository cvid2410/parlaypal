"""Detection consumer (1.4).

For one market that just moved: read every book's prices from Redis hot state, devig the
sharp reference (Pinnacle) into a fair probability per selection, then look for +EV soft
prices and cross-book arbitrage. Accepted opportunities become `signals` rows, deduped so
a flapping line can't spam and we only re-alert when the edge bucket improves
(NON-NEGOTIABLE #3).
"""
from __future__ import annotations

import hashlib
import logging
import time
from collections import defaultdict

from sqlalchemy import select

from app.config import settings
from app.models.core import Fixture, League, Market
from app.models.signals import Signal
from app.services.cache import get_redis
from app.shared.db import get_sessionmaker
from app.shared.math import devig_multi, ev_pct, find_arb_multi, kelly
from app.shared.metrics import emit

log = logging.getLogger("detect")


def _hot_key(fixture_id: str, market_id: int) -> str:
    return f"odds:{fixture_id}:{market_id}"


def _bucket(value: float) -> int:
    return int(value // settings.edge_bucket_pct)


async def _alert_allowed(r, scope: str, bucket: int) -> bool:
    """True only on first sight or a strictly improved bucket (re-alert on improvement,
    dedup flapping). `scope` uniquely identifies the opportunity sans edge magnitude."""
    best_key = f"sigbest:{scope}"
    cur = await r.get(best_key)
    if cur is not None and bucket <= int(cur):
        return False
    await r.set(best_key, bucket, ex=settings.signal_ttl_seconds)
    return True


def _dedup_hash(*parts) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()


async def detect_market(ctx: dict, fixture_id: str, market_id: int) -> dict:
    started = time.perf_counter()
    r = get_redis()
    Session = get_sessionmaker()
    stats = {"ev": 0, "arb": 0}

    async with Session() as session:
        market = (
            await session.execute(select(Market).where(Market.id == market_id))
        ).scalar_one_or_none()
        fixture = (
            await session.execute(select(Fixture).where(Fixture.id == fixture_id))
        ).scalar_one_or_none()
        if market is None or fixture is None:
            return stats
        league = (
            await session.execute(select(League).where(League.id == fixture.league_id))
        ).scalar_one()

        # Sharp leagues carry no edge — ingested for Scores only, never signalled.
        if not league.is_soft:
            return stats

        # Read hot state → {book: {selection: decimal}}
        flat = await r.hgetall(_hot_key(fixture_id, market_id))
        by_book: dict[str, dict[str, float]] = defaultdict(dict)
        for field, val in flat.items():
            book, _, sel = field.partition(":")
            by_book[book][sel] = float(val)

        sharp = by_book.get(league.sharp_ref_book)
        new_signals: list[Signal] = []

        # ---- +EV vs the sharp fair line ----
        if sharp and len(sharp) >= 2:
            fair = devig_multi(sharp)
            for book, sels in by_book.items():
                if book == league.sharp_ref_book:
                    continue
                for sel, dec in sels.items():
                    p = fair.get(sel)
                    if p is None:
                        continue
                    edge = ev_pct(dec, p)
                    if edge < settings.min_edge_pct:
                        continue
                    scope = f"ev:{fixture_id}:{market_id}:{sel}:{book}"
                    if not await _alert_allowed(r, scope, _bucket(edge)):
                        continue
                    new_signals.append(
                        Signal(
                            fixture_id=fixture_id,
                            market_id=market_id,
                            selection=sel,
                            book=book,
                            kind="ev",
                            offered_odds=dec,
                            fair_prob=p,
                            edge_pct=edge,
                            kelly_frac=kelly(p, dec, settings.kelly_fraction),
                            ttl_sec=settings.signal_ttl_seconds,
                            dedup_hash=_dedup_hash(
                                fixture_id, market_id, sel, book, _bucket(edge)
                            ),
                            status="live",
                            meta={"sharp_book": league.sharp_ref_book},
                        )
                    )
                    stats["ev"] += 1

        # ---- cross-book arbitrage (best price per selection across all books) ----
        best: dict[str, tuple[str, float]] = {}
        for book, sels in by_book.items():
            for sel, dec in sels.items():
                if sel not in best or dec > best[sel][1]:
                    best[sel] = (book, dec)
        if len(best) >= 2:
            arb = find_arb_multi({sel: dec for sel, (_, dec) in best.items()})
            if arb is not None:
                profit = arb["profit_pct"]
                scope = f"arb:{fixture_id}:{market_id}"
                if await _alert_allowed(r, scope, _bucket(profit)):
                    legs = {
                        sel: {"book": bk, "odds": dec, "stake_frac": arb["stake_fracs"][sel]}
                        for sel, (bk, dec) in best.items()
                    }
                    new_signals.append(
                        Signal(
                            fixture_id=fixture_id,
                            market_id=market_id,
                            selection="+".join(sorted(best)),
                            book="multi",
                            kind="arb",
                            offered_odds=0.0,
                            fair_prob=0.0,
                            edge_pct=profit,
                            kelly_frac=0.0,
                            ttl_sec=settings.signal_ttl_seconds,
                            dedup_hash=_dedup_hash(fixture_id, market_id, "arb", _bucket(profit)),
                            status="live",
                            meta={"legs": legs},
                        )
                    )
                    stats["arb"] += 1

        if new_signals:
            session.add_all(new_signals)
            await session.commit()
            arq = ctx.get("redis") if isinstance(ctx, dict) else None
            for sig in new_signals:
                emit("signal.accepted", signal_id=sig.id, kind=sig.kind,
                     edge_pct=round(sig.edge_pct, 3))
                if arq is not None:
                    await arq.enqueue_job("route_signal", sig.id, _job_id=f"route:{sig.id}")

    lag_ms = (time.perf_counter() - started) * 1000
    emit("detect.market", fixture_id=fixture_id, market_id=market_id,
         ev=stats["ev"], arb=stats["arb"], lag_ms=round(lag_ms, 1))
    return stats
