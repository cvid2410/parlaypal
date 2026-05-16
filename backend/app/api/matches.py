from fastapi import APIRouter, HTTPException, Query
from app.services.api_football import fetch_matches

router = APIRouter()


@router.get("/matches")
async def get_matches(group: str = Query(default="all")):
    try:
        matches = await fetch_matches()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    if group.lower() != "all":
        matches = [
            m for m in matches
            if group.upper() in m.get("group", "").upper()
        ]

    return matches
