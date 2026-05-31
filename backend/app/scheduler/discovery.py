"""Dynamic sport-key discovery.

Competitions come and go — friendlies (international breaks / pre-season), cups, qualifiers,
seasonal leagues. Instead of a static seed, this pulls The Odds API's active sports list and:
  - registers any new active soccer competition as a league (is_soft by default; known sharp
    keys flagged is_soft=false),
  - enables active leagues, disables dormant (off-season) ones — so polling tracks what's
    actually live.

Existing leagues' manual config (is_soft, af_league_id, name) is preserved — only
`ingest_enabled` is toggled. New leagues still route +EV through the CLV gate before users.
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy import select

from app.config import settings
from app.models.core import League
from app.shared.db import get_sessionmaker
from app.shared.metrics import emit

log = logging.getLogger("discovery")

THE_ODDS_BASE = "https://api.the-odds-api.com/v4"

# Sharp / efficient markets: ingested for arb/best-price/Scores but NOT classic +EV.
SHARP_KEYS = {
    "soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a",
    "soccer_germany_bundesliga", "soccer_france_ligue_one",
    "soccer_uefa_champs_league", "soccer_uefa_europa_league",
    "soccer_uefa_europa_conference_league", "soccer_fifa_world_cup",
    "soccer_uefa_european_championship", "soccer_uefa_nations_league",
}

# Curated (name, country) for The Odds API soccer keys — tidies the Leagues tab. Unknown
# keys (e.g. future friendlies) fall back to parsing the API title.
KEY_META: dict[str, tuple[str, str]] = {
    # domestic leagues
    "soccer_argentina_primera_division": ("Primera División", "Argentina"),
    "soccer_australia_aleague": ("A-League", "Australia"),
    "soccer_austria_bundesliga": ("Bundesliga", "Austria"),
    "soccer_belgium_first_div": ("First Division A", "Belgium"),
    "soccer_brazil_campeonato": ("Série A", "Brazil"),
    "soccer_brazil_serie_b": ("Série B", "Brazil"),
    "soccer_chile_campeonato": ("Primera División", "Chile"),
    "soccer_china_superleague": ("Super League", "China"),
    "soccer_denmark_superliga": ("Superliga", "Denmark"),
    "soccer_efl_champ": ("Championship", "England"),
    "soccer_england_league1": ("League One", "England"),
    "soccer_england_league2": ("League Two", "England"),
    "soccer_epl": ("Premier League", "England"),
    "soccer_finland_veikkausliiga": ("Veikkausliiga", "Finland"),
    "soccer_france_ligue_one": ("Ligue 1", "France"),
    "soccer_france_ligue_two": ("Ligue 2", "France"),
    "soccer_germany_bundesliga": ("Bundesliga", "Germany"),
    "soccer_germany_bundesliga2": ("2. Bundesliga", "Germany"),
    "soccer_germany_bundesliga_women": ("Frauen-Bundesliga", "Germany"),
    "soccer_germany_liga3": ("3. Liga", "Germany"),
    "soccer_greece_super_league": ("Super League", "Greece"),
    "soccer_italy_serie_a": ("Serie A", "Italy"),
    "soccer_italy_serie_b": ("Serie B", "Italy"),
    "soccer_japan_j_league": ("J1 League", "Japan"),
    "soccer_korea_kleague1": ("K League 1", "South Korea"),
    "soccer_league_of_ireland": ("Premier Division", "Ireland"),
    "soccer_mexico_ligamx": ("Liga MX", "Mexico"),
    "soccer_netherlands_eredivisie": ("Eredivisie", "Netherlands"),
    "soccer_norway_eliteserien": ("Eliteserien", "Norway"),
    "soccer_poland_ekstraklasa": ("Ekstraklasa", "Poland"),
    "soccer_portugal_primeira_liga": ("Primeira Liga", "Portugal"),
    "soccer_russia_premier_league": ("Premier League", "Russia"),
    "soccer_saudi_arabia_pro_league": ("Pro League", "Saudi Arabia"),
    "soccer_spain_la_liga": ("La Liga", "Spain"),
    "soccer_spain_segunda_division": ("La Liga 2", "Spain"),
    "soccer_spl": ("Premiership", "Scotland"),
    "soccer_sweden_allsvenskan": ("Allsvenskan", "Sweden"),
    "soccer_sweden_superettan": ("Superettan", "Sweden"),
    "soccer_switzerland_superleague": ("Super League", "Switzerland"),
    "soccer_turkey_super_league": ("Süper Lig", "Turkey"),
    "soccer_usa_mls": ("MLS", "USA"),
    # domestic cups
    "soccer_england_efl_cup": ("EFL Cup", "England"),
    "soccer_fa_cup": ("FA Cup", "England"),
    "soccer_france_coupe_de_france": ("Coupe de France", "France"),
    "soccer_germany_dfb_pokal": ("DFB-Pokal", "Germany"),
    "soccer_italy_coppa_italia": ("Coppa Italia", "Italy"),
    "soccer_spain_copa_del_rey": ("Copa del Rey", "Spain"),
    # continental / international
    "soccer_africa_cup_of_nations": ("Africa Cup of Nations", "Africa"),
    "soccer_concacaf_gold_cup": ("CONCACAF Gold Cup", "CONCACAF"),
    "soccer_concacaf_leagues_cup": ("Leagues Cup", "North America"),
    "soccer_conmebol_copa_america": ("Copa América", "CONMEBOL"),
    "soccer_conmebol_copa_libertadores": ("Copa Libertadores", "South America"),
    "soccer_conmebol_copa_sudamericana": ("Copa Sudamericana", "South America"),
    "soccer_fifa_club_world_cup": ("FIFA Club World Cup", "International"),
    "soccer_fifa_world_cup": ("FIFA World Cup", "International"),
    "soccer_fifa_world_cup_qualifiers_europe": ("World Cup Qualifiers", "Europe"),
    "soccer_fifa_world_cup_qualifiers_south_america": ("World Cup Qualifiers", "South America"),
    "soccer_fifa_world_cup_womens": ("Women's World Cup", "International"),
    "soccer_uefa_champs_league": ("Champions League", "Europe"),
    "soccer_uefa_champs_league_qualification": ("Champions League Qualifying", "Europe"),
    "soccer_uefa_champs_league_women": ("Women's Champions League", "Europe"),
    "soccer_uefa_euro_qualification": ("Euro Qualifying", "Europe"),
    "soccer_uefa_europa_conference_league": ("Conference League", "Europe"),
    "soccer_uefa_europa_league": ("Europa League", "Europe"),
    "soccer_uefa_european_championship": ("UEFA Euro", "Europe"),
    "soccer_uefa_nations_league": ("Nations League", "Europe"),
}


def is_soccer_match_sport(s: dict) -> bool:
    """Soccer, and a match market (not a pure outright/futures like *_winner)."""
    return s.get("group") == "Soccer" and not s.get("key", "").endswith("_winner")


def classify(key: str, title: str) -> tuple[str, str, bool]:
    """(name, country, is_soft). Prefer the curated map; else parse the API title
    ('League - Country')."""
    is_soft = key not in SHARP_KEYS
    if key in KEY_META:
        name, country = KEY_META[key]
        return name, country, is_soft
    name, country = title, ""
    if " - " in title:
        name, country = (p.strip() for p in title.split(" - ", 1))
    return name, country, is_soft


async def _fetch_active_sports() -> list[dict]:
    if not settings.the_odds_api_key:
        return []
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{THE_ODDS_BASE}/sports", params={"apiKey": settings.the_odds_api_key}
        )
        resp.raise_for_status()
        return resp.json()


async def discover_sports(fetch=None, manage_disable: bool = True) -> dict:
    sports = await (fetch or _fetch_active_sports)()
    active = [s for s in sports if is_soccer_match_sport(s) and s.get("active")]
    active_keys = {s["key"] for s in active}
    stats = {"active": len(active_keys), "added": 0, "enabled": 0, "disabled": 0, "tidied": 0}

    Session = get_sessionmaker()
    async with Session() as session:
        existing = {lg.sport_key: lg for lg in (
            await session.execute(select(League))
        ).scalars().all()}

        for s in active:
            key = s["key"]
            name, country, is_soft = classify(key, s["title"])
            lg = existing.get(key)
            if lg is not None:
                if not lg.ingest_enabled:
                    lg.ingest_enabled = True
                    stats["enabled"] += 1
                # Normalize name/country from the curated map (preserve manual is_soft).
                if key in KEY_META and (lg.name, lg.country) != (name, country):
                    lg.name, lg.country = name, country
                    stats["tidied"] += 1
                continue
            session.add(League(
                name=name, country=country, sport_key=key,
                sharp_ref_book="pinnacle", is_soft=is_soft, model_enabled=False,
                ingest_enabled=True,
            ))
            stats["added"] += 1

        if manage_disable:
            for key, lg in existing.items():
                if lg.ingest_enabled and key not in active_keys:
                    lg.ingest_enabled = False
                    stats["disabled"] += 1

        await session.commit()

    emit("discovery.pass", **stats)
    return stats
