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
    # --- sharp / big leagues: no soft-book +EV edge, but mechanical signals (arb, middles)
    #     still run, plus Scores/Standings. World Cup has no fixtures until June 2026. ---
    ("Premier League", "England", "soccer_epl", False, True, 39),
    ("La Liga", "Spain", "soccer_spain_la_liga", False, True, 140),
    ("World Cup", "International", "soccer_fifa_world_cup", False, True, 1),
    # --- Scores-only: The Odds API carries no international-friendlies feed, so ingest is
    #     off (no odds → no signals). af id 10 = men's international friendlies (verified
    #     against today's API-Football fixtures), so they still show on the live Scores tab.
    #     The sport_key is a placeholder (no active Odds API key); reconcile if one appears. ---
    ("Friendlies", "World", "soccer_friendlies_international", True, False, 10),
]


async def main() -> None:
    Session = get_sessionmaker()
    async with Session() as session:
        by_key = {
            lg.sport_key: lg
            for lg in (await session.execute(select(League))).scalars().all()
        }
        added = updated = 0
        for name, country, sport_key, is_soft, ingest_enabled, af_id, ev_certified in LEAGUES:
            existing = by_key.get(sport_key)
            if existing is not None:
                # Reconcile the curated flags on re-run (af id, and the EV launch gate so
                # certification is reproducible from this file, not just a one-off script run).
                changed = False
                if existing.af_league_id != af_id:
                    existing.af_league_id = af_id
                    changed = True
                if existing.ev_certified != ev_certified:
                    existing.ev_certified = ev_certified
                    changed = True
                updated += int(changed)
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
                    ev_certified=ev_certified,
                )
            )
            added += 1
        await session.commit()
        print(f"Seeded {added} new league(s); backfilled af id on {updated}; "
              f"{len(by_key)} already present.")


if __name__ == "__main__":
    asyncio.run(main())
