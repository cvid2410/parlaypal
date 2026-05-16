from fastapi import APIRouter, HTTPException, Query
from app.services.odds_api import fetch_all_odds, fetch_matches_from_odds

router = APIRouter()


@router.get("/odds")
async def get_odds(match_id: int = Query(...), market: str | None = Query(default=None)):
    try:
        matches = await fetch_matches_from_odds()
        all_odds = await fetch_all_odds()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    match = next((m for m in matches if m["id"] == match_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    key = f"{match['home_team']}|{match['away_team']}"
    odds = all_odds.get(key, [])
    if market:
        odds = [o for o in odds if o["market"] == market]
    return odds
