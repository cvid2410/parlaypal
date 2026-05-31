"""Shared API-Football client. One cached call per date powers both the results resolver
and the Scores tab (no duplicate API spend)."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import settings
from app.services.cache import get_cached, set_cached

AF_BASE = "https://v3.football.api-sports.io"
FINISHED = {"FT", "AET", "PEN", "AWD", "WO"}
LIVE = {"1H", "2H", "HT", "ET", "BT", "P", "LIVE", "INT", "SUSP"}
# Matches that won't be played — these must NOT fall through to "scheduled" (which would
# park a cancelled game in the Upcoming column with a future-looking kickoff time). The
# value is the human label shown on the Scores tab.
OFF = {"CANC": "Cancelled", "PST": "Postponed", "ABD": "Abandoned"}


async def fixtures_by_date(date_str: str) -> list[dict]:
    """Raw API-Football fixtures for a UTC date. Cached: today briefly, past dates long."""
    key = f"afraw:{date_str}"
    cached = await get_cached(key)
    if cached is not None:
        return cached
    if not settings.api_football_key:
        return []
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{AF_BASE}/fixtures",
            headers={"x-apisports-key": settings.api_football_key},
            params={"date": date_str, "timezone": "UTC"},
        )
        resp.raise_for_status()
        raw = resp.json().get("response", [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Don't pin an empty payload: a 200-with-[] is almost always a transient upstream blip
    # (a real past date with football is never empty), and caching it for a day would hide
    # those fixtures from the results resolver so their signals never get graded. Short TTL
    # lets the next request self-heal.
    ttl = 60 if not raw else (120 if date_str == today else 86400)
    await set_cached(key, raw, ttl=ttl)
    return raw


def status_of(short: str) -> str:
    if short in FINISHED:
        return "finished"
    if short in LIVE:
        return "live"
    if short in OFF:
        return "off"
    return "scheduled"


async def current_season(af_league_id: int) -> int | None:
    """The league's current season year (handles calendar vs cross-year leagues)."""
    key = f"afseason:{af_league_id}"
    cached = await get_cached(key)
    if cached is not None:
        return cached
    if not settings.api_football_key:
        return None
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{AF_BASE}/leagues",
            headers={"x-apisports-key": settings.api_football_key},
            params={"id": af_league_id},
        )
        resp.raise_for_status()
        data = resp.json().get("response", [])
    year = None
    if data:
        for s in data[0].get("seasons", []):
            if s.get("current"):
                year = s.get("year")
                break
    if year is not None:
        await set_cached(key, year, ttl=86400)
    return year


async def standings(af_league_id: int, season: int) -> list[dict]:
    """League table groups. Returns [{group, rows:[...]}] — one entry per table
    (most leagues have one; MLS-style leagues have a group per conference)."""
    key = f"afstand:{af_league_id}:{season}"
    cached = await get_cached(key)
    if cached is not None:
        return cached
    if not settings.api_football_key:
        return []
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{AF_BASE}/standings",
            headers={"x-apisports-key": settings.api_football_key},
            params={"league": af_league_id, "season": season},
        )
        resp.raise_for_status()
        data = resp.json().get("response", [])
    groups: list[dict] = []
    if data:
        for table in data[0].get("league", {}).get("standings", []):
            rows = [{
                "rank": r.get("rank"),
                "team": r["team"]["name"],
                "logo": r["team"].get("logo"),
                "points": r.get("points"),
                "played": r.get("all", {}).get("played"),
                "win": r.get("all", {}).get("win"),
                "draw": r.get("all", {}).get("draw"),
                "lose": r.get("all", {}).get("lose"),
                "gd": r.get("goalsDiff"),
                "form": r.get("form"),
            } for r in table]
            groups.append({"group": table[0].get("group") if table else "", "rows": rows})
    # As with fixtures_by_date: a transient empty standings response shouldn't pin "no table"
    # for 10 minutes — cache empties briefly so the next request recovers.
    await set_cached(key, groups, ttl=600 if groups else 60)
    return groups
