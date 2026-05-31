"""Settlement (3.2): grade signals once their fixture has kicked off.

Two-phase, idempotent:
  - At kickoff: grade CLV from our own Pinnacle snapshots (closing sharp line) → status
    'expired' (no longer live, result pending).
  - Once the fixture has a final score: grade result + P&L → status 'settled'.

Re-running is safe (the grade row is upserted and status never moves backwards).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.core import Fixture, League, Market
from app.models.odds import OddsSnapshot
from app.models.signals import Signal, SignalGrade
from app.shared.db import get_sessionmaker
from app.shared.grading import clv_beat, compute_result, pnl_units
from app.shared.metrics import emit

log = logging.getLogger("settle")


async def _closing_sharp_odds(session, fixture_id, market_id, selection, sharp_book, kickoff):
    """Last sharp (Pinnacle) price for this selection at/before kickoff = the closing line."""
    return (await session.execute(
        select(OddsSnapshot.decimal_odds)
        .where(
            OddsSnapshot.fixture_id == fixture_id,
            OddsSnapshot.book == sharp_book,
            OddsSnapshot.market_id == market_id,
            OddsSnapshot.selection == selection,
            OddsSnapshot.ts <= kickoff,
        )
        .order_by(OddsSnapshot.ts.desc())
        .limit(1)
    )).scalar()


async def settle_once() -> dict:
    now = datetime.now(timezone.utc)
    Session = get_sessionmaker()
    stats = {"graded": 0, "clv_beats": 0, "results": 0}

    async with Session() as session:
        rows = (await session.execute(
            select(Signal, Fixture, Market, League)
            .join(Fixture, Signal.fixture_id == Fixture.id)
            .join(Market, Signal.market_id == Market.id)
            .join(League, Fixture.league_id == League.id)
            .where(Signal.status.in_(["live", "expired"]), Fixture.kickoff_utc <= now)
        )).all()

        for sig, fx, market, league in rows:
            closing = beat = result = pnl = None
            # CLV only applies to single-selection EV bets (arb is multi-book).
            if sig.kind == "ev":
                closing = await _closing_sharp_odds(
                    session, fx.id, sig.market_id, sig.selection,
                    league.sharp_ref_book, fx.kickoff_utc,
                )
                beat = clv_beat(sig.offered_odds, closing)
                if fx.home_score is not None and fx.away_score is not None:
                    result = compute_result(fx.home_score, fx.away_score,
                                            market.type, market.line, sig.selection)
                    pnl = pnl_units(result, sig.offered_odds)

            await session.execute(
                pg_insert(SignalGrade)
                .values(signal_id=sig.id, closing_odds=closing, beat_clv=beat,
                        result=result, pnl_units=pnl)
                .on_conflict_do_update(
                    index_elements=["signal_id"],
                    set_={"closing_odds": closing, "beat_clv": beat,
                          "result": result, "pnl_units": pnl},
                )
            )
            sig.status = "settled" if result is not None else "expired"
            stats["graded"] += 1
            if beat:
                stats["clv_beats"] += 1
            if result is not None:
                stats["results"] += 1

        await session.commit()

    emit("settle.pass", **stats)
    return stats
