"""Canonical reference entities: leagues, teams, aliases, fixtures, markets."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db import Base


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[str] = mapped_column(String, nullable=False)
    # The Odds API sport key, e.g. "soccer_mexico_ligamx" - this is what makes the
    # ingestor league-agnostic: adding a league is a row, not code.
    sport_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    sharp_ref_book: Mapped[str] = mapped_column(String, default="pinnacle")
    is_soft: Mapped[bool] = mapped_column(Boolean, default=True)
    model_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # +EV launch gate (NON-NEGOTIABLE #2): EV is computed/stored for every soft league, but
    # only reaches users once the league clears the CLV gate and this is flipped True.
    # Arb/middle/promo are mechanical and not gated by this. Default False.
    ev_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    # API-Football league id (for the Scores tab). Null = no scores feed mapped.
    af_league_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Whether the ingestor polls this league at all (sharp leagues can be ingested for
    # the Scores tab but won't generate signals - see is_soft).
    ingest_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("league_id", "name", name="uq_team_league_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # Crest URL, backfilled from API-Football (see scheduler/logos.py). Null until matched.
    logo: Mapped[str | None] = mapped_column(String, nullable=True)


class TeamAlias(Base):
    """Per-book raw name → canonical team. Mostly unused in v1 (single aggregator
    normalizes names), but the table exists for direct-book ingestion later."""

    __tablename__ = "team_aliases"
    __table_args__ = (UniqueConstraint("book", "raw_name", name="uq_alias_book_raw"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    book: Mapped[str] = mapped_column(String, nullable=False)
    raw_name: Mapped[str] = mapped_column(String, nullable=False)


class Fixture(Base):
    __tablename__ = "fixtures"

    # The Odds API event id - the canonical fixture key for v1.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    home_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    kickoff_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, default="scheduled")
    # Final score, populated by the results resolver (API-Football). Null until settled.
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    league: Mapped[League] = relationship()


class Book(Base):
    """Sportsbook catalog - the source of truth for the settings picker, labels, and
    preference validation. Auto-populated: `ingestors/odds.py` registers `key`/`title` on
    first sight; `scheduler/books.py` (sync_books) fills `region` (queried one region at a
    time, since no per-book payload carries it) and refreshes from The Odds API.

    `pickable`, `category`, and the `affiliate_*` columns are the CURATED policy layer -
    sourced from `app.shared.books.BOOK_OVERRIDES` (code-owned) and applied by sync_books, so
    the live hot path never clobbers them. Logos are NOT stored: the frontend renders
    `/books/{key}.svg` with a name fallback (The Odds API has no logo feed)."""

    __tablename__ = "books"

    key: Mapped[str] = mapped_column(String, primary_key=True)  # The Odds API bookmaker key
    title: Mapped[str] = mapped_column(String, nullable=False)  # display name (API `title`)
    region: Mapped[str | None] = mapped_column(String, nullable=True)  # us|us2|uk|eu|au
    # Whether the book is offered in the picker. Default True; sweeps/sharp-ref/thin books are
    # flipped False via BOOK_OVERRIDES (e.g. fliff=sweeps, pinnacle=no US retail).
    pickable: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    category: Mapped[str | None] = mapped_column(String, nullable=True)  # us|offshore|exchange|...
    affiliate_promo: Mapped[str | None] = mapped_column(String, nullable=True)
    affiliate_url: Mapped[str | None] = mapped_column(String, nullable=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Market(Base):
    """A market definition, reusable across fixtures. e.g. ('total', 2.5, 'FT')."""

    __tablename__ = "markets"
    # line is NULL for line-less markets (h2h, btts). A plain unique constraint can't
    # dedupe those (NULLs are never equal in Postgres), so use a COALESCE functional
    # index - otherwise every process restart would mint duplicate h2h market rows.
    __table_args__ = (
        Index("uq_market_def", "type", text("coalesce(line, -1)"), "period", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)  # h2h, total, btts, ...
    line: Mapped[float | None] = mapped_column(Float, nullable=True)  # null for h2h/btts
    period: Mapped[str] = mapped_column(String, default="FT")
