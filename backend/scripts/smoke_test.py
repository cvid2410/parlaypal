"""
Run: python scripts/smoke_test.py
Verifies API-Football and The Odds API both respond with real data.
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

API_FOOTBALL_KEY = os.environ["API_FOOTBALL_KEY"]
ODDS_API_KEY = os.environ["THE_ODDS_API_KEY"]

# WC2026 league ID in API-Football is 1 (FIFA World Cup)
FIXTURES_URL = "https://v3.football.api-sports.io/fixtures"
ODDS_URL = "https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds"


def test_api_football():
    resp = httpx.get(
        FIXTURES_URL,
        headers={"x-apisports-key": API_FOOTBALL_KEY},
        params={"league": "1", "season": "2026"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    print(data)
    fixtures = data.get("response", [])
    print(f"[API-Football] {len(fixtures)} fixtures returned")
    if fixtures:
        f = fixtures[0]
        print(f"  Sample: {f['teams']['home']['name']} vs {f['teams']['away']['name']} — {f['fixture']['date']}")
    else:
        print("  WARNING: 0 fixtures — check league/season params or subscription tier")
    remaining = resp.headers.get("x-ratelimit-requests-remaining", "?")
    print(f"  Remaining requests today: {remaining}")


def test_odds_api():
    resp = httpx.get(
        ODDS_URL,
        params={
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h",
        },
        timeout=10,
    )
    resp.raise_for_status()
    games = resp.json()
    print(f"\n[The Odds API] {len(games)} games with odds returned")
    if games:
        g = games[0]
        book = g["bookmakers"][0] if g.get("bookmakers") else None
        print(f"  Sample: {g['home_team']} vs {g['away_team']} — {g['commence_time']}")
        if book:
            market = book["markets"][0]
            outcomes = {o["name"]: o["price"] for o in market["outcomes"]}
            print(f"  Odds ({book['key']}): {outcomes}")
    remaining = resp.headers.get("x-requests-remaining", "?")
    print(f"  Remaining requests this month: {remaining}")


if __name__ == "__main__":
    print("=== parlaypal.gg API Smoke Test ===\n")
    test_api_football()
    test_odds_api()
    print("\n✓ Smoke test complete")
