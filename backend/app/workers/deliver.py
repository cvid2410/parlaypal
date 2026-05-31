"""Delivery job (2.5). Idempotent per (signal, user, channel) via `alerts_sent`
(NON-NEGOTIABLE #4): claim-first, so a retried/duplicate job never double-sends.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.core import Fixture, League, Market, Team
from app.models.signals import Signal
from app.models.users import AlertSent
from app.shared.copy import SignalCopyContext, explain
from app.shared.db import get_sessionmaker
from app.shared.metrics import emit
from app.workers.channels import get_channel


async def _build_context(session, signal_id: int) -> SignalCopyContext | None:
    sig = (await session.execute(select(Signal).where(Signal.id == signal_id))).scalar_one_or_none()
    if sig is None:
        return None
    fixture = (await session.execute(select(Fixture).where(Fixture.id == sig.fixture_id))).scalar_one()
    market = (await session.execute(select(Market).where(Market.id == sig.market_id))).scalar_one()
    league = (await session.execute(select(League).where(League.id == fixture.league_id))).scalar_one()
    home = (await session.execute(select(Team).where(Team.id == fixture.home_id))).scalar_one()
    away = (await session.execute(select(Team).where(Team.id == fixture.away_id))).scalar_one()

    legs = []
    if sig.kind == "arb" and sig.meta and "legs" in sig.meta:
        legs = [
            {"selection": sel, "book": v["book"], "decimal": v["odds"],
             "stake_frac": v["stake_frac"]}
            for sel, v in sig.meta["legs"].items()
        ]
    return SignalCopyContext(
        kind=sig.kind, dedup_hash=sig.dedup_hash, league_name=league.name,
        home=home.name, away=away.name, market_type=market.type, line=market.line,
        selection=sig.selection, book=sig.book, offered_decimal=sig.offered_odds,
        fair_prob=sig.fair_prob, edge_pct=sig.edge_pct, kelly_frac=sig.kelly_frac, legs=legs,
    )


async def deliver(ctx: dict, signal_id: int, user_id: int, channel: str) -> bool:
    Session = get_sessionmaker()
    async with Session() as session:
        # Claim first: insert the alerts_sent row; a conflict means already delivered.
        claim = (
            pg_insert(AlertSent)
            .values(signal_id=signal_id, user_id=user_id, channel=channel)
            .on_conflict_do_nothing(constraint="pk_alerts_sent")
        )
        res = await session.execute(claim)
        await session.commit()
        if res.rowcount == 0:
            emit("deliver.duplicate", signal_id=signal_id, user_id=user_id, channel=channel)
            return False

        copy_ctx = await _build_context(session, signal_id)

    if copy_ctx is None:
        return False
    ch = get_channel(channel)
    if ch is None:
        emit("deliver.unknown_channel", channel=channel)
        return False
    copy = explain(copy_ctx)
    return await ch.send(user_id, copy)
