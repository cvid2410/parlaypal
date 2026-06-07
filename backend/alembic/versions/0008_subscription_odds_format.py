"""subscriptions.odds_format - per-user odds display format (i18n Phase 2)

"american" (US default) or "decimal" (what LatAm / Europe read). Math stays in decimal; this
only controls how odds are rendered in signal copy / the odds board for that user.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-06
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("odds_format", sa.String(), nullable=False, server_default="american"),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "odds_format")
