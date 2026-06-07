"""Per-user preferences (3.4 / NON-NEGOTIABLE #5): which leagues + books a user follows and
their minimum edge. This is the input side of the routing index - the Signals feed filters
by `books` (you only see plays you can place), and fan-out routes pushes by all three.

`PUT` writes the `subscriptions` row AND re-syncs the Redis routing index (deindex the old
membership, index the new), so a change takes effect immediately for both the feed and pushes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.models.core import Book, League
from app.models.users import Subscription, User
from app.services.cache import get_redis
from app.shared.db import get_db
from app.shared.routing import deindex_subscription, index_subscription

router = APIRouter(prefix="/me", tags=["preferences"])


class PreferencesIn(BaseModel):
    leagues: list[int] = Field(default_factory=list)
    books: list[str] = Field(default_factory=list)
    min_edge: float = 0.0
    odds_format: str = "american"


def _serialize(sub: Subscription | None) -> dict:
    if sub is None:
        return {"leagues": [], "books": [], "min_edge": 0.0, "odds_format": "american"}
    return {
        "leagues": list(sub.leagues),
        "books": list(sub.books),
        "min_edge": sub.min_edge,
        "odds_format": sub.odds_format,
    }


@router.get("/preferences")
async def get_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    sub = await db.get(Subscription, user.id)
    return _serialize(sub)


@router.put("/preferences")
async def put_preferences(
    body: PreferencesIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Validate against pickable books + real league ids so the routing index never holds junk.
    if body.books:
        known = set(
            (await db.execute(select(Book.key).where(Book.pickable.is_(True)))).scalars().all()
        )
        bad_books = [b for b in body.books if b not in known]
        if bad_books:
            raise HTTPException(status_code=422, detail=f"Unknown book(s): {', '.join(bad_books)}")
    if body.min_edge < 0:
        raise HTTPException(status_code=422, detail="min_edge must be >= 0")
    if body.odds_format not in ("american", "decimal"):
        raise HTTPException(status_code=422, detail="odds_format must be american or decimal")
    if body.leagues:
        valid = set(
            (await db.execute(select(League.id).where(League.id.in_(body.leagues)))).scalars().all()
        )
        bad_leagues = [lid for lid in body.leagues if lid not in valid]
        if bad_leagues:
            raise HTTPException(status_code=422, detail=f"Unknown league(s): {bad_leagues}")

    # Dedupe while preserving order; keep the user's existing delivery channels untouched.
    leagues = list(dict.fromkeys(body.leagues))
    books = list(dict.fromkeys(body.books))

    sub = await db.get(Subscription, user.id)
    old_leagues = list(sub.leagues) if sub else []
    old_books = list(sub.books) if sub else []
    channels = list(sub.channels) if sub else []
    if sub is None:
        sub = Subscription(user_id=user.id, channels=channels)
        db.add(sub)
    sub.leagues = leagues
    sub.books = books
    sub.min_edge = body.min_edge
    sub.odds_format = body.odds_format
    await db.commit()

    # Re-sync the routing index: drop old membership, then add the new (NON-NEGOTIABLE #5).
    r = get_redis()
    await deindex_subscription(r, user.id, old_leagues, old_books)
    await index_subscription(r, user.id, user.tier, leagues, books, body.min_edge, channels)

    return _serialize(sub)
