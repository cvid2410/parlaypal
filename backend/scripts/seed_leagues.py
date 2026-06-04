"""Curation layer over the league set — the deliberate judgment calls the mechanical scripts
can't make. Run it LAST in the league-setup chain:

    python -m scripts.sync_odds_api_leagues   # breadth: create every Odds API league (uncertified)
    python -m scripts.match_af_ids --apply    # scores: fill API-Football ids
    python -m scripts.seed_leagues            # curation: this file

This file owns ONLY the exceptions, and is the single source of truth for each:
  * EV_CERTIFIED — leagues whose +EV reaches users. A league is certified only after the
    CLV backtest gate passes (NON-NEGOTIABLE #2). Authoritative: anything NOT in this set is
    forced ev_certified=False, so certification is fully reproducible from here and removing
    a key un-certifies it. (scripts.certify_league is for quick experiments; this is durable.)
  * SHARP_OVERRIDE — leagues where sync's "domestic = soft" heuristic is wrong; force them
    sharp (arb + best-price + scores only, no soft-book +EV edge).
  * INGEST_DISABLED — leagues we deliberately don't poll for odds.
  * NON_FEED — scores-only leagues The Odds API doesn't carry, so sync never creates them.

It does NOT create feed leagues (sync_odds_api_leagues does) or set af ids (match_af_ids does).
"""

import asyncio

from sqlalchemy import select

from app.models.core import League
from app.shared.db import get_sessionmaker

# Leagues that passed the CLV backtest gate → +EV is served to users (NON-NEGOTIABLE #2).
# Add a sport_key ONLY after scripts.clv_report shows it PASS on a real sample; remove to
# un-certify. This set is authoritative over the whole table.
EV_CERTIFIED: set[str] = {
    "soccer_sweden_superettan",
}

# sync marks every domestic league soft, but the big-5 are sharp *domestic* leagues — too
# liquid for any soft-book +EV edge (arb + best-price + scores only). The heuristic can't
# tell them from a soft league (their keys carry no cup/tournament token), so pin them here.
SHARP_OVERRIDE: set[str] = {
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_germany_bundesliga",
    "soccer_italy_serie_a",
    "soccer_france_ligue_one",
}

# Leagues we deliberately don't poll for odds.
INGEST_DISABLED: set[str] = {
    "soccer_friendlies_international",  # no odds feed — scores-only
}

# Scores-only leagues The Odds API doesn't carry, so sync can't create them.
# (name, country, sport_key, af_league_id) — is_soft is moot (no odds), ingest stays off.
NON_FEED: list[tuple[str, str, str, int]] = [
    ("Friendlies", "World", "soccer_friendlies_international", 10),
]


async def main() -> None:
    Session = get_sessionmaker()
    async with Session() as session:
        by_key = {
            lg.sport_key: lg for lg in (await session.execute(select(League))).scalars().all()
        }

        # 1. Create the deliberate non-feed (scores-only) leagues sync can't.
        created = 0
        for name, country, sport_key, af_id in NON_FEED:
            if sport_key in by_key:
                continue
            lg = League(
                name=name,
                country=country,
                sport_key=sport_key,
                sharp_ref_book="pinnacle",
                is_soft=True,
                model_enabled=False,
                ingest_enabled=False,
                af_league_id=af_id,
                ev_certified=False,
            )
            session.add(lg)
            by_key[sport_key] = lg
            created += 1

        # 2. Apply curation overrides authoritatively across the whole table.
        certified = uncertified = sharp = ingest_off = 0
        for sport_key, lg in by_key.items():
            want_cert = sport_key in EV_CERTIFIED
            if want_cert and not lg.is_soft:  # can't have a soft-book +EV edge on a sharp league
                print(f"WARNING: {lg.name} is is_soft=False — refusing to certify +EV.")
                want_cert = False
            if lg.ev_certified != want_cert:
                lg.ev_certified = want_cert
                certified += int(want_cert)
                uncertified += int(not want_cert)
            if sport_key in SHARP_OVERRIDE and lg.is_soft:
                lg.is_soft = False
                sharp += 1
            if sport_key in INGEST_DISABLED and lg.ingest_enabled:
                lg.ingest_enabled = False
                ingest_off += 1

        # A certified key missing from the DB means the chain ran out of order (sync first).
        missing = EV_CERTIFIED - set(by_key)
        if missing:
            print(
                f"WARNING: certified leagues not in DB (run sync_odds_api_leagues first): {missing}"
            )

        await session.commit()
        print(
            f"Curation applied: created {created} non-feed league(s); "
            f"certified {certified}, un-certified {uncertified}, forced sharp {sharp}, "
            f"ingest-off {ingest_off}."
        )


if __name__ == "__main__":
    asyncio.run(main())
