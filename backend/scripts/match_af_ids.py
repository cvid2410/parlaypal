"""Match leagues missing an `af_league_id` to API-Football's /leagues catalog.

af_league_id powers the Scores/Standings tab. This pulls the live API-Football catalog and
fuzzy-matches each league with af_league_id IS NULL by (country, name), grounding every
proposed id in real catalog data — never a hardcoded guess (the seed's "351 turned out to
be a Czech league" scar). High-confidence exact matches auto-apply with --apply; everything
softer is printed as REVIEW and left NULL (NON-NEGOTIABLE #6 — unmatched go to review, not
/dev/null).

Run from backend/:
  python -m scripts.match_af_ids            # dry-run: print proposed matches
  python -m scripts.match_af_ids --apply    # write the high-confidence ones
"""

import argparse
import asyncio
import unicodedata
from difflib import SequenceMatcher

import httpx
from sqlalchemy import select

from app.config import settings
from app.models.core import League
from app.services.af import AF_BASE
from app.shared.db import get_sessionmaker

AUTO = 0.86  # >= this similarity (same country) auto-applies
MAYBE = 0.60  # >= this is shown as a REVIEW suggestion; below is "no match"

# Grounded overrides for leagues whose name differs too much from API-Football's to match by
# string similarity (verified by hand against the live /leagues catalog — never guessed).
# Keyed by Odds API sport_key. The fuzzy matcher handles everything else.
AF_OVERRIDE = {
    "soccer_germany_bundesliga2": 79,  # 2. Bundesliga
    "soccer_spain_segunda_division": 141,  # Segunda División
    "soccer_england_efl_cup": 48,  # League Cup
    "soccer_england_league1": 41,  # League One
    "soccer_england_league2": 42,  # League Two
    "soccer_belgium_first_div": 144,  # Jupiler Pro League
    "soccer_argentina_primera_division": 128,  # Liga Profesional Argentina
    "soccer_league_of_ireland": 357,  # Premier Division
    "soccer_austria_bundesliga": 218,  # Bundesliga (Austria)
    "soccer_conmebol_copa_libertadores": 13,  # CONMEBOL Libertadores
    "soccer_conmebol_copa_sudamericana": 11,  # CONMEBOL Sudamericana
    "soccer_denmark_superliga": 119,  # Superliga
    "soccer_saudi_arabia_pro_league": 307,  # Pro League
    "soccer_greece_super_league": 197,  # Super League 1
    "soccer_switzerland_superleague": 207,  # Super League (Switzerland)
    "soccer_turkey_super_league": 203,  # Süper Lig
    "soccer_fifa_world_cup_qualifiers_europe": 32,  # World Cup - Qualification Europe
    "soccer_fifa_world_cup_qualifiers_south_america": 34,  # WC - Qualification South America
    "soccer_fifa_world_cup_womens": 8,  # World Cup - Women
    "soccer_uefa_european_championship": 4,  # Euro Championship
    "soccer_uefa_euro_qualification": 960,  # Euro Championship - Qualification
    # soccer_uefa_champs_league_qualification: no distinct AF competition — stays NULL.
    # Names that diverge from API-Football's, so fuzzy match would send them to REVIEW.
    "soccer_brazil_campeonato": 71,  # Serie A (Brazil)
    "soccer_brazil_serie_b": 72,  # Serie B (Brazil)
    "soccer_japan_j_league": 98,  # J1 League
    "soccer_netherlands_eredivisie": 88,  # Eredivisie ("Dutch Eredivisie" in the catalog)
    "soccer_usa_mls": 253,  # Major League Soccer
    "soccer_epl": 39,  # Premier League
    "soccer_fifa_world_cup": 1,  # World Cup
}

# Our country label -> API-Football country name(s) when they differ.
COUNTRY_ALIAS = {
    "International": "World",
    "South Korea": "South-Korea",
    "Saudi Arabia": "Saudi-Arabia",
    "USA": "USA",
    "Europe": "World",
    "South America": "World",
}

# Strip these noise tokens before comparing names (keep the distinguishing ones).
NOISE = {"football", "the", "of", "fc"}

