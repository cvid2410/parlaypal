"""Seed the `leagues` table with the v1 target set.

Adding a league later is just another row here (+ a re-run) — the ingestor is driven by
`leagues.sport_key`, so no code change is needed.

Run from the backend/ dir:  python -m scripts.seed_leagues
"""
import asyncio

from sqlalchemy import select

from app.models.core import League
from app.shared.db import get_sessionmaker

# (name, country, sport_key, is_soft, ingest_enabled)
# Soft long-tail leagues are where the edge lives (CLAUDE.md). Sharp leagues are kept
# is_soft=False: ingested for the future Scores tab but excluded from signal detection.
LEAGUES = [
    # --- soft long tail (signal targets) ---
    ("Liga MX", "Mexico", "soccer_mexico_ligamx", True, True),
    ("Brazil Série A", "Brazil", "soccer_brazil_campeonato", True, True),
    ("Brazil Série B", "Brazil", "soccer_brazil_serie_b", True, True),
    ("J-League", "Japan", "soccer_japan_j_league", True, True),
    ("Eredivisie", "Netherlands", "soccer_netherlands_eredivisie", True, True),
    ("MLS", "USA", "soccer_usa_mls", True, True),
    ("Eliteserien", "Norway", "soccer_norway_eliteserien", True, True),
    ("Primeira Liga", "Portugal", "soccer_portugal_primeira_liga", True, True),
    # Honduras is the domain wedge but coverage on The Odds API is unconfirmed — keep the
    # row (so it shows in Leagues) but leave ingest off until the feed is verified
    # (BUILD_PLAN 0.2). Flip ingest_enabled=True once confirmed.
    ("Liga Nacional", "Honduras", "soccer_honduras_liga_nacional", True, False),
    # --- sharp leagues: Scores tab only, no edge, excluded from detection ---
    ("Premier League", "England", "soccer_epl", False, True),
    ("La Liga", "Spain", "soccer_spain_la_liga", False, True),
]


async def main() -> None:
    Session = get_sessionmaker()
    async with Session() as session:
        existing = set(
            (await session.execute(select(League.sport_key))).scalars().all()
        )
        added = 0
        for name, country, sport_key, is_soft, ingest_enabled in LEAGUES:
            if sport_key in existing:
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
                )
            )
            added += 1
        await session.commit()
        print(f"Seeded {added} new league(s); {len(existing)} already present.")


if __name__ == "__main__":
    asyncio.run(main())
