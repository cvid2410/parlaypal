"""Results resolver: populate fixtures.home_score/away_score from API-Football.

We only resolve fixtures that (a) have at least one of our signals (don't spend API calls
otherwise), (b) have kicked off, and (c) aren't scored yet. Results are matched by
(normalized home, normalized away) on the kickoff date — one API-Football call per date
covers every league that day, so no per-league id/season mapping is needed. Long-unmatched
fixtures land in review_queue for manual aliasing.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from app.config import settings
from app.models.core import Fixture, Team
from app.models.signals import Signal
from app.models.users import ReviewQueue
from app.services.cache import get_cached, get_redis, set_cached
from app.shared.db import get_sessionmaker
from app.shared.metrics import emit
from app.shared.normalize import norm_team

log = logging.getLogger("results")

AF_BASE = "https://v3.football.api-sports.io"
FINISHED = {"FT", "AET", "PEN", "AWD", "WO"}
# Only flag a fixture to review once it's well past kickoff (results lag).
REVIEW_GRACE = timedelta(hours=6)


async def _af_results_by_date(date_str: str) -> dict[tuple[str, str], tuple[int, int]]:
    """Finished API-Football fixtures for a date, indexed by (norm home, norm away).
    Cached: a past date's results are stable."""
    cache_key = f"afresults:{date_str}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return {tuple(k.split("|")): tuple(v) for k, v in cached.items()}
    if not settings.api_football_key:
        return {}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{AF_BASE}/fixtures",
            headers={"x-apisports-key": settings.api_football_key},
            params={"date": date_str, "timezone": "UTC"},
        )
        resp.raise_for_status()
        raw = resp.json().get("response", [])

    index: dict[str, list[int]] = {}
    for f in raw:
        if f["fixture"]["status"]["short"] not in FINISHED:
            continue
        goals = f.get("goals", {})
        if goals.get("home") is None or goals.get("away") is None:
            continue
        h = norm_team(f["teams"]["home"]["name"])
        a = norm_team(f["teams"]["away"]["name"])
        index[f"{h}|{a}"] = [goals["home"], goals["away"]]

    # Past dates are immutable; cache long. Today's may still be filling in.
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await set_cached(cache_key, index, ttl=900 if date_str == today else 86400)
    return {tuple(k.split("|")): tuple(v) for k, v in index.items()}


async def resolve_results() -> dict:
    now = datetime.now(timezone.utc)
    Session = get_sessionmaker()
    r = get_redis()
    stats = {"candidates": 0, "matched": 0, "review": 0}

    async with Session() as session:
        # Fixtures with signals, kicked off, not yet scored.
        rows = (await session.execute(
            select(Fixture)
            .where(
                Fixture.kickoff_utc <= now,
                Fixture.home_score.is_(None),
                Fixture.id.in_(select(Signal.fixture_id).distinct()),
            )
        )).scalars().all()
        if not rows:
            emit("results.pass", **stats)
            return stats

        # Cache the team-name lookups and per-date AF indices.
        team_name: dict[int, str] = {}

        async def name_of(team_id: int) -> str:
            if team_id not in team_name:
                team_name[team_id] = (await session.execute(
                    select(Team.name).where(Team.id == team_id)
                )).scalar_one()
            return team_name[team_id]

        date_cache: dict[str, dict] = {}
        for fx in rows:
            stats["candidates"] += 1
            date_str = fx.kickoff_utc.astimezone(timezone.utc).strftime("%Y-%m-%d")
            if date_str not in date_cache:
                date_cache[date_str] = await _af_results_by_date(date_str)
            index = date_cache[date_str]

            home = norm_team(await name_of(fx.home_id))
            away = norm_team(await name_of(fx.away_id))
            hit = index.get((home, away))
            if hit is not None:
                fx.home_score, fx.away_score = int(hit[0]), int(hit[1])
                stats["matched"] += 1
            elif now - fx.kickoff_utc > REVIEW_GRACE:
                raw = f"{home}|{away}"
                if await r.set(f"reviewed:result:{fx.id}", 1, nx=True, ex=86400):
                    session.add(ReviewQueue(
                        source="api_football", raw_name=raw, reason="result_unmatched",
                        context={"fixture_id": fx.id, "date": date_str,
                                 "home": home, "away": away},
                    ))
                    stats["review"] += 1
        await session.commit()

    emit("results.pass", **stats)
    return stats
