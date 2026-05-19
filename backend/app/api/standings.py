from fastapi import APIRouter, HTTPException
import httpx
from app.config import settings
from app.services.cache import get_cached, set_cached

router = APIRouter()

BASE_URL = "https://v3.football.api-sports.io"
CACHE_KEY = "standings:wc2026"
CACHE_TTL = 1800  # 30 minutes


def _parse_entry(e: dict) -> dict:
    team = e["team"]
    stats = e["all"]
    return {
        "rank": e["rank"],
        "team": team["name"],
        "logo": team["logo"],
        "played": stats["played"],
        "won": stats["win"],
        "drawn": stats["draw"],
        "lost": stats["lose"],
        "gf": stats["goals"]["for"],
        "ga": stats["goals"]["against"],
        "gd": e["goalsDiff"],
        "points": e["points"],
    }


@router.get("/standings")
async def get_standings():
    cached = await get_cached(CACHE_KEY)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{BASE_URL}/standings",
                headers={"x-apisports-key": settings.api_football_key},
                params={"league": "1", "season": "2026"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    groups = []
    for league in data.get("response", []):
        for group_entries in league["league"]["standings"]:
            if not group_entries:
                continue
            name = group_entries[0].get("group", "Group")
            groups.append({
                "group": name,
                "entries": [_parse_entry(e) for e in group_entries],
            })

    groups.sort(key=lambda g: g["group"])
    await set_cached(CACHE_KEY, groups, CACHE_TTL)
    return groups
