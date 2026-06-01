"""Shared user-facing signal filter.

The Signals feed and the Leagues "N live" badge must show the SAME set, or they disagree
(a count with no cards). They drifted once when the +EV gate (NON-NEGOTIABLE #2) was added
to the feed but not the badge — so the gate predicate lives here, imported by both.

Requires the query to already join Signal -> Fixture -> League.
"""

from __future__ import annotations

from app.models.core import League
from app.models.signals import Signal


def user_facing_clause():
    """SQLAlchemy predicate for signals a user may see: everything except +EV on a league
    that hasn't cleared the CLV gate (ev_certified=False). Arb/middle/promo are mechanical
    and never gated."""
    return ~((Signal.kind == "ev") & (League.ev_certified.is_(False)))


def required_books(sig: Signal) -> list[str]:
    """Books a user must hold to act on this signal. EV/promo: the single offering book.
    Arb/middle (book='multi'): every leg's book — you can't place the play without all legs.
    Shared by fan-out (push routing) and the in-app feed so both apply the same per-user book
    filter. Empty result means "no book requirement"."""
    if sig.book and sig.book != "multi":
        return [sig.book]
    legs = (sig.meta or {}).get("legs") or {}
    values = legs.values() if isinstance(legs, dict) else legs
    return [leg["book"] for leg in values if isinstance(leg, dict) and leg.get("book")]


def actionable_on(sig: Signal, user_books: set[str]) -> bool:
    """True if the user holds every book this signal requires (so they can actually place it).
    A user with no books set (empty) is unfiltered — they see everything."""
    if not user_books:
        return True
    return set(required_books(sig)).issubset(user_books)
