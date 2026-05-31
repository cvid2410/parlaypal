"""Results / tracker API (3.4).

Returns ParlayPal's *verified track record* — graded signals at a flat 1-unit stake. CLV-beat
% is the headline (always available from our own data); win-rate / ROI / P&L fill in as the
results resolver scores fixtures. This is proof, shown to any signed-in user (settled picks
leak no live edge), which is what sells the upgrade.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.models.core import Fixture, League, Market, Team
from app.models.signals import Signal, SignalGrade
from app.models.users import User
from app.shared.copy import selection_label
from app.shared.db import get_db

router = APIRouter(prefix="/results", tags=["results"])


@router.get("")
async def results(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = (
        await db.execute(
            select(SignalGrade, Signal, Fixture, League, Market)
            .join(Signal, SignalGrade.signal_id == Signal.id)
            .join(Fixture, Signal.fixture_id == Fixture.id)
            .join(League, Fixture.league_id == League.id)
            .join(Market, Signal.market_id == Market.id)
            .order_by(Signal.created_at)
        )
    ).all()

    # team names for labels (bulk)
    team_ids = {fx.home_id for _, _, fx, _, _ in rows} | {fx.away_id for _, _, fx, _, _ in rows}
    names: dict[int, str] = {}
    if team_ids:
        for tid, nm in (
            await db.execute(select(Team.id, Team.name).where(Team.id.in_(team_ids)))
        ).all():
            names[tid] = nm

    clv_n = clv_beats = 0
    wins = losses = pushes = 0
    pnl = 0.0
    curve = []
    recent = []
    for grade, sig, fx, league, market in rows:
        if grade.beat_clv is not None:
            clv_n += 1
            clv_beats += 1 if grade.beat_clv else 0
        if grade.result is not None:
            if grade.result == "win":
                wins += 1
            elif grade.result == "loss":
                losses += 1
            else:
                pushes += 1
            pnl += grade.pnl_units or 0.0
            curve.append(round(pnl, 3))
            if sig.kind == "arb":
                pick = "Arbitrage"
            else:
                pick = selection_label(
                    market.type,
                    market.line,
                    sig.selection,
                    names.get(fx.home_id, "?"),
                    names.get(fx.away_id, "?"),
                )
            recent.append(
                {
                    "pick": pick,
                    "league": league.name,
                    "result": grade.result,
                    "pnl_units": round(grade.pnl_units or 0.0, 2),
                }
            )

    settled = wins + losses + pushes
    decided = wins + losses
    return {
        "clv_beat_pct": round(100 * clv_beats / clv_n, 1) if clv_n else None,
        "clv_sample": clv_n,
        "settled": settled,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate": round(100 * wins / decided, 1) if decided else None,
        "pnl_units": round(pnl, 2),
        "roi_pct": round(100 * pnl / settled, 1) if settled else None,
        "curve": curve,
        "recent": list(reversed(recent[-15:])),
    }
