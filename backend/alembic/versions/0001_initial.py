"""initial schema (ParlayPal Signals)

Revision ID: 0001
Revises:
Create Date: 2026-05-30
"""
from alembic import op

import app.models  # noqa: F401  (registers all tables on Base.metadata)
from app.shared.db import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # create_all honours the `postgresql_partition_by` table arg on odds_snapshots, so
    # the parent is created as PARTITION BY RANGE (ts).
    Base.metadata.create_all(bind)
    # Catch-all partition so inserts never fail before a daily partition is created.
    op.execute(
        "CREATE TABLE IF NOT EXISTS odds_snapshots_default "
        "PARTITION OF odds_snapshots DEFAULT"
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.execute("DROP TABLE IF EXISTS odds_snapshots_default")
    Base.metadata.drop_all(bind)
