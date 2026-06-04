"""Sync the `leagues` table to The Odds API soccer catalog (GET /v4/sports?all=true).

Adds every soccer league the feed carries that isn't seeded yet, so our coverage == the
feed's coverage (re-run whenever The Odds API adds leagues). Design rules:

  * New leagues come in **ev_certified=False** — +EV reaches users only after the CLV gate
    passes (NON-NEGOTIABLE #2). This script never certifies anything.
  * **is_soft heuristic:** a domestic league is a soft +EV target; continental/international
    tournaments and cups are sharp (arb + best-price + scores only, no soft-book edge).
  * **Outright/futures-only entries are skipped** (has_outrights=True) — our detection is
    match-based (h2h/totals); a futures market would be a dead row.
  * **af_league_id=None** for new rows — the API-Football id (Scores/Standings) is a manual
    follow-up; odds ingestion + arb work without it.
  * Existing rows are left fully untouched (names, af ids, is_soft, ev_certified preserved).

Run from backend/:  python -m scripts.sync_odds_api_leagues [--dry-run]
"""

import argparse
import asyncio

import httpx
from sqlalchemy import select

from app.config import settings
from app.models.core import League
from app.shared.db import get_sessionmaker

SPORTS_URL = "https://api.the-odds-api.com/v4/sports"

# A league key containing any of these is a tournament/cup/international comp → sharp.
SHARP_TOKENS = (
    "uefa",
    "fifa",
    "world_cup",
    "euro",
    "nations",
    "champs_league",
    "europa",
    "qualif",
    "copa_america",
    "copa_libertadores",
    "copa_sudamericana",
    "gold_cup",
    "leagues_cup",
    "club_world",
    "africa_cup",
    "_cup",
    "coppa",
    "pokal",
    "copa_del_rey",
    "coupe",
    "fa_cup",
    "dfb",
)

# Full sport_key → country overrides (keys that don't start with a country segment).
KEY_OVERRIDE = {
    "soccer_epl": "England",
    "soccer_spl": "Scotland",
    "soccer_efl_champ": "England",
    "soccer_fa_cup": "England",
    "soccer_league_of_ireland": "Ireland",
}

# First key segment (after "soccer_") → proper country name. Anything not here (uefa, fifa,
# conmebol, concacaf, africa…) is an international comp → "International".
SEGMENT_COUNTRY = {
    "argentina": "Argentina",
    "australia": "Australia",
    "austria": "Austria",
    "belgium": "Belgium",
    "brazil": "Brazil",
    "chile": "Chile",
    "china": "China",
    "denmark": "Denmark",
    "efl": "England",
    "england": "England",
    "finland": "Finland",
    "france": "France",
    "germany": "Germany",
    "greece": "Greece",
    "italy": "Italy",
    "japan": "Japan",
    "korea": "South Korea",
    "mexico": "Mexico",
    "netherlands": "Netherlands",
    "norway": "Norway",
    "poland": "Poland",
    "portugal": "Portugal",
    "russia": "Russia",
    "saudi": "Saudi Arabia",
    "spain": "Spain",
    "sweden": "Sweden",
    "switzerland": "Switzerland",
    "turkey": "Turkey",
    "usa": "USA",
}


def is_sharp(key: str) -> bool:
    return any(tok in key for tok in SHARP_TOKENS)


def derive_name_country(key: str, title: str) -> tuple[str, str]:
    """Best-effort (name, country) from the catalog title + key."""
    name = title.split(" - ", 1)[0].strip()  # drop any " - <country>" suffix
    first = key[len("soccer_") :].split("_")[0]
    if key in KEY_OVERRIDE:
        country = KEY_OVERRIDE[key]
    elif " - " in title:  # e.g. "Primeira Liga - Portugal"
        country = title.split(" - ", 1)[1].strip()
    else:
        country = SEGMENT_COUNTRY.get(first, "International")
    return name, country


async def main() -> None:
    ap = argparse.ArgumentParser(description="Seed all Odds API soccer leagues (uncertified).")
    ap.add_argument("--dry-run", action="store_true", help="list what would be added, add nothing")
    args = ap.parse_args()

    if not settings.the_odds_api_key:
        ap.error("THE_ODDS_API_KEY is not set")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            SPORTS_URL, params={"apiKey": settings.the_odds_api_key, "all": "true"}
        )
        resp.raise_for_status()
        catalog = resp.json()

    soccer = [
        s for s in catalog if s["key"].startswith("soccer_") and not s.get("has_outrights", False)
    ]

    Session = get_sessionmaker()
    async with Session() as session:
        have = {lg.sport_key for lg in (await session.execute(select(League))).scalars().all()}
        new = [s for s in sorted(soccer, key=lambda x: x["key"]) if s["key"] not in have]

        if not new:
            print(f"Up to date — all {len(soccer)} match-market soccer leagues already seeded.")
            return

        print(f"{len(new)} new league(s) to add (of {len(soccer)} match-market soccer leagues):\n")
        for s in new:
            name, country = derive_name_country(s["key"], s["title"])
            soft = not is_sharp(s["key"])
            print(f"  {'soft ' if soft else 'sharp'}  {s['key']:42} {name} ({country})")
            if not args.dry_run:
                session.add(
                    League(
                        name=name,
                        country=country,
                        sport_key=s["key"],
                        sharp_ref_book="pinnacle",
                        is_soft=soft,
                        model_enabled=False,
                        ingest_enabled=True,
                        af_league_id=None,
                        ev_certified=False,
                    )
                )
        if args.dry_run:
            print("\n--dry-run: nothing written.")
            return
        await session.commit()
        print(f"\nAdded {len(new)} league(s), all ev_certified=False, af_league_id=None.")


if __name__ == "__main__":
    asyncio.run(main())
