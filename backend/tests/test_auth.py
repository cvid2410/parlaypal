import uuid

import httpx
from httpx import ASGITransport
from sqlalchemy import delete

from app.main import app
from app.models.users import User
from app.shared.db import get_sessionmaker


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _cleanup(email: str) -> None:
    async with get_sessionmaker()() as s:
        await s.execute(delete(User).where(User.email == email))
        await s.commit()


async def test_signup_login_me_flow():
    email = f"{uuid.uuid4().hex[:8]}@x.com"
    try:
        async with _client() as c:
            r = await c.post("/api/auth/signup", json={"email": email, "password": "password123"})
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["tier"] == "free" and body["token_type"] == "bearer"
            token = body["access_token"]

            # duplicate email rejected
            dup = await c.post("/api/auth/signup", json={"email": email, "password": "password123"})
            assert dup.status_code == 409

            # wrong password rejected
            bad = await c.post("/api/auth/login", json={"email": email, "password": "wrongpass1"})
            assert bad.status_code == 401

            # correct login works
            ok = await c.post("/api/auth/login", json={"email": email, "password": "password123"})
            assert ok.status_code == 200

            # /me with token
            me = await c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert me.status_code == 200
            assert me.json()["email"] == email and me.json()["tier"] == "free"

            # /me without token
            assert (await c.get("/api/auth/me")).status_code == 401
            # /me with garbage token
            assert (
                await c.get("/api/auth/me", headers={"Authorization": "Bearer nope"})
            ).status_code == 401
    finally:
        await _cleanup(email)


async def test_signup_rejects_short_password():
    email = f"{uuid.uuid4().hex[:8]}@x.com"
    try:
        async with _client() as c:
            r = await c.post("/api/auth/signup", json={"email": email, "password": "short"})
            assert r.status_code == 422
    finally:
        await _cleanup(email)
