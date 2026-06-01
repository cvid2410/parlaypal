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
from app.shared.signal_feed import actionable_on, required_books
from app.workers.deliver import deliver
from app.workers.fanout import route_signal


def test_required_books_single_and_multi():
    # EV/promo → the one offering book.
    assert required_books(Signal(book="fanduel", kind="ev", meta=None)) == ["fanduel"]
    # Arb/middle → every leg's book, pulled from meta.legs (dict keyed by selection).
    arb = Signal(
        book="multi",
        kind="arb",
        meta={
            "legs": {
                "home": {"book": "draftkings", "odds": 2.1, "stake_frac": 0.5},
                "away": {"book": "betmgm", "odds": 2.1, "stake_frac": 0.5},
            }
        },
    )
    assert sorted(required_books(arb)) == ["betmgm", "draftkings"]
    # actionable_on: user must hold every leg book; empty user set = unfiltered.
    assert actionable_on(arb, {"draftkings", "betmgm", "caesars"}) is True
    assert actionable_on(arb, {"draftkings"}) is False  # missing betmgm leg
    assert actionable_on(arb, set()) is True


@pytest.fixture
async def world():
    """A soft league + fixture + an EV signal + a bettor user subscribed to it."""
    Session = get_sessionmaker()
    r = get_redis()
    tag = uuid.uuid4().hex[:8]
    fid = f"test_fx_{tag}"
    async with Session() as s:
        lg = League(
            name="Test",
            country="T",
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
        sig = Signal(
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
            dedup_hash=f"hash_{tag}",
            status="live",
        )
        s.add(sig)
        user = User(email=f"u_{tag}@x.com", tier="bettor", bankroll=1000.0)
        s.add(user)
        await s.flush()
        s.add(
            Subscription(
                user_id=user.id, leagues=[lg.id], books=["fanduel"], min_edge=0.0, channels=["log"]
            )
        )
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
    # EV requires the one offering book; user follows fanduel → eligible.
    users = await eligible_users(r, world["league_id"], ["fanduel"])
    assert world["uid"] in users
    # A book the user doesn't follow → not eligible.
    assert world["uid"] not in await eligible_users(r, world["league_id"], ["betmgm"])
    meta = await user_route_meta(r, world["uid"])
    assert meta["tier"] == "bettor" and meta["channels"] == ["log"]


async def test_cross_book_requires_all_leg_books(world):
    r = get_redis()
    lid, uid = world["league_id"], world["uid"]
    # An arb whose legs are all on a book the user holds → eligible.
    assert uid in await eligible_users(r, lid, ["fanduel"])
    # An arb spanning fanduel + betmgm → the user lacks betmgm and can't lock the play, so they
    # must NOT be routed it (the gap this feature closes).
    assert uid not in await eligible_users(r, lid, ["fanduel", "betmgm"])
    # Once they follow both books, the full-leg arb reaches them.
    await index_subscription(r, uid, "bettor", [lid], ["fanduel", "betmgm"], 0.0, ["log"])
    assert uid in await eligible_users(r, lid, ["fanduel", "betmgm"])
    await r.srem("sub:book:betmgm", uid)  # not tag-scoped, so clean it up explicitly


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
        rows = (
            (await s.execute(select(AlertSent).where(AlertSent.signal_id == world["sig_id"])))
            .scalars()
            .all()
        )
    assert len(rows) == 1


async def test_min_edge_filters_out(world):
    r = get_redis()
    # Raise the user's min_edge above the signal's edge → routed to zero deliveries.
    await index_subscription(
        r, world["uid"], "bettor", [world["league_id"]], ["fanduel"], 50.0, ["log"]
    )
    out = await route_signal({}, world["sig_id"])
    assert out["enqueued"] == 0
