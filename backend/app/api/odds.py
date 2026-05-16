from fastapi import APIRouter, HTTPException, Query
from app.services.api_football import fetch_matches
from app.services.odds_api import fetch_all_odds

router = APIRouter()

# API-Football team names that differ from The Odds API spellings
_AF_TO_ODDS: dict[str, str] = {
    "Türkiye": "Turkey",
    "Congo DR": "DR Congo",
    "Cape Verde Islands": "Cape Verde",
}


def _odds_name(name: str) -> str:
    return _AF_TO_ODDS.get(name, name)


_BOOK_PREFERENCE = ["draftkings", "fanduel", "betmgm"]


@router.get("/odds/h2h")
async def get_h2h_summary():
    """Returns best available h2h odds per match, keyed by match_id string."""
    try:
        matches = await fetch_matches()
        all_odds = await fetch_all_odds()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    result: dict[str, list] = {}
    for match in matches:
        key = f"{_odds_name(match['home_team'])}|{_odds_name(match['away_team'])}"
        h2h = [o for o in all_odds.get(key, []) if o["market"] == "h2h"]
        if not h2h:
            continue
        chosen = next(
            (lines for book in _BOOK_PREFERENCE
             if (lines := [l for l in h2h if l["book"] == book]) and len(lines) >= 2),
            h2h[:3],
        )
        result[str(match["id"])] = chosen
    return result


@router.get("/odds")
async def get_odds(match_id: int = Query(...), market: str | None = Query(default=None)):
    try:
        matches = await fetch_matches()
        all_odds = await fetch_all_odds()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    match = next((m for m in matches if m["id"] == match_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    key = f"{_odds_name(match['home_team'])}|{_odds_name(match['away_team'])}"
    odds = all_odds.get(key, [])
    if market:
        odds = [o for o in odds if o["market"] == market]
    return odds
