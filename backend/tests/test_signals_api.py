"""Tier gating for GET /api/signals. Requires Postgres + Redis."""

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
async def world():
    Session = get_sessionmaker()
    tag = uuid.uuid4().hex[:8]
    fid = f"test_fx_{tag}"
    async with Session() as s:
        lg = League(
            name="Test",
            country="Testland",
            sport_key=f"tl_{tag}",
            is_soft=True,
            ingest_enabled=False,
            ev_certified=True,
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
        s.add(
            Signal(
                fixture_id=fid,
                market_id=mid,
                selection="home",
                book="fanduel",
                kind="ev",
                offered_odds=2.35,
                fair_prob=0.5,
                edge_pct=9.1,
                kelly_frac=0.03,
                ttl_sec=1800,
                dedup_hash=f"h_{tag}",
                status="live",
            )
        )
        free = User(email=f"free_{tag}@x.com", tier="free")
        paid = User(email=f"paid_{tag}@x.com", tier="bettor")
        s.add_all([free, paid])
        await s.commit()
        ids = (lg.id, fid, free.id, paid.id)
    yield {
        "league_id": ids[0],
        "fid": ids[1],
        "free_token": create_access_token(ids[2]),
        "paid_token": create_access_token(ids[3]),
        "free_id": ids[2],
        "paid_id": ids[3],
    }
    async with Session() as s:
        await s.execute(delete(Signal).where(Signal.fixture_id == fid))
        await s.execute(delete(Fixture).where(Fixture.id == fid))
        await s.execute(delete(Team).where(Team.league_id == ids[0]))
        await s.execute(delete(User).where(User.id.in_([ids[2], ids[3]])))
        await s.execute(delete(League).where(League.id == ids[0]))
        await s.commit()


def _find(cards, fid):
    return [c for c in cards if c["fixture"] and fid]  # fixture label present


async def test_paid_sees_full_signal(world):
    async with _client() as c:
        r = await c.get("/api/signals", headers={"Authorization": f"Bearer {world['paid_token']}"})
    assert r.status_code == 200
    data = r.json()
    assert data["tier"] == "bettor"
    card = next(s for s in data["signals"] if s["country"] == "Testland")
    assert card["locked"] is False
    assert card["book"] == "FanDuel"
    assert card["odds"] == "+135"
    assert "body" in card and "9.1%" in card["body"]


async def test_free_sees_locked_teaser(world):
    async with _client() as c:
        r = await c.get("/api/signals", headers={"Authorization": f"Bearer {world['free_token']}"})
    assert r.status_code == 200
    data = r.json()
    assert data["tier"] == "free"
    card = next(s for s in data["signals"] if s["country"] == "Testland")
    assert card["locked"] is True
    assert "unlock" in card["title"].lower()
    # No edge leaks: pick / book / odds / body absent.
    assert "book" not in card and "odds" not in card and "body" not in card


async def test_signals_requires_auth():
    async with _client() as c:
        assert (await c.get("/api/signals")).status_code == 401


async def test_uncertified_ev_hidden_arb_shown():
    """+EV on an UNcertified league must not appear at all (NON-NEGOTIABLE #2) — not even as
    a teaser, since it's not a proven edge. Arb on the same league still shows (mechanical)."""
    Session = get_sessionmaker()
    tag = uuid.uuid4().hex[:8]
    fid = f"test_fx_{tag}"
    async with Session() as s:
        lg = League(
            name="Unc",
            country="Uncertia",
            sport_key=f"tl_{tag}",
            is_soft=True,
            ingest_enabled=False,
            ev_certified=False,
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
        mid = await _get_market_id(s, "h2h", None)
        s.add_all(
            [
                Signal(
                    fixture_id=fid,
                    market_id=mid,
                    selection="home",
                    book="fanduel",
                    kind="ev",
                    offered_odds=2.2,
                    fair_prob=0.5,
                    edge_pct=10.0,
                    kelly_frac=0.05,
                    ttl_sec=1800,
                    dedup_hash=f"ev_{tag}",
                    status="live",
                ),
                Signal(
                    fixture_id=fid,
                    market_id=mid,
                    selection="home+away",
                    book="multi",
                    kind="arb",
                    offered_odds=0.0,
                    fair_prob=0.0,
                    edge_pct=2.0,
                    kelly_frac=0.0,
                    ttl_sec=1800,
                    dedup_hash=f"arb_{tag}",
                    status="live",
                    meta={
                        "legs": {
                            "home": {"book": "betmgm", "odds": 2.1, "stake_frac": 0.5},
                            "away": {"book": "fanduel", "odds": 2.1, "stake_frac": 0.5},
                        }
                    },
                ),
            ]
        )
        paid = User(email=f"p_{tag}@x.com", tier="bettor")
        s.add(paid)
        await s.commit()
        league_id, uid = lg.id, paid.id
    try:
        token = create_access_token(uid)
        async with _client() as c:
            r = await c.get("/api/signals", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        kinds = [s["kind"] for s in r.json()["signals"] if s.get("country") == "Uncertia"]
        assert "ev" not in kinds, "uncertified +EV must be hidden"
        assert "arb" in kinds, "arb is mechanical and must still show"
    finally:
        async with Session() as s:
            await s.execute(delete(Signal).where(Signal.fixture_id == fid))
            await s.execute(delete(Fixture).where(Fixture.id == fid))
            await s.execute(delete(Team).where(Team.league_id == league_id))
            await s.execute(delete(User).where(User.id == uid))
            await s.execute(delete(League).where(League.id == league_id))
            await s.commit()
