"""Leagues tab: our leagues with live-signal counts (all from our own DB)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.models.core import Fixture, League
from app.models.signals import Signal
from app.models.users import User
from app.shared.db import get_db

router = APIRouter(prefix="/leagues", tags=["leagues"])


@router.get("")
async def list_leagues(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    live_counts = (
        select(Fixture.league_id, func.count(Signal.id).label("c"))
        .join(Signal, Signal.fixture_id == Fixture.id)
        .where(Signal.status == "live")
        .group_by(Fixture.league_id)
        .subquery()
    )
    rows = (await db.execute(
        select(League, func.coalesce(live_counts.c.c, 0))
        .outerjoin(live_counts, live_counts.c.league_id == League.id)
        .order_by(func.coalesce(live_counts.c.c, 0).desc(), League.name)
    )).all()

    leagues = [{
        "id": lg.id,
        "name": lg.name,
        "country": lg.country,
        "is_soft": lg.is_soft,
        "live_signals": int(c),
    } for lg, c in rows]
    return {"count": len(leagues), "live_total": sum(l["live_signals"] for l in leagues),
            "leagues": leagues}
