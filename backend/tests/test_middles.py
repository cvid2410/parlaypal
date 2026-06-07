"""Integration test for the cross-market middle detector. Requires Postgres + Redis."""

import datetime as dt
import uuid

import pytest
from sqlalchemy import delete, select

from app.ingestors.odds import _get_market_id
from app.models.core import Fixture, League, Team
from app.models.signals import Signal
from app.services.cache import get_redis
from app.shared.db import get_sessionmaker
from app.workers.middles import detect_middles


@pytest.fixture
async def totals_world():
    """A fixture with two totals markets (1.5 and 2.5) wired in Redis hot state."""
    Session = get_sessionmaker()
    r = get_redis()
    tag = uuid.uuid4().hex[:8]
    fid = f"test_fx_{tag}"
    async with Session() as s:
        lg = League(
            name=f"M {tag}", country="X", sport_key=f"tl_{tag}", is_soft=True, ingest_enabled=False
        )
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
        m15 = await _get_market_id(s, "total", 1.5)
        m25 = await _get_market_id(s, "total", 2.5)
        await s.commit()
        league_id = lg.id

    # Over 1.5 @ 2.0 (DK) and Under 2.5 @ 2.0 (MGM) → middle on total = 2.
    await r.delete(f"odds:{fid}:{m15}", f"odds:{fid}:{m25}", f"fxtotals:{fid}")
    await r.hset(f"odds:{fid}:{m15}", mapping={"draftkings:over": 2.0, "draftkings:under": 1.8})
    await r.hset(f"odds:{fid}:{m25}", mapping={"betmgm:under": 2.0, "betmgm:over": 1.8})
    await r.sadd(f"fxtotals:{fid}", m15, m25)

    yield {"fid": fid, "m15": m15, "m25": m25}

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


async def test_middle_detected(totals_world):
    fid = totals_world["fid"]
    out = await detect_middles({}, fid)
    assert out["middle"] == 1
    async with get_sessionmaker()() as s:
        sigs = (await s.execute(select(Signal).where(Signal.fixture_id == fid))).scalars().all()
    middle = next(x for x in sigs if x.kind == "middle")
    assert middle.edge_pct == pytest.approx(100.0)  # free middle (s=1.0)
    assert middle.meta["window"] == [2]
    assert set(middle.meta["legs"]) == {"over", "under"}


async def test_middle_invalidated_when_gap_closes(totals_world):
    """Once a totals leg moves and the middle no longer exists, the stale middle is expired on
    the next detection (not left sitting out the TTL)."""
    fid, m25 = totals_world["fid"], totals_world["m25"]
    r = get_redis()
    await detect_middles({}, fid)
    async with get_sessionmaker()() as s:
        rows = (await s.execute(select(Signal).where(Signal.fixture_id == fid))).scalars().all()
    live = [x for x in rows if x.kind == "middle"]
    assert len(live) == 1 and live[0].status == "live"

    # The Under 2.5 leg vanishes (book pulls it) → no middle exists. Re-detection expires it.
    await r.hdel(f"odds:{fid}:{m25}", "betmgm:under")
    await detect_middles({}, fid)
    async with get_sessionmaker()() as s:
        rows = (await s.execute(select(Signal).where(Signal.fixture_id == fid))).scalars().all()
    mids = [x for x in rows if x.kind == "middle"]
    assert len(mids) == 1
    assert mids[0].status == "expired"
