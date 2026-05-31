"""Integration test for settlement + CLV grading. Requires Postgres + Redis."""
import datetime as dt
import uuid

import pytest
from sqlalchemy import delete, select

from app.ingestors.odds import _get_market_id
from app.models.core import Fixture, League, Team
from app.models.odds import OddsSnapshot
from app.models.signals import Signal, SignalGrade
from app.scheduler.settle import settle_once
from app.shared.clv import clv_report_by_league
from app.shared.db import ensure_daily_partition, get_sessionmaker


@pytest.fixture
async def settled_world():
    """A soft league with a past-kickoff fixture, an EV signal, and a closing Pinnacle line."""
    Session = get_sessionmaker()
    tag = uuid.uuid4().hex[:8]
    fid = f"test_fx_{tag}"
    kickoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
    await ensure_daily_partition(kickoff)
    async with Session() as s:
        lg = League(name=f"Test {tag}", country="Testland", sport_key=f"tl_{tag}",
                    sharp_ref_book="pinnacle", is_soft=True, ingest_enabled=False)
        s.add(lg)
        await s.flush()
        h = Team(league_id=lg.id, name=f"Home {tag}")
        a = Team(league_id=lg.id, name=f"Away {tag}")
        s.add_all([h, a])
        await s.flush()
        s.add(Fixture(id=fid, league_id=lg.id, home_id=h.id, away_id=a.id, kickoff_utc=kickoff))
        mid = await _get_market_id(s, "h2h", None)
        sig = Signal(fixture_id=fid, market_id=mid, selection="home", book="fanduel",
                     kind="ev", offered_odds=2.35, fair_prob=0.5, edge_pct=9.1,
                     kelly_frac=0.03, ttl_sec=1800, dedup_hash=f"h_{tag}", status="live")
        s.add(sig)
        # Closing Pinnacle line for 'home' = 2.20 (we alerted 2.35 → we beat closing).
        s.add(OddsSnapshot(fixture_id=fid, book="pinnacle", market_id=mid, selection="home",
                           decimal_odds=2.20, ts=kickoff - dt.timedelta(minutes=5)))
        await s.commit()
        ids = (lg.id, fid, sig.id, mid)
    yield {"league_id": ids[0], "fid": ids[1], "sig_id": ids[2], "mid": ids[3], "kickoff": kickoff}
    async with Session() as s:
        await s.execute(delete(SignalGrade).where(SignalGrade.signal_id == ids[2]))
        await s.execute(delete(Signal).where(Signal.id == ids[2]))
        await s.execute(delete(OddsSnapshot).where(OddsSnapshot.fixture_id == ids[1]))
        await s.execute(delete(Fixture).where(Fixture.id == ids[1]))
        await s.execute(delete(Team).where(Team.league_id == ids[0]))
        await s.execute(delete(League).where(League.id == ids[0]))
        await s.commit()


async def _grade(sig_id):
    async with get_sessionmaker()() as s:
        return (await s.execute(select(SignalGrade).where(SignalGrade.signal_id == sig_id))).scalar_one_or_none()


async def _signal(sig_id):
    async with get_sessionmaker()() as s:
        return (await s.execute(select(Signal).where(Signal.id == sig_id))).scalar_one()


async def test_clv_graded_at_kickoff_before_score(settled_world):
    stats = await settle_once()
    assert stats["graded"] >= 1
    g = await _grade(settled_world["sig_id"])
    assert g is not None
    assert g.closing_odds == pytest.approx(2.20)
    assert g.beat_clv is True       # 2.35 > 2.20
    assert g.result is None          # no score yet
    assert (await _signal(settled_world["sig_id"])).status == "expired"


async def test_result_and_pnl_after_score(settled_world):
    await settle_once()  # CLV first
    async with get_sessionmaker()() as s:
        fx = (await s.execute(select(Fixture).where(Fixture.id == settled_world["fid"]))).scalar_one()
        fx.home_score, fx.away_score = 2, 1  # home wins → our 'home' pick wins
        await s.commit()
    await settle_once()  # now grades result
    g = await _grade(settled_world["sig_id"])
    assert g.result == "win"
    assert g.pnl_units == pytest.approx(1.35)  # (2.35 - 1) * 1u
    assert g.beat_clv is True
    assert (await _signal(settled_world["sig_id"])).status == "settled"


async def test_clv_report_includes_league(settled_world):
    await settle_once()
    async with get_sessionmaker()() as s:
        report = await clv_report_by_league(s)
    row = next(r for r in report if r.league_id == settled_world["league_id"])
    assert row.n == 1 and row.beats == 1 and row.beat_pct == pytest.approx(1.0)


async def test_stale_live_signal_expires_fresh_stays():
    """A live signal older than the alert TTL becomes 'expired'; a fresh one stays 'live'.
    Fixture kicks off in the future so neither is graded — isolates the TTL expiry."""
    Session = get_sessionmaker()
    tag = uuid.uuid4().hex[:8]
    fid = f"test_fx_{tag}"
    now = dt.datetime.now(dt.timezone.utc)
    async with Session() as s:
        lg = League(name=f"E {tag}", country="X", sport_key=f"tl_{tag}",
                    is_soft=True, ingest_enabled=False)
        s.add(lg)
        await s.flush()
        h = Team(league_id=lg.id, name=f"H {tag}")
        a = Team(league_id=lg.id, name=f"A {tag}")
        s.add_all([h, a])
        await s.flush()
        s.add(Fixture(id=fid, league_id=lg.id, home_id=h.id, away_id=a.id,
                      kickoff_utc=now + dt.timedelta(hours=2)))   # future → not graded
        mid = await _get_market_id(s, "h2h", None)
        old = Signal(fixture_id=fid, market_id=mid, selection="home", book="fanduel",
                     kind="ev", offered_odds=2.1, fair_prob=0.5, edge_pct=5.0, kelly_frac=0.02,
                     ttl_sec=1800, dedup_hash=f"old_{tag}", status="live",
                     created_at=now - dt.timedelta(hours=1))
        fresh = Signal(fixture_id=fid, market_id=mid, selection="away", book="fanduel",
                       kind="ev", offered_odds=2.1, fair_prob=0.5, edge_pct=5.0, kelly_frac=0.02,
                       ttl_sec=1800, dedup_hash=f"fresh_{tag}", status="live", created_at=now)
        s.add_all([old, fresh])
        await s.commit()
        old_id, fresh_id, league_id = old.id, fresh.id, lg.id
    try:
        await settle_once()
        async with Session() as s:
            assert (await s.get(Signal, old_id)).status == "expired"
            assert (await s.get(Signal, fresh_id)).status == "live"
    finally:
        async with Session() as s:
            await s.execute(delete(Signal).where(Signal.fixture_id == fid))
            await s.execute(delete(Fixture).where(Fixture.id == fid))
            await s.execute(delete(Team).where(Team.league_id == league_id))
            await s.execute(delete(League).where(League.id == league_id))
            await s.commit()