# Tokens that *distinguish* a league from a same-named sibling. If two names differ by any
# of these (or by a digit), they are NOT the same competition — e.g. "Bundesliga" vs
# "Bundesliga 2", "World Cup" vs "Women's World Cup", "Champions League" vs its
# "Qualification". Such a pair can never auto-apply (it goes to REVIEW), no matter how high
# the raw string similarity is. This is what stops the dangerous substring matches.
DISCRIMINATORS = {
    "women",
    "womens",
    "w",
    "qualification",
    "qualifying",
    "qualifiers",
    "quali",
    "amateur",
    "reserve",
    "reserves",
    "youth",
    "u19",
    "u20",
    "u21",
    "u23",
    "cup",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = "".join(c if c.isalnum() else " " for c in s.lower())
    toks = [t for t in s.split() if t not in NOISE]
    return " ".join(toks)


def discriminators(name: str) -> set[str]:
    return {t for t in norm(name).split() if t.isdigit() or t in DISCRIMINATORS}


def score(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def discriminator_conflict(a: str, b: str) -> bool:
    """True if the names carry different distinguishing tokens (tier number, women, quali…)."""
    return discriminators(a) != discriminators(b)


async def main() -> None:
    ap = argparse.ArgumentParser(description="Match null af_league_id to API-Football.")
    ap.add_argument("--apply", action="store_true", help="write high-confidence matches")
    args = ap.parse_args()
    if not settings.api_football_key:
        ap.error("API_FOOTBALL_KEY is not set")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{AF_BASE}/leagues", headers={"x-apisports-key": settings.api_football_key}
        )
        resp.raise_for_status()
        catalog = resp.json().get("response", [])
    # country (lowered) -> list of (af_id, af_name, af_type)
    by_country: dict[str, list[tuple[int, str, str]]] = {}
    for row in catalog:
        lg, co = row["league"], row.get("country", {})
        by_country.setdefault((co.get("name") or "").lower(), []).append(
            (lg["id"], lg["name"], lg.get("type", ""))
        )

    Session = get_sessionmaker()
    async with Session() as session:
        nulls = (
            (await session.execute(select(League).where(League.af_league_id.is_(None))))
            .scalars()
            .all()
        )
        auto, review, none = [], [], []
        by_id = {lg["league"]["id"]: lg["league"]["name"] for lg in catalog}
        for lg in sorted(nulls, key=lambda x: x.name):
            if lg.sport_key in AF_OVERRIDE:  # hand-verified — bypass fuzzy matching
                af_id = AF_OVERRIDE[lg.sport_key]
                auto.append((lg, (af_id, by_id.get(af_id, "?"), "override"), 1.0))
                continue
            af_country = COUNTRY_ALIAS.get(lg.country, lg.country)
            cands = by_country.get(af_country.lower(), [])
            best = max(cands, key=lambda c: score(lg.name, c[1]), default=None)
            s = score(lg.name, best[1]) if best else 0.0
            # A discriminator conflict (tier number, women, qualifiers…) forces REVIEW even
            # at sim=1.0 on the base name — that's the exact "Bundesliga vs Bundesliga 2" trap.
            conflict = bool(best) and discriminator_conflict(lg.name, best[1])
            if best and s >= AUTO and not conflict:
                auto.append((lg, best, s))
            elif best and (s >= MAYBE or conflict):
                review.append((lg, best, s))
            else:
                none.append((lg, best, s))

        def show(rows, tag):
            for lg, best, s in rows:
                tgt = f"{best[0]} {best[1]} [{best[2]}]" if best else "(no candidate in country)"
                print(f"  {tag}  {lg.name} ({lg.country})  ->  {tgt}   sim={s:.2f}")

        print(f"\n== AUTO ({len(auto)}) — applied with --apply ==")
        show(auto, "OK  ")
        print(f"\n== REVIEW ({len(review)}) — eyeball, set manually ==")
        show(review, "?? ")
        print(f"\n== NO MATCH ({len(none)}) — no good candidate in that country ==")
        show(none, "XX ")

        if args.apply:
            for lg, best, _ in auto:
                lg.af_league_id = best[0]
            await session.commit()
            print(f"\nApplied {len(auto)} af ids. {len(review) + len(none)} still NULL (manual).")
        else:
            print(f"\n--dry-run: nothing written. {len(auto)} would auto-apply with --apply.")


if __name__ == "__main__":
    asyncio.run(main())
