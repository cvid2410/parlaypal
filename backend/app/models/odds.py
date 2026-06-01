"""odds_snapshots — the firehose. Partitioned by day on `ts` (see CLAUDE.md / shared.db).

The parent table is created with `PARTITION BY RANGE (ts)` in the Alembic migration; this
ORM model maps the parent for inserts/queries (Postgres routes rows to the right child).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    # ts is part of the PK because Postgres requires the partition key in the PK of a
    # partitioned table.
    __table_args__ = (
        PrimaryKeyConstraint(
            "fixture_id", "book", "market_id", "selection", "ts", name="pk_odds_snapshots"
        ),
        {"postgresql_partition_by": "RANGE (ts)"},
    )

    fixture_id: Mapped[str] = mapped_column(String, nullable=False)
    book: Mapped[str] = mapped_column(String, nullable=False)
    market_id: Mapped[int] = mapped_column(Integer, nullable=False)
    selection: Mapped[str] = mapped_column(String, nullable=False)
    decimal_odds: Mapped[float] = mapped_column(Float, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
