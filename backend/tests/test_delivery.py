"""Integration test for routing + delivery. Requires Postgres + Redis."""
import datetime as dt
import uuid

import pytest
from sqlalchemy import delete, select

from app.ingestors.odds import _get_market_id
from app.models.core import Fixture, League, Team
from app.models.signals import Signal
from app.models.users import AlertSent, Subscription, User
from app.services.cache import get_redis
from app.shared.db import get_sessionmaker
from app.shared.routing import eligible_users, index_subscription, user_route_meta
from app.workers.deliver import deliver
from app.workers.fanout import route_signal


@pytest.fixture
async def world():
    """A soft league + fixture + an EV signal + a bettor user subscribed to it."""
    Session = get_sessionmaker()
    r = get_redis()
    tag = uuid.uuid4().hex[:8]
    fid = f"test_fx_{tag}"
    async with Session() as s:
        lg = League(name="Test", country="T", sport_key=f"tl_{tag}",
                    is_soft=True, ingest_enabled=False)
        s.add(lg)
        await s.flush()
        h = Team(league_id=lg.id, name=f"Home {tag}")
        a = Team(league_id=lg.id, name=f"Away {tag}")
        s.add_all([h, a])
        await s.flush()
        s.add(Fixture(id=fid, league_id=lg.id, home_id=h.id, away_id=a.id,
                      kickoff_utc=dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)))
        mid = await _get_market_id(s, "h2h", None)
        sig = Signal(fixture_id=fid, market_id=mid, selection="home", book="fanduel",
                     kind="ev", offered_odds=2.35, fair_prob=0.5, edge_pct=9.1,
                     kelly_frac=0.03, ttl_sec=1800, dedup_hash=f"hash_{tag}", status="live")
        s.add(sig)
        user = User(email=f"u_{tag}@x.com", tier="bettor", bankroll=1000.0)
        s.add(user)
        await s.flush()
        s.add(Subscription(user_id=user.id, leagues=[lg.id], books=["fanduel"],
                           min_edge=0.0, channels=["log"]))
        await s.commit()
        league_id, sig_id, uid = lg.id, sig.id, user.id

    await index_subscription(r, uid, "bettor", [league_id], ["fanduel"], 0.0, ["log"])

    yield {"league_id": league_id, "sig_id": sig_id, "uid": uid, "fid": fid}

    async with Session() as s:
        await s.execute(delete(AlertSent).where(AlertSent.signal_id == sig_id))
        await s.execute(delete(Signal).where(Signal.fixture_id == fid))
        await s.execute(delete(Subscription).where(Subscription.user_id == uid))
        await s.execute(delete(User).where(User.id == uid))
        await s.execute(delete(Fixture).where(Fixture.id == fid))
        await s.execute(delete(Team).where(Team.league_id == league_id))
        await s.execute(delete(League).where(League.id == league_id))
        await s.commit()
    async for k in r.scan_iter(match=f"*{tag}*"):
        await r.delete(k)
    await r.srem(f"sub:league:{league_id}", uid)
    await r.srem("sub:book:fanduel", uid)
    await r.delete(f"usermeta:{uid}")


async def test_routing_index_and_eligibility(world):
    r = get_redis()
    # EV intersects league∩book → user eligible.
    users = await eligible_users(r, world["league_id"], "fanduel", "ev")
    assert world["uid"] in users
    # A book the user doesn't follow → not eligible for EV.
    assert world["uid"] not in await eligible_users(r, world["league_id"], "betmgm", "ev")
    meta = await user_route_meta(r, world["uid"])
    assert meta["tier"] == "bettor" and meta["channels"] == ["log"]


async def test_route_signal_counts_eligible(world):
    out = await route_signal({}, world["sig_id"])
    assert out["eligible"] >= 1
    assert out["enqueued"] >= 1  # one channel (log)


async def test_deliver_is_idempotent(world):
    Session = get_sessionmaker()
    ok = await deliver({}, world["sig_id"], world["uid"], "log")
    assert ok is True
    # Second attempt is a no-op (claim-first dedup), no double-send.
    assert await deliver({}, world["sig_id"], world["uid"], "log") is False
    async with Session() as s:
        rows = (await s.execute(
            select(AlertSent).where(AlertSent.signal_id == world["sig_id"])
        )).scalars().all()
    assert len(rows) == 1


async def test_min_edge_filters_out(world):
    r = get_redis()
    # Raise the user's min_edge above the signal's edge → routed to zero deliveries.
    await index_subscription(r, world["uid"], "bettor", [world["league_id"]],
                            ["fanduel"], 50.0, ["log"])
    out = await route_signal({}, world["sig_id"])
    assert out["enqueued"] == 0
