"""Settlement (3.2): grade signals once their fixture has kicked off.

Two-phase, idempotent:
  - At kickoff: grade CLV from our own Pinnacle snapshots (closing sharp line) → status
    'expired' (no longer live, result pending).
  - Once the fixture has a final score: grade result + P&L → status 'settled'.

Re-running is safe (the grade row is upserted and status never moves backwards).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.models.core import Fixture, League, Market
from app.models.odds import OddsSnapshot
from app.models.signals import Signal, SignalGrade
from app.shared.db import get_sessionmaker
from app.shared.detect_core import _complete
from app.shared.grading import clv_beat, compute_result, pnl_units
from app.shared.math import devig
from app.shared.metrics import emit

log = logging.getLogger("settle")


async def _closing_sharp_fair_decimal(
    session, fixture_id, market_id, selection, sharp_book, kickoff, market_type
):
    """The NO-VIG closing fair decimal for `selection`.

    CLV must be measured against the sharp's true closing probability, not its raw posted
    odds - the vig makes raw odds shorter than fair, so 'offered > raw closing' is a
    structurally easy bar that inflates beat-CLV. We pull every sharp selection's last price
    at/before kickoff, devig the whole market, and return 1/fair_prob for our selection.

    Requires the FULL selection set for the market type (same `_complete` rule detection
    uses) - devigging an incomplete market (e.g. a 3-way h2h missing the draw) mangles the
    fair probs and silently mis-grades CLV.
    """
    rows = (
        await session.execute(
            select(OddsSnapshot.selection, OddsSnapshot.decimal_odds)
            .where(
                OddsSnapshot.fixture_id == fixture_id,
                OddsSnapshot.book == sharp_book,
                OddsSnapshot.market_id == market_id,
                OddsSnapshot.ts <= kickoff,
            )
            .order_by(OddsSnapshot.selection, OddsSnapshot.ts.desc())
        )
    ).all()
    raw: dict[str, float] = {}
    for sel, dec in rows:  # first per selection = latest (ts desc within selection)
        if sel not in raw:
            raw[sel] = dec
    if not _complete(market_type, raw):  # full market only - same rule as detection
        return None
    p = devig(raw, settings.devig_method).get(selection)
    return (1.0 / p) if p and p > 0 else None


async def settle_once() -> dict:
    now = datetime.now(UTC)
    ttl_cutoff = now - timedelta(seconds=settings.signal_ttl_seconds)
    Session = get_sessionmaker()
    stats = {"graded": 0, "clv_beats": 0, "results": 0, "expired": 0}

    async with Session() as session:
        # Expire stale 'live' signals (older than the alert TTL) so 'live' means fresh.
        # They're still graded at kickoff below (the query includes 'expired').
        res = await session.execute(
            update(Signal)
            .where(Signal.status == "live", Signal.created_at < ttl_cutoff)
            .values(status="expired")
        )
        stats["expired"] = res.rowcount
        await session.commit()

        rows = (
            await session.execute(
                select(Signal, Fixture, Market, League)
                .join(Fixture, Signal.fixture_id == Fixture.id)
                .join(Market, Signal.market_id == Market.id)
                .join(League, Fixture.league_id == League.id)
                .where(Signal.status.in_(["live", "expired"]), Fixture.kickoff_utc <= now)
            )
        ).all()

        for sig, fx, market, league in rows:
            closing = beat = result = pnl = None
            final = fx.home_score is not None and fx.away_score is not None

            # CLV + result grading applies to single-selection bets (ev and promo) - both
            # alert one selection at a posted price gradable against the sharp closing line.
            # Arb/middle are mechanical multi-leg signals with no single-selection outcome, so
            # they carry no grade row; they still reach a terminal state below.
            if sig.kind in ("ev", "promo", "value"):
                # `closing` is the no-vig fair closing decimal, so beat = our odds longer
                # than fair (genuine positive CLV).
                closing = await _closing_sharp_fair_decimal(
                    session,
                    fx.id,
                    sig.market_id,
                    sig.selection,
                    league.sharp_ref_book,
                    fx.kickoff_utc,
                    market.type,
                )
                beat = clv_beat(sig.offered_odds, closing)
                # Same condition as `final`, but inlined so the type checker narrows the scores.
                if fx.home_score is not None and fx.away_score is not None:
                    result = compute_result(
                        fx.home_score, fx.away_score, market.type, market.line, sig.selection
                    )
                    pnl = pnl_units(result, sig.offered_odds)

                # Only persist a grade row once we have something to record - never an
                # all-NULL row (which previously kept every signal re-graded forever).
                if closing is not None or result is not None:
                    await session.execute(
                        pg_insert(SignalGrade)
                        .values(
                            signal_id=sig.id,
                            closing_odds=closing,
                            beat_clv=beat,
                            result=result,
                            pnl_units=pnl,
                        )
                        .on_conflict_do_update(
                            index_elements=["signal_id"],
                            set_={
                                "closing_odds": closing,
                                "beat_clv": beat,
                                "result": result,
                                "pnl_units": pnl,
                            },
                        )
                    )

            # Terminal state once the fixture is final - for EVERY kind, so arb/middle/promo
            # stop being re-selected on each pass; pre-final they sit at 'expired'.
            sig.status = "settled" if final else "expired"
            stats["graded"] += 1
            if beat:
                stats["clv_beats"] += 1
            if result is not None:
                stats["results"] += 1

        await session.commit()

    emit("settle.pass", **stats)
    return stats
