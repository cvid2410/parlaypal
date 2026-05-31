"""Seed the `leagues` table with the v1 target set.

Adding a league later is just another row here (+ a re-run) — the ingestor is driven by
`leagues.sport_key`, so no code change is needed.

Run from the backend/ dir:  python -m scripts.seed_leagues
"""
import asyncio

from sqlalchemy import select

from app.models.core import League
from app.shared.db import get_sessionmaker

# (name, country, sport_key, is_soft, ingest_enabled, af_league_id)
# Soft long-tail leagues are where the edge lives (CLAUDE.md). Sharp leagues are kept
# is_soft=False: ingested for the Scores tab but excluded from signal detection.
# af_league_id = API-Football league id, powers the Scores tab.
LEAGUES = [
    # --- soft long tail (signal targets) ---
    ("Liga MX", "Mexico", "soccer_mexico_ligamx", True, True, 262),
    ("Brazil Série A", "Brazil", "soccer_brazil_campeonato", True, True, 71),
    ("Brazil Série B", "Brazil", "soccer_brazil_serie_b", True, True, 72),
    ("J-League", "Japan", "soccer_japan_j_league", True, True, 98),
    ("Eredivisie", "Netherlands", "soccer_netherlands_eredivisie", True, True, 88),
    ("MLS", "USA", "soccer_usa_mls", True, True, 253),
    ("Eliteserien", "Norway", "soccer_norway_eliteserien", True, True, 103),
    ("Primeira Liga", "Portugal", "soccer_portugal_primeira_liga", True, True, 94),
    # Honduras is the domain wedge but coverage on The Odds API is unconfirmed — keep the
    # row (so it shows in Leagues) but leave ingest off until the feed is verified
    # (BUILD_PLAN 0.2). Flip ingest_enabled=True once confirmed.
    # af_league_id left None: the correct API-Football id for Honduras is unverified
    # (351 turned out to be a Czech league). Set it once confirmed.
    ("Liga Nacional", "Honduras", "soccer_honduras_liga_nacional", True, False, None),
    # --- sharp leagues: Scores tab only, no edge, excluded from detection ---
    ("Premier League", "England", "soccer_epl", False, True, 39),
    ("La Liga", "Spain", "soccer_spain_la_liga", False, True, 140),
]


async def main() -> None:
    Session = get_sessionmaker()
    async with Session() as session:
        by_key = {
            lg.sport_key: lg
            for lg in (await session.execute(select(League))).scalars().all()
        }
        added = updated = 0
        for name, country, sport_key, is_soft, ingest_enabled, af_id in LEAGUES:
            existing = by_key.get(sport_key)
            if existing is not None:
                if existing.af_league_id != af_id:  # backfill af id on re-run
                    existing.af_league_id = af_id
                    updated += 1
                continue
            session.add(
                League(
                    name=name,
                    country=country,
                    sport_key=sport_key,
                    sharp_ref_book="pinnacle",
                    is_soft=is_soft,
                    model_enabled=False,
                    ingest_enabled=ingest_enabled,
                    af_league_id=af_id,
                )
            )
            added += 1
        await session.commit()
        print(f"Seeded {added} new league(s); backfilled af id on {updated}; "
              f"{len(by_key)} already present.")


if __name__ == "__main__":
    asyncio.run(main())
