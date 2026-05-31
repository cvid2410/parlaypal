"""Stripe billing: webhook event application (the network-free core) + endpoint guards."""

import uuid

import httpx
from httpx import ASGITransport
from sqlalchemy import delete

from app.api.billing import apply_stripe_event
from app.main import app
from app.models.users import User
from app.shared.db import get_sessionmaker
from app.shared.security import create_access_token


async def _mk_user(tier: str = "free", customer: str | None = None) -> int:
    async with get_sessionmaker()() as s:
        u = User(email=f"{uuid.uuid4().hex[:8]}@x.com", tier=tier, stripe_customer_id=customer)
        s.add(u)
        await s.commit()
        await s.refresh(u)
        return u.id


async def _del_user(uid: int) -> None:
    async with get_sessionmaker()() as s:
        await s.execute(delete(User).where(User.id == uid))
        await s.commit()


def _client():
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_checkout_completed_upgrades_and_stores_customer():
    uid = await _mk_user("free")
    try:
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": str(uid),
                    "customer": "cus_123",
                    "metadata": {"user_id": str(uid), "tier": "bettor"},
                }
            },
        }
        async with get_sessionmaker()() as s:
            assert await apply_stripe_event(s, event) is not None
        async with get_sessionmaker()() as s:
            u = await s.get(User, uid)
            assert u.tier == "bettor"
            assert u.stripe_customer_id == "cus_123"
    finally:
        await _del_user(uid)


async def test_subscription_deleted_downgrades_to_free():
    uid = await _mk_user("sharp", customer="cus_x")
    try:
        event = {"type": "customer.subscription.deleted", "data": {"object": {"customer": "cus_x"}}}
        async with get_sessionmaker()() as s:
            assert await apply_stripe_event(s, event) is not None
        async with get_sessionmaker()() as s:
            assert (await s.get(User, uid)).tier == "free"
    finally:
        await _del_user(uid)


async def test_unknown_event_is_ignored():
    async with get_sessionmaker()() as s:
        assert await apply_stripe_event(s, {"type": "invoice.paid", "data": {"object": {}}}) is None


async def test_config_endpoint_reports_disabled_without_keys():
    async with _client() as c:
        r = await c.get("/api/billing/config")
    assert r.status_code == 200
    d = r.json()
    assert d["stripe_enabled"] is False  # no key in test env
    assert d["allow_dev_upgrade"] is True


async def test_checkout_503_without_stripe_config():
    uid = await _mk_user()
    try:
        token = create_access_token(uid)
        async with _client() as c:
            r = await c.post(
                "/api/billing/checkout",
                json={"tier": "bettor"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 503
    finally:
        await _del_user(uid)


async def test_checkout_requires_auth():
    async with _client() as c:
        assert (await c.post("/api/billing/checkout", json={"tier": "bettor"})).status_code == 401
