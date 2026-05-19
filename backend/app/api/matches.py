from fastapi import APIRouter, HTTPException, Query
from app.services.api_football import fetch_matches

router = APIRouter()


@router.get("/matches")
async def get_matches(
    group: str = Query(default="all"),
    mock_live: bool = Query(default=False),
):
    try:
        matches = await fetch_matches()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    if group.lower() != "all":
        matches = [
            m for m in matches
            if group.upper() in m.get("group", "").upper()
        ]

    if mock_live and matches:
        import copy
        matches = [copy.copy(m) for m in matches]
        matches[0]["status"] = "live"
        matches[0]["home_score"] = 1
        matches[0]["away_score"] = 0

    return matches
