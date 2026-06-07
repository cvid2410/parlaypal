"""Routing index (NON-NEGOTIABLE #5).

A signal must reach only matching users without iterating the whole user table. We keep
precomputed Redis sets per league and per book; fan-out intersects them and filters by each
user's min_edge. The index is maintained whenever a subscription changes.

Keys:
  sub:league:{league_id}  -> set of user ids
  sub:book:{book}         -> set of user ids
  usermeta:{user_id}      -> hash {tier, min_edge, channels(csv)}
"""

from __future__ import annotations

PAID_TIERS = {"bettor", "sharp"}


def _league_key(league_id: int) -> str:
    return f"sub:league:{league_id}"


def _book_key(book: str) -> str:
    return f"sub:book:{book}"


def _meta_key(user_id: int) -> str:
    return f"usermeta:{user_id}"


async def index_subscription(
    r,
    user_id: int,
    tier: str,
    leagues: list[int],
    books: list[str],
    min_edge: float,
    channels: list[str],
) -> None:
    """(Re)write one user's routing membership + meta."""
    pipe = r.pipeline()
    for lid in leagues:
        pipe.sadd(_league_key(lid), user_id)
    for book in books:
        pipe.sadd(_book_key(book), user_id)
    pipe.hset(
        _meta_key(user_id),
        mapping={"tier": tier, "min_edge": min_edge, "channels": ",".join(channels)},
    )
    await pipe.execute()


async def deindex_subscription(r, user_id: int, leagues: list[int], books: list[str]) -> None:
    """Remove a user from the given league/book routing sets. Call with the user's OLD
    leagues/books before re-indexing on a preferences change, so a book/league they dropped
    stops routing to them (index_subscription only adds - it can't know what to remove)."""
    pipe = r.pipeline()
    for lid in leagues:
        pipe.srem(_league_key(lid), user_id)
    for book in books:
        pipe.srem(_book_key(book), user_id)
    await pipe.execute()


async def eligible_users(r, league_id: int, books: list[str]) -> set[int]:
    """User ids that should see this signal: subscribed to the league AND to EVERY book the
    signal requires. Single-book signals (ev, promo) require the one offering book; cross-book
    signals (arb, middle) require all leg books - a user missing any leg can't execute the play
    (you can't lock an arb without every leg), so they don't get it. Intersecting league∩books
    keeps this off the full user table (NON-NEGOTIABLE #5). Empty `books` (shouldn't happen)
    falls back to league-only so a signal is never silently dropped to nobody."""
    keys = [_league_key(league_id)] + [_book_key(b) for b in dict.fromkeys(books)]
    members = await r.sinter(*keys)
    return {int(m) for m in members}


async def user_route_meta(r, user_id: int) -> dict | None:
    meta = await r.hgetall(_meta_key(user_id))
    if not meta:
        return None
    return {
        "tier": meta.get("tier", "free"),
        "min_edge": float(meta.get("min_edge", 0) or 0),
        "channels": [c for c in meta.get("channels", "").split(",") if c],
    }
