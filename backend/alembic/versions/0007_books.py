"""books — sportsbook catalog for the settings picker / labels / preference validation

Auto-populated: the ingestor registers key+title on first sight; sync_books fills region from
The Odds API (queried one region at a time) and applies the curated overrides (pickable /
category / affiliate links) from app.shared.books. Not a foreign key on odds_snapshots — it's
a metadata catalog, so the firehose stays a plain string column.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("pickable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("affiliate_promo", sa.String(), nullable=True),
        sa.Column("affiliate_url", sa.String(), nullable=True),
        sa.Column(
            "first_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("books")
