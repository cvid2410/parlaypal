"""Detection consumer (1.4).

For one market that just moved: read every book's prices from Redis hot state, devig the
sharp reference (Pinnacle) into a fair probability per selection, then look for +EV soft
prices and cross-book arbitrage. Accepted opportunities become `signals` rows, deduped so
a flapping line can't spam and we only re-alert when the edge bucket improves
(NON-NEGOTIABLE #3).
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from sqlalchemy import select

from app.config import settings
from app.models.core import Fixture, League, Market
from app.models.signals import Signal
from app.services.cache import get_redis
from app.shared.db import get_sessionmaker
from app.shared.detect_core import _bucket as _core_bucket
from app.shared.detect_core import _dedup_hash, find_opportunities
from app.shared.metrics import emit

log = logging.getLogger("detect")

# Re-exported for the other signal-kind workers (middles, boosts) that share the same
# flap-dedup primitives. `_dedup_hash` is the pure core hash; `_bucket` binds it to config.
__all__ = ["detect_market", "_alert_allowed", "_bucket", "_dedup_hash"]


def _hot_key(fixture_id: str, market_id: int) -> str:
    return f"odds:{fixture_id}:{market_id}"


def _bucket(value: float) -> int:
    """Settings-bound edge bucket (shared by middles/boosts dedup)."""
    return _core_bucket(value, settings.edge_bucket_pct)


async def _alert_allowed(r, scope: str, bucket: int) -> bool:
    """True only on first sight or a strictly improved bucket (re-alert on improvement,
    dedup flapping). `scope` uniquely identifies the opportunity sans edge magnitude."""
    best_key = f"sigbest:{scope}"
    cur = await r.get(best_key)
    if cur is not None and bucket <= int(cur):
        return False
    await r.set(best_key, bucket, ex=settings.signal_ttl_seconds)
    return True


def _validity_key(kind: str, selection: str, book: str) -> tuple:
    """Identity for 'is this exact edge still present'. Arb/middle are market-level (one per
    market, defined by their legs); single bets (ev/value) are keyed by selection + book."""
    if kind in ("arb", "middle"):
        return (kind,)
    return (kind, selection, book)


async def detect_market(ctx: dict, fixture_id: str, market_id: int) -> dict:
    started = time.perf_counter()
    r = get_redis()
    Session = get_sessionmaker()
    stats = {"ev": 0, "arb": 0, "value": 0, "expired": 0}

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

        # Read hot state → {book: {selection: decimal}}
        flat = await r.hgetall(_hot_key(fixture_id, market_id))
        by_book: dict[str, dict[str, float]] = defaultdict(dict)
        for field, val in flat.items():
            book, _, sel = field.partition(":")
            by_book[book][sel] = float(val)

        # Pure detection (shared with the backtest replay). The flap-dedup below is the only
        # stateful gate; everything math lives in detect_core.find_opportunities.
        opps = find_opportunities(
            fixture_id,
            market_id,
            by_book,
            is_soft=league.is_soft,
            sharp_ref_book=league.sharp_ref_book,
            min_edge_pct=settings.min_edge_pct,
            kelly_fraction=settings.kelly_fraction,
            edge_bucket_pct=settings.edge_bucket_pct,
            market_type=market.type,
            max_offered_odds=settings.max_offered_odds,
            max_edge_pct=settings.max_edge_pct,
            devig_method=settings.devig_method,
            min_consensus_books=settings.min_consensus_books,
        )

        # Event-driven invalidation (real-time-ish removal, like OddsJam): a live signal on this
        # market whose edge is no longer in the current opportunities is no longer true - the line
        # moved and the price/edge is gone. Expire it now instead of letting it sit out the
        # 30-min TTL. Arbs get pulled the moment a leg moves; single bets when the offering book's
        # price falls below the edge threshold. (Middles are invalidated by detect_middles.)
        valid_keys = {_validity_key(o.kind, o.selection, o.book) for o in opps}
        live_now = (
            (
                await session.execute(
                    select(Signal).where(
                        Signal.fixture_id == fixture_id,
                        Signal.market_id == market_id,
                        Signal.status == "live",
                        Signal.kind.in_(("ev", "value", "arb")),
                    )
                )
            )
            .scalars()
            .all()
        )
        for sig in live_now:
            if _validity_key(sig.kind, sig.selection, sig.book) not in valid_keys:
                sig.status = "expired"
                stats["expired"] += 1

        new_signals: list[Signal] = []
        for opp in opps:
            if not await _alert_allowed(r, opp.scope, opp.bucket):
                continue
            new_signals.append(
                Signal(
                    fixture_id=fixture_id,
                    market_id=market_id,
                    selection=opp.selection,
                    book=opp.book,
                    kind=opp.kind,
                    offered_odds=opp.offered_odds,
                    fair_prob=opp.fair_prob,
                    edge_pct=opp.edge_pct,
                    kelly_frac=opp.kelly_frac,
                    ttl_sec=settings.signal_ttl_seconds,
                    dedup_hash=opp.dedup_hash,
                    status="live",
                    meta=opp.meta,
                )
            )
            stats[opp.kind] += 1

        arq = ctx.get("redis") if isinstance(ctx, dict) else None
        if new_signals:
            session.add_all(new_signals)
        # Commit if we created new signals OR expired stale ones (the invalidation above).
        if new_signals or stats["expired"]:
            await session.commit()
        for sig in new_signals:
            emit(
                "signal.accepted",
                signal_id=sig.id,
                kind=sig.kind,
                edge_pct=round(sig.edge_pct, 3),
            )
            if arq is not None:
                await arq.enqueue_job("route_signal", sig.id, _job_id=f"route:{sig.id}")

        # A totals move can create a cross-market middle - hand off to the middle detector.
        if market.type == "total" and arq is not None:
            await arq.enqueue_job("detect_middles", fixture_id, _job_id=f"middles:{fixture_id}")

    lag_ms = (time.perf_counter() - started) * 1000
    emit(
        "detect.market",
        fixture_id=fixture_id,
        market_id=market_id,
        ev=stats["ev"],
        arb=stats["arb"],
        value=stats["value"],
        expired=stats["expired"],
        lag_ms=round(lag_ms, 1),
    )
    return stats
