"""Preferences API: GET/PUT /api/me/preferences + routing-index sync. Postgres + Redis."""

import uuid

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import delete

from app.main import app
from app.models.users import Subscription, User
from app.services.cache import get_redis
from app.shared.db import get_sessionmaker
from app.shared.security import create_access_token


def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def user():
    Session = get_sessionmaker()
    tag = uuid.uuid4().hex[:8]
    async with Session() as s:
        u = User(email=f"prefs_{tag}@x.com", tier="bettor")
        s.add(u)
        await s.commit()
        uid = u.id
    yield {"id": uid, "token": create_access_token(uid)}
    r = get_redis()
    for b in ("draftkings", "fanduel", "betmgm"):
        await r.srem(f"sub:book:{b}", uid)
    await r.delete(f"usermeta:{uid}")
    async with Session() as s:
        await s.execute(delete(Subscription).where(Subscription.user_id == uid))
        await s.execute(delete(User).where(User.id == uid))
        await s.commit()


async def test_get_defaults_when_no_subscription(user):
    async with _client() as c:
        r = await c.get("/api/me/preferences", headers={"Authorization": f"Bearer {user['token']}"})
    assert r.status_code == 200
    assert r.json() == {"leagues": [], "books": [], "min_edge": 0.0}


async def test_put_upserts_and_indexes(user):
    uid, token = user["id"], user["token"]
    body = {"leagues": [], "books": ["draftkings", "fanduel"], "min_edge": 2.5}
    async with _client() as c:
        r = await c.put(
            "/api/me/preferences", json=body, headers={"Authorization": f"Bearer {token}"}
        )
    assert r.status_code == 200
    assert r.json()["books"] == ["draftkings", "fanduel"]
    assert r.json()["min_edge"] == 2.5

    # Persisted to the subscriptions row...
    async with get_sessionmaker()() as s:
        sub = await s.get(Subscription, uid)
        assert set(sub.books) == {"draftkings", "fanduel"}
    # ...and the routing index reflects it.
    r_ = get_redis()
    assert await r_.sismember("sub:book:draftkings", uid)
    assert await r_.sismember("sub:book:fanduel", uid)


async def test_put_deindexes_dropped_books(user):
    uid, token = user["id"], user["token"]
    async with _client() as c:
        await c.put(
            "/api/me/preferences",
            json={"books": ["draftkings", "fanduel"], "min_edge": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        # Drop fanduel — it must leave the routing set, not linger.
        await c.put(
            "/api/me/preferences",
            json={"books": ["draftkings"], "min_edge": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
    r = get_redis()
    assert await r.sismember("sub:book:draftkings", uid)
    assert not await r.sismember("sub:book:fanduel", uid)


async def test_put_rejects_unknown_book(user):
    async with _client() as c:
        r = await c.put(
            "/api/me/preferences",
            json={"books": ["bovada"], "min_edge": 0},
            headers={"Authorization": f"Bearer {user['token']}"},
        )
    assert r.status_code == 422
