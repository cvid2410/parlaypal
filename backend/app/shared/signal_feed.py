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
