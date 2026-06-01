"""auth columns on users (password_hash, provider, stripe_customer_id)

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-30
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column("provider", sa.String(), nullable=False, server_default="password"),
    )
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "provider")
    op.drop_column("users", "password_hash")
