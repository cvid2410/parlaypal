"""initial schema (ParlayPal Signals)

Revision ID: 0001
Revises:
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leagues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("sport_key", sa.String(), nullable=False),
        sa.Column("sharp_ref_book", sa.String(), nullable=False),
        sa.Column("is_soft", sa.Boolean(), nullable=False),
        sa.Column("model_enabled", sa.Boolean(), nullable=False),
        sa.Column("ingest_enabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sport_key"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("bankroll", sa.Float(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "markets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("line", sa.Float(), nullable=True),
        sa.Column("period", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # line is NULL for line-less markets (h2h/btts); NULLs are never equal in Postgres, so a
    # plain unique constraint can't dedupe them — use a COALESCE functional unique index.
    op.execute("CREATE UNIQUE INDEX uq_market_def ON markets (type, coalesce(line, -1), period)")

    op.create_table(
        "review_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("raw_name", sa.String(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("league_id", sa.Integer(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("league_id", "name", name="uq_team_league_name"),
    )

    op.create_table(
        "team_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("book", sa.String(), nullable=False),
        sa.Column("raw_name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book", "raw_name", name="uq_alias_book_raw"),
    )

    op.create_table(
        "fixtures",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("league_id", sa.Integer(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("home_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("away_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("kickoff_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fixture_id", sa.String(), sa.ForeignKey("fixtures.id"), nullable=False),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("selection", sa.String(), nullable=False),
        sa.Column("book", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("offered_odds", sa.Float(), nullable=False),
        sa.Column("fair_prob", sa.Float(), nullable=False),
        sa.Column("edge_pct", sa.Float(), nullable=False),
        sa.Column("kelly_frac", sa.Float(), nullable=False),
        sa.Column("ttl_sec", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("dedup_hash", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_signals_created_at", "signals", ["created_at"])
    op.create_index("ix_signals_dedup_hash", "signals", ["dedup_hash"])

    op.create_table(
        "signal_grades",
        sa.Column("signal_id", sa.Integer(), sa.ForeignKey("signals.id"), nullable=False),
        sa.Column("closing_odds", sa.Float(), nullable=True),
        sa.Column("beat_clv", sa.Boolean(), nullable=True),
        sa.Column("result", sa.String(), nullable=True),
        sa.Column("pnl_units", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("signal_id"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("leagues", sa.ARRAY(sa.Integer()), nullable=False),
        sa.Column("books", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("min_edge", sa.Float(), nullable=False),
        sa.Column("channels", sa.ARRAY(sa.String()), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "alerts_sent",
        sa.Column("signal_id", sa.Integer(), sa.ForeignKey("signals.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column(
            "ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("signal_id", "user_id", "channel", name="pk_alerts_sent"),
    )

    op.create_table(
        "odds_snapshots",
        sa.Column("fixture_id", sa.String(), nullable=False),
        sa.Column("book", sa.String(), nullable=False),
        sa.Column("market_id", sa.Integer(), nullable=False),
        sa.Column("selection", sa.String(), nullable=False),
        sa.Column("decimal_odds", sa.Float(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "fixture_id", "book", "market_id", "selection", "ts", name="pk_odds_snapshots"
        ),
        postgresql_partition_by="RANGE (ts)",
    )
    op.execute(
        "CREATE TABLE IF NOT EXISTS odds_snapshots_default PARTITION OF odds_snapshots DEFAULT"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS odds_snapshots_default")
    op.drop_table("odds_snapshots")
    op.drop_table("alerts_sent")
    op.drop_table("subscriptions")
    op.drop_table("signal_grades")
    op.drop_index("ix_signals_dedup_hash", table_name="signals")
    op.drop_index("ix_signals_created_at", table_name="signals")
    op.drop_table("signals")
    op.drop_table("fixtures")
    op.drop_table("team_aliases")
    op.drop_table("teams")
    op.drop_table("review_queue")
    op.execute("DROP INDEX IF EXISTS uq_market_def")
    op.drop_table("markets")
    op.drop_table("users")
    op.drop_table("leagues")
