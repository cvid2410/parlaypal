"""Scores tab: live + today's fixtures for our leagues, via API-Football.

One /fixtures?date=today call (shared, cached) → filter to leagues we map by af_league_id.
No edge here (scores aren't an edge), so this is a free-tier surface.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.models.core import League
from app.models.users import User
from app.services.af import OFF, fixtures_by_date, status_of
from app.shared.db import get_db

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("")
async def scores(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    af_map = {
        lg.af_league_id: lg
        for lg in (await db.execute(select(League).where(League.af_league_id.isnot(None))))
        .scalars()
        .all()
    }
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    raw = await fixtures_by_date(today)

    live, upcoming, finished, off = [], [], [], []
    for f in raw:
        lg = af_map.get(f["league"]["id"])
        if lg is None:
            continue
        short = f["fixture"]["status"]["short"]
        st = status_of(short)
        goals = f.get("goals", {})
        item = {
            "league": lg.name,
            "country": lg.country,
            "home": f["teams"]["home"]["name"],
            "away": f["teams"]["away"]["name"],
            "home_logo": f["teams"]["home"].get("logo"),
            "away_logo": f["teams"]["away"].get("logo"),
            "home_score": goals.get("home"),
            "away_score": goals.get("away"),
            "status": st,
            "note": OFF.get(short),  # human label for off matches; None otherwise
            "minute": f["fixture"]["status"].get("elapsed"),
            "kickoff": f["fixture"]["date"],
        }
        {"live": live, "finished": finished, "off": off}.get(st, upcoming).append(item)

    upcoming.sort(key=lambda m: m["kickoff"])
    return {"live": live, "upcoming": upcoming, "finished": finished, "off": off}
