"""teams.logo (crest URL from API-Football)

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("teams", sa.Column("logo", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("teams", "logo")
