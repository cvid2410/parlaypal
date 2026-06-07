"""Auth API: email+password signup/login issuing JWTs, plus the current-user dependency.

Provider-ready: a future Google flow adds another route that resolves/creates a user and
calls `create_access_token` - the token + `get_current_user` path stay identical.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.shared.db import get_db
from app.shared.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tier: str


class MeOut(BaseModel):
    id: int
    email: EmailStr
    tier: str
    bankroll: float


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    user_id = decode_access_token(authorization.split(" ", 1)[1])
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/signup", response_model=TokenOut)
async def signup(body: Credentials, db: AsyncSession = Depends(get_db)) -> TokenOut:
    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    email = body.email.lower()
    exists = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=email, tier="free", provider="password", password_hash=hash_password(body.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id), tier=user.tier)


@router.post("/login", response_model=TokenOut)
async def login(body: Credentials, db: AsyncSession = Depends(get_db)) -> TokenOut:
    email = body.email.lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if (
        user is None
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenOut(access_token=create_access_token(user.id), tier=user.tier)


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(get_current_user)) -> MeOut:
    return MeOut(id=user.id, email=user.email, tier=user.tier, bankroll=user.bankroll)
