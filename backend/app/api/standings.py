"""Standings tab: a league's table(s) from API-Football, with team logos."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.models.core import League
from app.models.users import User
from app.services.af import current_season, standings
from app.shared.db import get_db

router = APIRouter(prefix="/standings", tags=["standings"])


@router.get("/{league_id}")
async def league_standings(
    league_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    lg = (await db.execute(select(League).where(League.id == league_id))).scalar_one_or_none()
    if lg is None:
        raise HTTPException(status_code=404, detail="League not found")
    if lg.af_league_id is None:
        return {"league": lg.name, "country": lg.country, "available": False, "groups": []}

    season = await current_season(lg.af_league_id)
    groups = await standings(lg.af_league_id, season) if season else []
    return {
        "league": lg.name,
        "country": lg.country,
        "available": bool(groups),
        "season": season,
        "groups": groups,
    }
