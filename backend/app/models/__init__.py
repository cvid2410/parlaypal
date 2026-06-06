"""Import all models so they register on Base.metadata (for Alembic + create_all)."""

from app.models.core import Book, Fixture, League, Market, Team, TeamAlias
from app.models.odds import OddsSnapshot
from app.models.signals import Signal, SignalGrade
from app.models.users import AlertSent, ReviewQueue, Subscription, User

__all__ = [
    "Book",
    "League",
    "Team",
    "TeamAlias",
    "Fixture",
    "Market",
    "OddsSnapshot",
    "Signal",
    "SignalGrade",
    "User",
    "Subscription",
    "AlertSent",
    "ReviewQueue",
]
