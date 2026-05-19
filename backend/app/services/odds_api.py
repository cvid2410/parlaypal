import httpx
from app.config import settings
from app.services.cache import get_cached, set_cached

BASE_URL = "https://api.the-odds-api.com/v4"
SPORT = "soccer_fifa_world_cup"
CACHE_TTL = 300  # 5 minutes
MARKETS = "h2h,totals"
PROP_MARKETS = ["btts", "corners", "player_shots_on_target", "player_cards"]
BOOKS = "draftkings,fanduel,betmgm"


def _to_american(decimal: float) -> str:
    if decimal >= 2.0:
        return f"+{int((decimal - 1) * 100)}"
    return str(int(-100 / (decimal - 1)))


def _parse_game(game: dict) -> list[dict]:
    results = []
    for bookmaker in game.get("bookmakers", []):
        book = bookmaker["key"]
        book_link = bookmaker.get("link")
        for market in bookmaker.get("markets", []):
            market_key = market["key"]
            market_link = market.get("link")
            for outcome in market.get("outcomes", []):
                price = outcome.get("price", 2.0)
                link = outcome.get("link") or market_link or book_link or None
                results.append({
                    "market": market_key,
                    "selection": outcome["name"].lower().replace(" ", "_"),
                    "odds": _to_american(price),
                    "book": book,
                    "description": outcome.get("description", ""),
                    "point": outcome.get("point"),
                    "link": link,
                })
    return results


async def _fetch_games(markets: str, client: httpx.AsyncClient) -> list[dict]:
    resp = await client.get(
        f"{BASE_URL}/sports/{SPORT}/odds",
        params={
            "apiKey": settings.the_odds_api_key,
            "regions": "us",
            "markets": markets,
            "bookmakers": BOOKS,
            "oddsFormat": "decimal",
            "includeLinks": "true",
        },
    )
    resp.raise_for_status()
    return resp.json()


async def fetch_all_odds() -> dict[str, list[dict]]:
    """Fetch all WC2026 odds keyed by 'HomeTeam|AwayTeam', including prop markets."""
    cached = await get_cached("odds:all")
    if cached is not None:
        return cached

    result: dict[str, list[dict]] = {}

    async with httpx.AsyncClient(timeout=15) as client:
        games = await _fetch_games(MARKETS, client)
        for game in games:
            key = f"{game['home_team']}|{game['away_team']}"
            result[key] = _parse_game(game)

        if settings.the_odds_api_key:
            for prop_market in PROP_MARKETS:
                try:
                    prop_games = await _fetch_games(prop_market, client)
                    for game in prop_games:
                        key = f"{game['home_team']}|{game['away_team']}"
                        result.setdefault(key, [])
                        result[key].extend(_parse_game(game))
                except Exception:
                    pass

    await set_cached("odds:all", result, CACHE_TTL)
    return result
