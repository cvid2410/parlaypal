"""leagues.af_league_id (API-Football league id) for the Scores tab

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leagues", sa.Column("af_league_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("leagues", "af_league_id")
