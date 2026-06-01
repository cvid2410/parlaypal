"""Integration test for the detection consumer. Requires Postgres + Redis (run in the
compose stack). Creates an isolated soft league/fixture/market, drives hot state, and
asserts the signal + dedup + re-alert-on-improvement behaviour, then cleans up.
"""

import datetime as dt
import uuid

import pytest
from sqlalchemy import delete, select

from app.ingestors.odds import _get_market_id
from app.models.core import Fixture, League, Team
from app.models.signals import Signal
from app.services.cache import get_redis
from app.shared.db import get_sessionmaker
from app.workers.detect import detect_market


@pytest.fixture
async def scenario():
    """A soft league with a fixture and an h2h market; yields (fixture_id, market_id)."""
    Session = get_sessionmaker()
    r = get_redis()
    fid = f"test_fx_{uuid.uuid4().hex[:8]}"
    sport_key = f"test_league_{uuid.uuid4().hex[:8]}"
    async with Session() as s:
        lg = League(
            name="Test",
            country="Testland",
            sport_key=sport_key,
            sharp_ref_book="pinnacle",
            is_soft=True,
            ingest_enabled=False,
        )
        s.add(lg)
        await s.flush()
        home = Team(league_id=lg.id, name=f"Home {fid}")
        away = Team(league_id=lg.id, name=f"Away {fid}")
        s.add_all([home, away])
        await s.flush()
        s.add(
            Fixture(
                id=fid,
                league_id=lg.id,
                home_id=home.id,
                away_id=away.id,
                kickoff_utc=__import__("datetime").datetime(
                    2026, 6, 1, tzinfo=__import__("datetime").timezone.utc
                ),
            )
        )
        mid = await _get_market_id(s, "h2h", None)
        await s.commit()
        league_id = lg.id

    yield fid, mid

    # cleanup
    async with Session() as s:
        await s.execute(delete(Signal).where(Signal.fixture_id == fid))
        await s.execute(delete(Fixture).where(Fixture.id == fid))
        await s.execute(delete(Team).where(Team.league_id == league_id))
        await s.execute(delete(League).where(League.id == league_id))
        await s.commit()
    async for key in r.scan_iter(match=f"*{fid}*"):
        await r.delete(key)


async def _hot(r, fid, mid, mapping):
    await r.delete(f"odds:{fid}:{mid}")
    await r.hset(f"odds:{fid}:{mid}", mapping=mapping)


async def _signals(fid):
    async with get_sessionmaker()() as s:
        return (await s.execute(select(Signal).where(Signal.fixture_id == fid))).scalars().all()


async def test_ev_signal_dedup_and_improvement(scenario):
    fid, mid = scenario
    r = get_redis()

    # Shin devig of (1.8, 3.6, 4.5) → home fair ~0.534. FanDuel home at 2.2 is +EV (~17.5%).
    # (The multiplicative method gives ~0.526 / 15.8%; Shin pulls the favourite up — see
    # the devig_method default in config, set to 'shin'.)
    await _hot(
        r,
        fid,
        mid,
        {
            "pinnacle:home": 1.8,
            "pinnacle:draw": 3.6,
            "pinnacle:away": 4.5,
            "fanduel:home": 2.2,
            "fanduel:draw": 3.5,
            "fanduel:away": 3.4,
        },
    )
    await detect_market({}, fid, mid)
    sigs = await _signals(fid)
    ev = [x for x in sigs if x.kind == "ev" and x.selection == "home" and x.book == "fanduel"]
    assert len(ev) == 1
    assert ev[0].edge_pct == pytest.approx(17.54, abs=0.5)
    assert ev[0].kelly_frac > 0

    # Flap within the same edge bucket → no new signal.
    await detect_market({}, fid, mid)
    assert len([x for x in await _signals(fid) if x.kind == "ev" and x.selection == "home"]) == 1

    # Edge improves to a higher bucket → exactly one more signal.
    await r.hset(f"odds:{fid}:{mid}", "fanduel:home", "2.5")
    await detect_market({}, fid, mid)
    assert len([x for x in await _signals(fid) if x.kind == "ev" and x.selection == "home"]) == 2


async def test_sharp_league_gets_arb_not_ev():
    """On a non-soft (big/sharp) league: arb still fires, but EV never does — even when a
    soft book looks mispriced vs Pinnacle."""
    Session = get_sessionmaker()
    r = get_redis()
    tag = uuid.uuid4().hex[:8]
    fid = f"test_fx_{tag}"
    async with Session() as s:
        lg = League(
            name=f"Sharp {tag}",
            country="X",
            sport_key=f"tl_{tag}",
            sharp_ref_book="pinnacle",
            is_soft=False,
            ingest_enabled=True,
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
        await s.commit()
        league_id = lg.id
    try:
        # Pinnacle fair + a FanDuel home at 2.2 (would be +EV on a soft league). Best prices
        # across books also leave an arb gap (1/2.2 + 1/3.6 + 1/4.5 < 1).
        await r.delete(f"odds:{fid}:{mid}")
        await r.hset(
            f"odds:{fid}:{mid}",
            mapping={
                "pinnacle:home": 1.8,
                "pinnacle:draw": 3.6,
                "pinnacle:away": 4.5,
                "fanduel:home": 2.2,
                "fanduel:draw": 3.6,
                "betmgm:away": 4.5,
            },
        )
        await detect_market({}, fid, mid)
        async with Session() as s:
            sigs = (await s.execute(select(Signal).where(Signal.fixture_id == fid))).scalars().all()
        assert not any(x.kind == "ev" for x in sigs), "EV must not fire on a sharp league"
        assert any(x.kind == "arb" for x in sigs), "arb should still fire on a sharp league"
    finally:
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


async def test_arb_detected(scenario):
    fid, mid = scenario
    r = get_redis()
    # Best price per outcome across books: 1/3.0 + 1/4.0 + 1/4.0 = 0.833 < 1 → arb.
    await _hot(
        r,
        fid,
        mid,
        {
            "pinnacle:home": 3.0,
            "pinnacle:draw": 2.0,
            "pinnacle:away": 2.0,
            "fanduel:draw": 4.0,
            "betmgm:away": 4.0,
        },
    )
    await detect_market({}, fid, mid)
    arbs = [x for x in await _signals(fid) if x.kind == "arb"]
    assert len(arbs) == 1
    assert arbs[0].edge_pct > 0
    assert "legs" in arbs[0].meta
