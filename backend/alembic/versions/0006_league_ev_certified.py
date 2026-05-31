"""leagues.ev_certified — per-league +EV launch gate (NON-NEGOTIABLE #2)

A league only sends +EV signals to users once its backtested signals clear the CLV gate
(Wilson lower bound >= threshold over a real sample). EV is still computed/stored for every
soft league (for backtest + monitoring); this flag controls whether it reaches users.
Defaults False so nothing is user-facing until explicitly certified.

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leagues",
        sa.Column("ev_certified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("leagues", "ev_certified")
