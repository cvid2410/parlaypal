"""signals + signal_grades - the detection output and its later CLV/result grading."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[str] = mapped_column(ForeignKey("fixtures.id"), nullable=False)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), nullable=False)
    selection: Mapped[str] = mapped_column(String, nullable=False)
    book: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # ev|arb|middle|model|promo

    offered_odds: Mapped[float] = mapped_column(Float, nullable=False)  # decimal
    fair_prob: Mapped[float] = mapped_column(Float, nullable=False)
    edge_pct: Mapped[float] = mapped_column(Float, nullable=False)
    kelly_frac: Mapped[float] = mapped_column(Float, default=0.0)

    ttl_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    dedup_hash: Mapped[str] = mapped_column(String, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="live")  # live|expired|settled
    # Arb leg detail / extra context (e.g. opposing book, stake fractions).
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SignalGrade(Base):
    __tablename__ = "signal_grades"

    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), primary_key=True)
    closing_odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    beat_clv: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    result: Mapped[str | None] = mapped_column(String, nullable=True)  # win|loss|push
    pnl_units: Mapped[float | None] = mapped_column(Float, nullable=True)
