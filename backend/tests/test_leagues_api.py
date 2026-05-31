"""GET /api/leagues — league list + live signal counts. Requires Postgres + Redis."""
import datetime as dt
import uuid

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete

from app.ingestors.odds import _get_market_id
from app.main import app
from app.models.core import Fixture, League, Team
from app.models.signals import Signal
from app.models.users import User
from app.shared.db import get_sessionmaker
from app.shared.security import create_access_token


def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def league_with_signal():
    Session = get_sessionmaker()
    tag = uuid.uuid4().hex[:8]
    fid = f"test_fx_{tag}"
    async with Session() as s:
        lg = League(name=f"LG {tag}", country="Testland", sport_key=f"tl_{tag}",
                    is_soft=True, ingest_enabled=False)
        s.add(lg)
        await s.flush()
        h = Team(league_id=lg.id, name=f"H {tag}")
        a = Team(league_id=lg.id, name=f"A {tag}")
        s.add_all([h, a])
        await s.flush()
        s.add(Fixture(id=fid, league_id=lg.id, home_id=h.id, away_id=a.id,
                      kickoff_utc=dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)))
        mid = await _get_market_id(s, "h2h", None)
        s.add(Signal(fixture_id=fid, market_id=mid, selection="home", book="fanduel",
                     kind="ev", offered_odds=2.1, fair_prob=0.5, edge_pct=5.0, kelly_frac=0.02,
                     ttl_sec=1800, dedup_hash=f"h_{tag}", status="live"))
        user = User(email=f"lg_{tag}@x.com", tier="free")
        s.add(user)
        await s.commit()
        ids = (lg.id, fid, user.id, f"LG {tag}")
    yield {"token": create_access_token(ids[2]), "name": ids[3]}
    async with Session() as s:
        await s.execute(delete(Signal).where(Signal.fixture_id == ids[1]))
        await s.execute(delete(Fixture).where(Fixture.id == ids[1]))
        await s.execute(delete(Team).where(Team.league_id == ids[0]))
        await s.execute(delete(User).where(User.id == ids[2]))
        await s.execute(delete(League).where(League.id == ids[0]))
        await s.commit()


async def test_leagues_lists_with_live_counts(league_with_signal):
    async with _client() as c:
        r = await c.get("/api/leagues", headers={"Authorization": f"Bearer {league_with_signal['token']}"})
    assert r.status_code == 200
    d = r.json()
    mine = next(l for l in d["leagues"] if l["name"] == league_with_signal["name"])
    assert mine["live_signals"] == 1
    assert mine["is_soft"] is True
    assert d["live_total"] >= 1


async def test_leagues_requires_auth():
    async with _client() as c:
        assert (await c.get("/api/leagues")).status_code == 401
