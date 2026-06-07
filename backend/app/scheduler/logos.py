"""Backfill team crest URLs from API-Football.

Only resolves teams that appear in a fixture with one of our signals (so we don't spend
API calls on teams we never display). Matches by normalized name within the fixture's
kickoff date - AF's fixtures for that date list every team playing, with its logo. Reuses
the same cached day fetch as the results resolver and Scores.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC

from sqlalchemy import select

from app.models.core import Fixture, Team
from app.models.signals import Signal
from app.services.af import fixtures_by_date
from app.shared.db import get_sessionmaker
from app.shared.metrics import emit
from app.shared.normalize import norm_team

log = logging.getLogger("logos")


async def resolve_team_logos() -> dict:
    Session = get_sessionmaker()
    stats = {"candidates": 0, "matched": 0}

    async with Session() as session:
        fixtures = (
            (
                await session.execute(
                    select(Fixture).where(Fixture.id.in_(select(Signal.fixture_id).distinct()))
                )
            )
            .scalars()
            .all()
        )
        if not fixtures:
            emit("logos.pass", **stats)
            return stats

        # team_id -> a date we can look it up on
        team_date: dict[int, str] = {}
        team_ids: set[int] = set()
        for fx in fixtures:
            d = fx.kickoff_utc.astimezone(UTC).strftime("%Y-%m-%d")
            team_date.setdefault(fx.home_id, d)
            team_date.setdefault(fx.away_id, d)
            team_ids.update((fx.home_id, fx.away_id))

        teams = (
            (await session.execute(select(Team).where(Team.id.in_(team_ids), Team.logo.is_(None))))
            .scalars()
            .all()
        )
        stats["candidates"] = len(teams)

        by_date: dict[str, list[Team]] = defaultdict(list)
        for t in teams:
            by_date[team_date[t.id]].append(t)

        for date_str, date_teams in by_date.items():
            index: dict[str, str] = {}
            for f in await fixtures_by_date(date_str):
                for side in ("home", "away"):
                    logo = f["teams"][side].get("logo")
                    if logo:
                        index[norm_team(f["teams"][side]["name"])] = logo
            for t in date_teams:
                logo = index.get(norm_team(t.name))
                if logo:
                    t.logo = logo
                    stats["matched"] += 1
        await session.commit()

    emit("logos.pass", **stats)
    return stats
