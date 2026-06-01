"""Kickoff-aware polling: tier logic (pure) + due-league selection (integration)."""

import datetime as dt
import time
import uuid

import pytest

from app.config import settings
from app.ingestors.odds import _due_leagues, league_tier, tier_cadence
from app.models.core import Fixture, League, Team
from app.services.cache import get_redis
from app.shared.db import get_sessionmaker

NOW = dt.datetime(2026, 6, 1, 12, 0, tzinfo=dt.UTC)


def test_league_tier():
    # In-play game → fast regardless of next kickoff.
    assert league_tier(True, None, NOW) == "fast"
    # Kicks off in 30 min (≤ 75) → fast.
    assert league_tier(False, NOW + dt.timedelta(minutes=30), NOW) == "fast"
    # Later today (≤ 12h) → medium.
    assert league_tier(False, NOW + dt.timedelta(hours=5), NOW) == "medium"
    # Far out → slow.
    assert league_tier(False, NOW + dt.timedelta(hours=20), NOW) == "slow"
    # Nothing scheduled → slow.
    assert league_tier(False, None, NOW) == "slow"


def test_tier_cadence_ordering():
    assert tier_cadence("fast") <= tier_cadence("medium") <= tier_cadence("slow")
    assert tier_cadence("fast") == settings.poll_fast_seconds


@pytest.fixture
async def league_soon():
    """A league with a fixture kicking off in 30 min (→ fast tier)."""
    Session = get_sessionmaker()
    tag = uuid.uuid4().hex[:8]
    async with Session() as s:
        lg = League(
            name=f"P {tag}", country="T", sport_key=f"tl_{tag}", is_soft=True, ingest_enabled=True
        )
        s.add(lg)
        await s.flush()
        h = Team(league_id=lg.id, name=f"H {tag}")
        a = Team(league_id=lg.id, name=f"A {tag}")
        s.add_all([h, a])
        await s.flush()
        s.add(
            Fixture(
                id=f"pf_{tag}",
                league_id=lg.id,
                home_id=h.id,
                away_id=a.id,
                kickoff_utc=dt.datetime.now(dt.UTC) + dt.timedelta(minutes=30),
            )
        )
        await s.commit()
        lg_id = lg.id
    yield lg_id
    async with Session() as s:
        from sqlalchemy import delete

        await s.execute(delete(Fixture).where(Fixture.league_id == lg_id))
        await s.execute(delete(Team).where(Team.league_id == lg_id))
        await s.execute(delete(League).where(League.id == lg_id))
        await s.commit()
    await get_redis().delete(f"lastpoll:{lg_id}")


async def test_due_leagues_respects_last_poll(league_soon):
    Session = get_sessionmaker()
    r = get_redis()
    await r.delete(f"lastpoll:{league_soon}")
    now = dt.datetime.now(dt.UTC)
    async with Session() as s:
        lg = (
            await s.execute(__import__("sqlalchemy").select(League).where(League.id == league_soon))
        ).scalar_one()

        # Never polled → due.
        due = await _due_leagues(s, r, [lg], now)
        assert lg in due

        # Just polled → not due (within the fast cadence).
        await r.set(f"lastpoll:{league_soon}", time.time())
        assert lg not in await _due_leagues(s, r, [lg], now)

        # Polled long ago → due again.
        await r.set(f"lastpoll:{league_soon}", time.time() - settings.poll_fast_seconds - 5)
        assert lg in await _due_leagues(s, r, [lg], now)
