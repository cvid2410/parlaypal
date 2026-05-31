"""Odds boosts / promos (kind='promo').

A boost is a book-subsidized price that can be genuinely +EV even on a sharp market. The
Odds API doesn't carry boosts, so there's no auto-source yet — this is the path + a manual
injection entry point (a feed or admin UI plugs in here later). Given a boosted price we
compute the fair probability from current hot state (devig Pinnacle, else book consensus)
and emit a promo signal when it's +EV.
"""
from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy import select

from app.config import settings
from app.models.core import Fixture, League, Market
from app.models.signals import Signal
from app.services.cache import get_redis
from app.shared.db import get_sessionmaker
from app.shared.math import american_to_decimal, devig, ev_pct, kelly
from app.shared.metrics import emit
from app.workers.detect import _alert_allowed, _bucket, _dedup_hash

log = logging.getLogger("boosts")


def _fair_from_hotstate(by_book: dict[str, dict[str, float]], sharp_book: str,
                        method: str) -> dict[str, float]:
    """Fair prob per selection: devig the sharp reference if present, else the book consensus.

    Uses the league's `sharp_ref_book` and the configured devig `method` — the SAME fair line
    EV/arb and the CLV gate use — so a promo's edge isn't measured against a different (or
    absent) reference than everything else in the pipeline.
    """
    sharp = by_book.get(sharp_book)
    if sharp and len(sharp) >= 2:
        return devig(sharp, method)
    # Consensus fallback: the (still vigged) consensus decimal per selection — the harmonic
    # mean of decimals == 1 / mean implied prob — then devig with the same method, rather than
    # hand-rolling a proportional normalisation that silently pins the method to multiplicative.
    dec_by_sel: dict[str, list[float]] = defaultdict(list)
    for sels in by_book.values():
        for sel, dec in sels.items():
            if dec > 1:
                dec_by_sel[sel].append(dec)
    if len(dec_by_sel) < 2:
        return {}
    consensus = {sel: len(v) / sum(1 / d for d in v) for sel, v in dec_by_sel.items()}
    return devig(consensus, method)


async def inject_boost(fixture_id: str, market_type: str, line: float | None,
                      selection: str, book: str, boosted_american: float,
                      ctx: dict | None = None) -> dict:
    r = get_redis()
    Session = get_sessionmaker()
    async with Session() as session:
        fx = (await session.execute(
            select(Fixture).where(Fixture.id == fixture_id)
        )).scalar_one_or_none()
        if fx is None:
            return {"emitted": False, "error": "fixture not found"}
        sharp_book = (await session.execute(
            select(League.sharp_ref_book).where(League.id == fx.league_id)
        )).scalar_one()

        q = select(Market.id).where(Market.type == market_type, Market.period == "FT")
        q = q.where(Market.line.is_(None) if line is None else Market.line == line)
        mid = (await session.execute(q)).scalar()
        if mid is None:
            return {"emitted": False, "error": "market not found"}

        by_book: dict[str, dict[str, float]] = defaultdict(dict)
        for field, val in (await r.hgetall(f"odds:{fixture_id}:{mid}")).items():
            b, _, sel = field.partition(":")
            by_book[b][sel] = float(val)
        fair = _fair_from_hotstate(by_book, sharp_book, settings.devig_method)
        if selection not in fair:
            return {"emitted": False, "error": "no fair reference for selection"}

        p = fair[selection]
        dec = american_to_decimal(boosted_american)
        edge = ev_pct(dec, p)
        if edge <= 0:
            return {"emitted": False, "edge_pct": round(edge, 2)}  # junk boost, skip

        bucket = _bucket(edge)
        scope = f"promo:{fixture_id}:{mid}:{selection}:{book}"
        if not await _alert_allowed(r, scope, bucket):
            return {"emitted": False, "edge_pct": round(edge, 2), "dedup": True}

        sig = Signal(
            fixture_id=fixture_id, market_id=mid, selection=selection, book=book,
            kind="promo", offered_odds=dec, fair_prob=p, edge_pct=edge,
            kelly_frac=kelly(p, dec, settings.kelly_fraction),
            ttl_sec=settings.signal_ttl_seconds,
            dedup_hash=_dedup_hash(fixture_id, mid, selection, book, "promo", bucket),
            status="live", meta={"boost": True, "boosted_american": boosted_american},
        )
        session.add(sig)
        await session.commit()
        emit("signal.accepted", signal_id=sig.id, kind="promo", edge_pct=round(edge, 3))
        arq = ctx.get("redis") if isinstance(ctx, dict) else None
        if arq is not None:
            await arq.enqueue_job("route_signal", sig.id, _job_id=f"route:{sig.id}")
        return {"emitted": True, "signal_id": sig.id, "edge_pct": round(edge, 2)}
