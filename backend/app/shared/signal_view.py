"""Build a render-ready context from a persisted Signal (shared by delivery + the API)."""
from __future__ import annotations

from sqlalchemy import select

from app.models.core import Fixture, League, Market, Team
from app.models.signals import Signal
from app.shared.copy import SignalCopyContext


async def signal_context(session, sig: Signal) -> SignalCopyContext | None:
    fixture = (await session.execute(
        select(Fixture).where(Fixture.id == sig.fixture_id)
    )).scalar_one_or_none()
    if fixture is None:
        return None
    market = (await session.execute(
        select(Market).where(Market.id == sig.market_id)
    )).scalar_one()
    league = (await session.execute(
        select(League).where(League.id == fixture.league_id)
    )).scalar_one()
    home = (await session.execute(select(Team).where(Team.id == fixture.home_id))).scalar_one()
    away = (await session.execute(select(Team).where(Team.id == fixture.away_id))).scalar_one()

    legs, window = [], None
    if sig.kind in ("arb", "middle") and sig.meta and "legs" in sig.meta:
        legs = [
            {"selection": s, "book": v["book"], "decimal": v["odds"],
             "stake_frac": v["stake_frac"], "line": v.get("line")}
            for s, v in sig.meta["legs"].items()
        ]
        window = sig.meta.get("window")
    return SignalCopyContext(
        kind=sig.kind, dedup_hash=sig.dedup_hash, league_name=league.name,
        country=league.country, home=home.name, away=away.name,
        home_logo=home.logo, away_logo=away.logo, market_type=market.type,
        line=market.line, selection=sig.selection, book=sig.book,
        offered_decimal=sig.offered_odds, fair_prob=sig.fair_prob,
        edge_pct=sig.edge_pct, kelly_frac=sig.kelly_frac, legs=legs, window=window,
    )
