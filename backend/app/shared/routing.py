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


async def index_subscription(r, user_id: int, tier: str, leagues: list[int],
                            books: list[str], min_edge: float,
                            channels: list[str]) -> None:
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


async def eligible_users(r, league_id: int, book: str, kind: str) -> set[int]:
    """User ids that should see this signal. Single-book signals (ev, promo) intersect
    league∩book; cross-book signals carry book='multi' and route by league only since they
    span several books. Keyed on the 'multi' marker, not the kind, so every cross-book kind
    (arb AND middle) is covered — middle previously fell through to sinter against the empty
    sub:book:multi set and reached zero users."""
    if book == "multi":
        members = await r.smembers(_league_key(league_id))
    else:
        members = await r.sinter(_league_key(league_id), _book_key(book))
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
