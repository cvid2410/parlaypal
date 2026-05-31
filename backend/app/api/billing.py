"""Billing API.

For now this only exposes a DEV-ONLY tier toggle so the frontend can demo the Free/Pro
experience before Stripe lands. Real Stripe Checkout + webhook (task 3.1b) will replace
`dev-upgrade` as the only legitimate way to change `users.tier` in production.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import settings
from app.models.users import User
from app.shared.db import get_db

router = APIRouter(prefix="/billing", tags=["billing"])

_VALID_TIERS = {"free", "bettor", "sharp"}


class TierIn(BaseModel):
    tier: str


@router.post("/dev-upgrade")
async def dev_upgrade(
    body: TierIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not settings.allow_dev_upgrade:
        raise HTTPException(status_code=403, detail="Dev upgrade disabled")
    if body.tier not in _VALID_TIERS:
        raise HTTPException(status_code=422, detail="Invalid tier")
    user.tier = body.tier
    await db.commit()
    return {"tier": user.tier}
