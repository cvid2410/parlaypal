"""users, subscriptions, alerts_sent (idempotency), review_queue (NON-NEGOTIABLE #6)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(String, default="free")  # free|bettor|sharp
    bankroll: Mapped[float] = mapped_column(Float, default=1000.0)
    # Auth: password_hash is null for non-password providers (e.g. future 'google').
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    provider: Mapped[str] = mapped_column(String, default="password")  # password|google
    stripe_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    leagues: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list)
    books: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    min_edge: Mapped[float] = mapped_column(Float, default=0.0)
    channels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    # Display preference (i18n): "american" (US default) or "decimal" (LatAm / Europe).
    odds_format: Mapped[str] = mapped_column(String, default="american", server_default="american")


class AlertSent(Base):
    """Idempotency + audit (NON-NEGOTIABLE #4). Never double-send a (signal,user,channel)."""

    __tablename__ = "alerts_sent"
    __table_args__ = (
        PrimaryKeyConstraint("signal_id", "user_id", "channel", name="pk_alerts_sent"),
    )

    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewQueue(Base):
    """Unmatched entities land here, never /dev/null (NON-NEGOTIABLE #6)."""

    __tablename__ = "review_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)  # book / feed key
    raw_name: Mapped[str] = mapped_column(String, nullable=False)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
