import httpx
from app.config import settings
from app.services.cache import get_cached, set_cached

BASE_URL = "https://v3.football.api-sports.io"
CACHE_KEY = "matches:wc2026"
CACHE_TTL = 3600  # 60 minutes


def _parse_fixture(f: dict) -> dict:
    fixture = f["fixture"]
    teams = f["teams"]
    league = f["league"]
    return {
        "id": fixture["id"],
        "date": fixture["date"],
        "home_team": teams["home"]["name"],
        "away_team": teams["away"]["name"],
        "home_flag": teams["home"]["logo"],
        "away_flag": teams["away"]["logo"],
        "group": league.get("round", ""),
        "venue": fixture["venue"]["name"] or "",
        "city": fixture["venue"]["city"] or "",
        "status": _map_status(fixture["status"]["short"]),
    }


def _map_status(short: str) -> str:
    if short in ("NS", "TBD"):
        return "scheduled"
    if short in ("FT", "AET", "PEN", "AWD", "WO"):
        return "finished"
    return "live"


async def fetch_matches() -> list[dict]:
    cached = await get_cached(CACHE_KEY)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{BASE_URL}/fixtures",
            headers={"x-apisports-key": settings.api_football_key},
            params={"league": "1", "season": "2026"},
        )
        resp.raise_for_status()
        raw = resp.json().get("response", [])

    matches = [_parse_fixture(f) for f in raw]
    await set_cached(CACHE_KEY, matches, CACHE_TTL)
    return matches
