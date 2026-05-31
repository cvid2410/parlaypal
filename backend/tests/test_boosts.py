"""Boost/promo injection. Requires Postgres + Redis."""

import datetime as dt
import uuid

import pytest
from sqlalchemy import delete, select

from app.ingestors.odds import _get_market_id
from app.models.core import Fixture, League, Team
from app.models.signals import Signal
from app.services.cache import get_redis
from app.shared.db import get_sessionmaker
from app.workers.boosts import inject_boost


@pytest.fixture
async def world():
    Session = get_sessionmaker()
    r = get_redis()
    tag = uuid.uuid4().hex[:8]
    fid = f"test_fx_{tag}"
    async with Session() as s:
        lg = League(
            name=f"B {tag}", country="X", sport_key=f"tl_{tag}", is_soft=False, ingest_enabled=False
        )  # promo works on sharp leagues too
        s.add(lg)
        await s.flush()
        h = Team(league_id=lg.id, name=f"H {tag}")
        a = Team(league_id=lg.id, name=f"A {tag}")
        s.add_all([h, a])
        await s.flush()
        s.add(
            Fixture(
                id=fid,
                league_id=lg.id,
                home_id=h.id,
                away_id=a.id,
                kickoff_utc=dt.datetime(2026, 6, 1, tzinfo=dt.UTC),
            )
        )
        mid = await _get_market_id(s, "h2h", None)
        await s.commit()
        league_id = lg.id
    # Pinnacle fair (home ~0.526). Boost will price home far above fair.
    await r.delete(f"odds:{fid}:{mid}")
    await r.hset(
        f"odds:{fid}:{mid}",
        mapping={
            "pinnacle:home": 1.8,
            "pinnacle:draw": 3.6,
            "pinnacle:away": 4.5,
        },
    )
    yield {"fid": fid, "league_id": league_id}
    async with Session() as s:
        await s.execute(delete(Signal).where(Signal.fixture_id == fid))
        await s.execute(delete(Fixture).where(Fixture.id == fid))
        await s.execute(delete(Team).where(Team.league_id == league_id))
        await s.execute(delete(League).where(League.id == league_id))
        await s.commit()
    async for k in r.scan_iter(match=f"*{tag}*"):
        await r.delete(k)
    async for k in r.scan_iter(match=f"*{fid}*"):
        await r.delete(k)


async def test_boost_emits_promo_when_plus_ev(world):
    # Boost home to +150 (2.5 dec); fair ~0.526 → ~+31% edge.
    out = await inject_boost(world["fid"], "h2h", None, "home", "fanduel", 150)
    assert out["emitted"] is True
    assert out["edge_pct"] > 20
    async with get_sessionmaker()() as s:
        sig = (
            await s.execute(
                select(Signal).where(Signal.fixture_id == world["fid"], Signal.kind == "promo")
            )
        ).scalar_one()
    assert sig.book == "fanduel"
    assert sig.meta["boost"] is True


async def test_junk_boost_not_emitted(world):
    # Boost home to only -200 (1.5 dec) — below fair → not +EV → skipped.
    out = await inject_boost(world["fid"], "h2h", None, "home", "fanduel", -200)
    assert out["emitted"] is False
