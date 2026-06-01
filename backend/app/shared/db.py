"""Async SQLAlchemy engine/session + Postgres partition helpers.

`odds_snapshots` is the firehose (CLAUDE.md) and is declared `PARTITION BY RANGE (ts)`.
The parent table is created in the Alembic migration; daily child partitions are created
on demand via `ensure_daily_partition` so inserts always have a home.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    pass


def sync_database_url() -> str:
    """Sync URL (psycopg2) for Alembic; runtime uses the async asyncpg URL."""
    return settings.database_url.replace("+asyncpg", "+psycopg2")


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        # NullPool: a fresh connection per checkout. Keeps the engine loop-agnostic
        # (no pooled asyncpg connection bound to a now-closed event loop) and is fine for
        # our low-QPS worker. Revisit pooling when the API starts serving DB-backed reads.
        _engine = create_async_engine(settings.database_url, poolclass=NullPool)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_db():
    """FastAPI dependency: yield an async session per request."""
    async with get_sessionmaker()() as session:
        yield session


async def ensure_daily_partition(when: datetime | date | None = None) -> str:
    """Create today's (or `when`'s) odds_snapshots partition if absent. Idempotent."""
    if when is None:
        when = datetime.now(UTC).date()
    elif isinstance(when, datetime):
        when = when.astimezone(UTC).date()

    start = when
    end = when + timedelta(days=1)
    table = f"odds_snapshots_{start:%Y%m%d}"
    # Partition-DDL can't take bind parameters; dates are server-derived (not user input)
    # and ISO-formatted, so inlining them is safe.
    sql = text(
        f'CREATE TABLE IF NOT EXISTS "{table}" PARTITION OF odds_snapshots '
        f"FOR VALUES FROM ('{start:%Y-%m-%d}') TO ('{end:%Y-%m-%d}')"
    )
    async with get_engine().begin() as conn:
        await conn.execute(sql)
    return table
