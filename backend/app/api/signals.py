"""Tier-gated signals feed for the Signals tab.

Paid tiers (bettor/sharp) see live signals in full, rendered through the compliant copy
engine. Free tier sees the same activity as *locked teasers* - league/fixture/kind only,
with the pick, book, and odds redacted so no edge leaks (CLAUDE.md: scores aren't an edge,
but picks are). Upgrading flips the same cards to full detail.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import settings
from app.models.core import Fixture, League
from app.models.signals import Signal
from app.models.users import Subscription, User
from app.shared.copy import action_ticket, explain
from app.shared.db import get_db
from app.shared.routing import PAID_TIERS
from app.shared.signal_feed import actionable_on, user_facing_clause
from app.shared.signal_view import signal_context

router = APIRouter(prefix="/signals", tags=["signals"])

FEED_LIMIT = 50
# Book-filtering happens in Python (it depends on arb leg books in JSON meta), so we pull a
# wider candidate set first and trim to FEED_LIMIT after, or a heavy book filter could starve
# the feed below its cap.
CANDIDATE_CAP = 200


@router.get("")
async def list_signals(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    paid = user.tier in PAID_TIERS
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=settings.signal_ttl_seconds)

    # The user's subscription filters the feed to what they actually care about / can place:
    # leagues + min_edge in SQL, books in Python below. An unset (or empty) field = no filter,
    # so a brand-new user still sees the full feed.
    sub = await db.get(Subscription, user.id)
    user_books = set(sub.books) if sub else set()

    # +EV launch gate (NON-NEGOTIABLE #2): EV is stored for every soft league but only shown
    # (not even as a teaser) on CLV-certified leagues. Arb/middle/promo aren't gated - they're
    # mechanical. The same clause gates the Leagues badge so the two screens agree.
    conditions = [Signal.status == "live", Signal.created_at >= cutoff, user_facing_clause()]
    if sub and sub.leagues:
        conditions.append(Fixture.league_id.in_(sub.leagues))
    if sub and sub.min_edge > 0:
        conditions.append(Signal.edge_pct >= sub.min_edge)

    candidates = (
        (
            await db.execute(
                select(Signal)
                .join(Fixture, Signal.fixture_id == Fixture.id)
                .join(League, Fixture.league_id == League.id)
                .where(*conditions)
                .order_by(Signal.created_at.desc())
                .limit(CANDIDATE_CAP)
            )
        )
        .scalars()
        .all()
    )

    # Book filter (NON-NEGOTIABLE #5 intent on the read side): only show plays the user can
    # actually place - for an arb that means holding every leg's book.
    sigs = [s for s in candidates if actionable_on(s, user_books)][:FEED_LIMIT]

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
            card.update(
                {
                    "title": copy["title"],
                    "body": copy["body"],
                    "footer": copy["footer"],
                    # Structured "Your bet" inputs (book/pick/min-odds/stake, or per-leg split).
                    "ticket": action_ticket(ctx, user.bankroll),
                    **copy["fields"],
                }
            )
            # Unified headline metric (ev edge / arb profit / middle upside all live in edge_pct).
            card["edge_pct"] = round(sig.edge_pct, 2)
            # Off-market value: surface the consensus depth as a trust signal ("vs N books").
            if sig.kind == "value":
                card["consensus_books"] = (sig.meta or {}).get("n_books")
        else:
            # Redacted teaser - show that an edge exists, not what it is.
            label = {"arb": "arbitrage", "middle": "middle", "promo": "boost"}.get(
                sig.kind, "value bet"
            )
            card["title"] = f"Live {label} - unlock to see the pick"
        cards.append(card)

    return {"tier": user.tier, "count": len(cards), "signals": cards}
