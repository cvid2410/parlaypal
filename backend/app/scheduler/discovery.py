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


def is_soccer_match_sport(s: dict) -> bool:
    """Soccer, and a match market (not a pure outright/futures like *_winner)."""
    return s.get("group") == "Soccer" and not s.get("key", "").endswith("_winner")


def classify(key: str, title: str) -> tuple[str, str, bool]:
    """(name, country, is_soft) from a sport entry. Titles are often 'League - Country'."""
    name, country = title, ""
    if " - " in title:
        name, country = (p.strip() for p in title.split(" - ", 1))
    return name, country, key not in SHARP_KEYS


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
    stats = {"active": len(active_keys), "added": 0, "enabled": 0, "disabled": 0}

    Session = get_sessionmaker()
    async with Session() as session:
        existing = {lg.sport_key: lg for lg in (
            await session.execute(select(League))
        ).scalars().all()}

        for s in active:
            lg = existing.get(s["key"])
            if lg is not None:
                if not lg.ingest_enabled:
                    lg.ingest_enabled = True
                    stats["enabled"] += 1
                continue
            name, country, is_soft = classify(s["key"], s["title"])
            session.add(League(
                name=name, country=country, sport_key=s["key"],
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
