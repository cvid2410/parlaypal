"""Billing API: Stripe Checkout + webhook (3.1b), with a dev-only tier toggle fallback.

In production (stripe configured, allow_dev_upgrade=False) the Stripe webhook is the only
way `users.tier` changes. Locally, with no Stripe keys, the frontend falls back to
`/billing/dev-upgrade` so the Free/Pro flow stays demoable.
"""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import settings
from app.models.users import User
from app.shared.db import get_db

log = logging.getLogger("billing")
router = APIRouter(prefix="/billing", tags=["billing"])

_VALID_TIERS = {"free", "bettor", "sharp"}


class TierIn(BaseModel):
    tier: str


def _tier_to_price(tier: str) -> str | None:
    return {"bettor": settings.stripe_price_bettor, "sharp": settings.stripe_price_sharp}.get(tier)


@router.get("/config")
async def billing_config() -> dict:
    """Lets the frontend decide between real Stripe checkout and the dev toggle."""
    return {
        "stripe_enabled": bool(settings.stripe_secret_key),
        "allow_dev_upgrade": settings.allow_dev_upgrade,
        "prices": {"bettor": 29, "sharp": 79},
    }


@router.post("/checkout")
async def checkout(
    body: TierIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing not configured")
    price = _tier_to_price(body.tier)
    if not price:
        raise HTTPException(status_code=422, detail="Invalid or unpriced tier")

    stripe.api_key = settings.stripe_secret_key
    params: dict = {
        "mode": "subscription",
        "line_items": [{"price": price, "quantity": 1}],
        "client_reference_id": str(user.id),
        "metadata": {"user_id": str(user.id), "tier": body.tier},
        "subscription_data": {"metadata": {"user_id": str(user.id), "tier": body.tier}},
        "success_url": f"{settings.public_base_url}/signals?upgraded=1",
        "cancel_url": f"{settings.public_base_url}/signals",
    }
    if user.stripe_customer_id:
        params["customer"] = user.stripe_customer_id
    else:
        params["customer_email"] = user.email

    session = await run_in_threadpool(stripe.checkout.Session.create, **params)
    return {"url": session.url}


async def apply_stripe_event(db: AsyncSession, event: dict) -> str | None:
    """Pure-ish event applier (no signature concerns) so it's unit-testable.

    Returns a short description of what it did, or None if ignored.
    """
    etype = event.get("type")
    obj = event.get("data", {}).get("object", {})

    if etype == "checkout.session.completed":
        uid = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("user_id")
        tier = (obj.get("metadata") or {}).get("tier")
        if uid is None or tier not in _VALID_TIERS:
            return None
        user = await db.get(User, int(uid))
        if user is None:
            return None
        user.tier = tier
        if obj.get("customer"):
            user.stripe_customer_id = obj["customer"]
        await db.commit()
        return f"user {uid} -> {tier}"

    if etype == "customer.subscription.deleted":
        cust = obj.get("customer")
        if not cust:
            return None
        user = (
            await db.execute(select(User).where(User.stripe_customer_id == cust))
        ).scalar_one_or_none()
        if user is None:
            return None
        user.tier = "free"
        await db.commit()
        return f"user {user.id} -> free (canceled)"

    return None


@router.post("/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.stripe_webhook_secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature") from None
    result = await apply_stripe_event(db, event)
    log.info("stripe webhook %s -> %s", event.get("type"), result)
    return {"ok": True}


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
