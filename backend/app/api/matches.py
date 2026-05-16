from fastapi import APIRouter, HTTPException, Query
from app.services.odds_api import fetch_matches_from_odds

router = APIRouter()


@router.get("/matches")
async def get_matches(group: str = Query(default="all")):
    try:
        matches = await fetch_matches_from_odds()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    if group.lower() != "all":
        matches = [
            m for m in matches
            if not m.get("group") or group.upper() in m.get("group", "").upper()
        ]

    return matches
