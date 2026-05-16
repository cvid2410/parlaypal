import zlib
import httpx
from app.config import settings
from app.services.cache import get_cached, set_cached

BASE_URL = "https://api.the-odds-api.com/v4"
SPORT = "soccer_fifa_world_cup"
CACHE_TTL = 300  # 5 minutes
MATCHES_CACHE_TTL = 3600  # 60 minutes
MARKETS = "h2h,totals,btts"
PROP_MARKETS = ["corners", "player_shots_on_target", "player_cards"]
BOOKS = "draftkings,fanduel,betmgm"

# ISO 3166-1 alpha-2 codes for flagcdn.com — covers all WC 2026 nations
_TEAM_FLAGS: dict[str, str] = {
    "Argentina": "ar", "Brazil": "br", "Colombia": "co", "Ecuador": "ec",
    "Uruguay": "uy", "Paraguay": "py", "Chile": "cl", "Venezuela": "ve",
    "Bolivia": "bo", "Peru": "pe",
    "Mexico": "mx", "United States": "us", "USA": "us", "Canada": "ca",
    "Panama": "pa", "Costa Rica": "cr", "Honduras": "hn", "Jamaica": "jm",
    "Guatemala": "gt", "El Salvador": "sv", "Trinidad and Tobago": "tt",
    "Morocco": "ma", "Nigeria": "ng", "Egypt": "eg", "Senegal": "sn",
    "Ivory Coast": "ci", "South Africa": "za", "DR Congo": "cd",
    "Cameroon": "cm", "Tunisia": "tn", "Ghana": "gh", "Mali": "ml",
    "Algeria": "dz", "Benin": "bj", "Guinea": "gn", "Cape Verde": "cv",
    "Zimbabwe": "zw", "Burkina Faso": "bf", "Equatorial Guinea": "gq",
    "France": "fr", "Germany": "de", "Spain": "es", "England": "gb-eng",
    "Portugal": "pt", "Netherlands": "nl", "Italy": "it", "Belgium": "be",
    "Croatia": "hr", "Switzerland": "ch", "Denmark": "dk", "Poland": "pl",
    "Serbia": "rs", "Romania": "ro", "Austria": "at", "Hungary": "hu",
    "Scotland": "gb-sct", "Turkey": "tr", "Czech Republic": "cz",
    "Slovakia": "sk", "Slovenia": "si", "Georgia": "ge", "Ukraine": "ua",
    "Albania": "al",
    "Japan": "jp", "South Korea": "kr", "Iran": "ir", "Saudi Arabia": "sa",
    "Australia": "au", "Qatar": "qa", "Jordan": "jo", "Uzbekistan": "uz",
    "Iraq": "iq", "Indonesia": "id",
    "New Zealand": "nz",
}


def _flag_url(team: str) -> str:
    code = _TEAM_FLAGS.get(team, "")
    return f"https://flagcdn.com/w40/{code}.png" if code else ""


def _game_to_match(game: dict) -> dict:
    event_id = game.get("id", game["home_team"] + game["away_team"])
    match_id = zlib.crc32(event_id.encode()) & 0x7FFFFFFF
    home = game["home_team"]
    away = game["away_team"]
    return {
        "id": match_id,
        "date": game["commence_time"],
        "home_team": home,
        "away_team": away,
        "home_flag": _flag_url(home),
        "away_flag": _flag_url(away),
        "group": "",
        "venue": "",
        "city": "",
        "status": "scheduled",
    }


async def fetch_matches_from_odds() -> list[dict]:
    cached = await get_cached("matches:wc2026")
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=15) as client:
        games = await _fetch_games("h2h", client)

    matches = sorted([_game_to_match(g) for g in games], key=lambda m: m["date"])
    await set_cached("matches:wc2026", matches, MATCHES_CACHE_TTL)
    return matches


def _cache_key(match_id: int) -> str:
    return f"odds:{match_id}"


def _to_american(decimal: float) -> str:
    if decimal >= 2.0:
        return f"+{int((decimal - 1) * 100)}"
    return str(int(-100 / (decimal - 1)))


def _parse_game(game: dict) -> list[dict]:
    results = []
    for bookmaker in game.get("bookmakers", []):
        book = bookmaker["key"]
        for market in bookmaker.get("markets", []):
            market_key = market["key"]  # h2h, totals, etc.
            for outcome in market.get("outcomes", []):
                price = outcome.get("price", 2.0)
                # The Odds API returns decimal odds
                results.append({
                    "market": market_key,
                    "selection": outcome["name"].lower().replace(" ", "_"),
                    "odds": _to_american(price),
                    "book": book,
                    "description": outcome.get("description", ""),
                    "point": outcome.get("point"),
                })
    return results


async def fetch_odds_for_match(match_id: int) -> list[dict]:
    cache_key = _cache_key(match_id)
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    # The Odds API uses its own event IDs, not API-Football IDs.
    # Fetch all WC2026 events and find by home/away team matching.
    # For now we fetch the full list and the caller filters by match_id.
    # In Task 3 we store api_football_id→event mapping; here we do best-effort.
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{BASE_URL}/sports/{SPORT}/odds",
            params={
                "apiKey": settings.the_odds_api_key,
                "regions": "us",
                "markets": MARKETS,
                "bookmakers": BOOKS,
                "oddsFormat": "decimal",
            },
        )
        resp.raise_for_status()
        games = resp.json()

    # Return all odds; the router filters to the requested match_id via team name lookup
    all_odds: dict[str, list[dict]] = {}
    for game in games:
        key = f"{game['home_team']}|{game['away_team']}"
        all_odds[key] = _parse_game(game)

    # Cache each game individually using a combined key (best-effort without true ID mapping)
    await set_cached(cache_key, list(all_odds.values())[:1] or [], CACHE_TTL)

    # Return empty for now — proper team→match_id mapping wired in Task 3 DB work
    return all_odds.get(str(match_id), [])


async def _fetch_games(markets: str, client: httpx.AsyncClient) -> list[dict]:
    resp = await client.get(
        f"{BASE_URL}/sports/{SPORT}/odds",
        params={
            "apiKey": settings.the_odds_api_key,
            "regions": "us",
            "markets": markets,
            "bookmakers": BOOKS,
            "oddsFormat": "decimal",
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
        # Core markets (always fetch)
        games = await _fetch_games(MARKETS, client)
        for game in games:
            key = f"{game['home_team']}|{game['away_team']}"
            result[key] = _parse_game(game)

        # Prop markets — may not exist on free tier; fail silently per market
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
