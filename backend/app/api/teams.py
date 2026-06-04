"""Team page: a team's recent + upcoming games across all competitions, via API-Football.

Keyed by API-Football team id (surfaced on the standings rows). No edge here (scores aren't
an edge), so this is a free-tier surface like /scores and /standings.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.auth import get_current_user
from app.models.users import User
from app.services.af import status_of, team_fixtures

router = APIRouter(prefix="/teams", tags=["teams"])


def _shape(games: list[dict], af_team_id: int) -> list[dict]:
    """One AF fixture → a row from this team's point of view (opponent, H/A, score, status)."""
    out: list[dict] = []
    for f in games:
        teams = f.get("teams", {})
        home, away = teams.get("home", {}), teams.get("away", {})
        is_home = home.get("id") == af_team_id
        opp = away if is_home else home
        goals = f.get("goals", {})
        out.append(
            {
                "opponent": opp.get("name"),
                "opponent_logo": opp.get("logo"),
                "home_away": "H" if is_home else "A",
                "league": f.get("league", {}).get("name"),
                "kickoff": f["fixture"]["date"],
                "status": status_of(f["fixture"]["status"]["short"]),
                "minute": f["fixture"]["status"].get("elapsed"),
                "team_score": goals.get("home") if is_home else goals.get("away"),
                "opp_score": goals.get("away") if is_home else goals.get("home"),
            }
        )
    return out


def _team_header(games: list[dict], af_team_id: int) -> dict:
    """Pull the team's own name/logo from any fixture it appears in."""
    for f in games:
        for side in ("home", "away"):
            t = f.get("teams", {}).get(side, {})
            if t.get("id") == af_team_id:
                return {"name": t.get("name"), "logo": t.get("logo")}
    return {"name": None, "logo": None}


@router.get("/{af_team_id}")
async def team(
    af_team_id: int,
    last: int = Query(10, ge=1, le=40),
    next_: int = Query(10, ge=1, le=40, alias="next"),
    user: User = Depends(get_current_user),
) -> dict:
    data = await team_fixtures(af_team_id, last, next_)
    past = sorted(_shape(data["past"], af_team_id), key=lambda g: g["kickoff"], reverse=True)
    upcoming = sorted(_shape(data["upcoming"], af_team_id), key=lambda g: g["kickoff"])
    return {
        "team": _team_header(data["past"] + data["upcoming"], af_team_id),
        "past": past,
        "upcoming": upcoming,
    }
