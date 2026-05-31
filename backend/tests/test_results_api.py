"""GET /api/results aggregation. Requires Postgres + Redis."""

import datetime as dt
import uuid

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete

from app.ingestors.odds import _get_market_id
from app.main import app
from app.models.core import Fixture, League, Team
from app.models.signals import Signal, SignalGrade
from app.models.users import User
from app.shared.db import get_sessionmaker
from app.shared.security import create_access_token


def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def graded_world():
    Session = get_sessionmaker()
    tag = uuid.uuid4().hex[:8]
    fid = f"test_fx_{tag}"
    async with Session() as s:
        lg = League(
            name=f"TR {tag}",
            country="Testland",
            sport_key=f"tl_{tag}",
            is_soft=True,
            ingest_enabled=False,
        )
        s.add(lg)
        await s.flush()
        h = Team(league_id=lg.id, name=f"Home {tag}")
        a = Team(league_id=lg.id, name=f"Away {tag}")
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
        # three settled EV signals: 2 wins (CLV beat) + 1 loss (no CLV beat)
        specs = [
            ("home", 2.35, True, "win", 1.35),
            ("away", 1.90, False, "loss", -1.0),
            ("draw", 1.80, True, "win", 0.80),
        ]
        sig_ids = []
        for sel, odds, beat, result, pnl in specs:
            sig = Signal(
                fixture_id=fid,
                market_id=mid,
                selection=sel,
                book="fanduel",
                kind="ev",
                offered_odds=odds,
                fair_prob=0.5,
                edge_pct=5.0,
                kelly_frac=0.02,
                ttl_sec=1800,
                dedup_hash=f"{tag}_{sel}",
                status="settled",
            )
            s.add(sig)
            await s.flush()
            s.add(
                SignalGrade(
                    signal_id=sig.id,
                    closing_odds=odds - 0.1,
                    beat_clv=beat,
                    result=result,
                    pnl_units=pnl,
                )
            )
            sig_ids.append(sig.id)
        user = User(email=f"tr_{tag}@x.com", tier="bettor")
        s.add(user)
        await s.commit()
        ids = (lg.id, fid, [*sig_ids], user.id)
    yield {"token": create_access_token(ids[3]), "league": f"TR {tag}"}
    async with Session() as s:
        await s.execute(delete(SignalGrade).where(SignalGrade.signal_id.in_(ids[2])))
        await s.execute(delete(Signal).where(Signal.fixture_id == ids[1]))
        await s.execute(delete(Fixture).where(Fixture.id == ids[1]))
        await s.execute(delete(Team).where(Team.league_id == ids[0]))
        await s.execute(delete(User).where(User.id == ids[3]))
        await s.execute(delete(League).where(League.id == ids[0]))
        await s.commit()


async def test_results_aggregates(graded_world):
    async with _client() as c:
        r = await c.get(
            "/api/results", headers={"Authorization": f"Bearer {graded_world['token']}"}
        )
    assert r.status_code == 200
    d = r.json()
    # CLV: 2 of 3 beat → 66.7%
    assert d["clv_sample"] >= 3
    # win rate 2/3 of decided
    assert d["wins"] >= 2 and d["losses"] >= 1
    # our three contribute +1.15u; curve advances per settled signal
    assert len(d["curve"]) >= 3
    assert any(item["league"] == graded_world["league"] for item in d["recent"])


async def test_results_requires_auth():
    async with _client() as c:
        assert (await c.get("/api/results")).status_code == 401
