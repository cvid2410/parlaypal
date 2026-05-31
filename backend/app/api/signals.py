"""Tier-gated signals feed for the Signals tab.

Paid tiers (bettor/sharp) see live signals in full, rendered through the compliant copy
engine. Free tier sees the same activity as *locked teasers* — league/fixture/kind only,
with the pick, book, and odds redacted so no edge leaks (CLAUDE.md: scores aren't an edge,
but picks are). Upgrading flips the same cards to full detail.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.core import Fixture, League
from app.models.signals import Signal
from app.models.users import User
from app.api.auth import get_current_user
from app.shared.copy import explain
from app.shared.db import get_db
from app.shared.routing import PAID_TIERS
from app.shared.signal_view import signal_context

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("")
async def list_signals(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    paid = user.tier in PAID_TIERS
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=settings.signal_ttl_seconds)

    # +EV launch gate (NON-NEGOTIABLE #2): EV is stored for every soft league but only shown
    # (not even as a teaser) on CLV-certified leagues. Arb/middle/promo aren't gated — they're
    # mechanical. Exclude uncertified EV right in the query.
    sigs = (await db.execute(
        select(Signal)
        .join(Fixture, Signal.fixture_id == Fixture.id)
        .join(League, Fixture.league_id == League.id)
        .where(
            Signal.status == "live",
            Signal.created_at >= cutoff,
            ~((Signal.kind == "ev") & (League.ev_certified.is_(False))),
        )
        .order_by(Signal.created_at.desc())
        .limit(50)
    )).scalars().all()

    cards = []
    for sig in sigs:
        ctx = await signal_context(db, sig)
        if ctx is None:
            continue
        age = int((now - sig.created_at).total_seconds())
        card = {
            "id": sig.id,
            "kind": sig.kind,
            "fixture_id": sig.fixture_id,
            "league": ctx.league_name,
            "country": ctx.country,
            "fixture": ctx.fixture_label,
            "home_logo": ctx.home_logo,
            "away_logo": ctx.away_logo,
            "created_at": sig.created_at.isoformat(),
            "age_seconds": age,
            "locked": not paid,
        }
        if paid:
            copy = explain(ctx)
            card.update({
                "title": copy["title"],
                "body": copy["body"],
                "footer": copy["footer"],
                **copy["fields"],
            })
            # Unified headline metric (ev edge / arb profit / middle upside all live in edge_pct).
            card["edge_pct"] = round(sig.edge_pct, 2)
        else:
            # Redacted teaser — show that an edge exists, not what it is.
            label = {"arb": "arbitrage", "middle": "middle", "promo": "boost"}.get(sig.kind, "value bet")
            card["title"] = f"Live {label} — unlock to see the pick"
        cards.append(card)

    return {"tier": user.tier, "count": len(cards), "signals": cards}
