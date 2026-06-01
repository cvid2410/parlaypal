"""Multi-league odds ingestor.

Generalised from the WC-only `services/odds_api.py`. Driven by `leagues.sport_key`, it
pulls soft US books + the Pinnacle sharp reference through The Odds API (one aggregator,
so team names are already normalised and each event has a stable `id` we use as the
canonical fixture key).

Per poll it:
  1. fetches odds for every ingest-enabled league,
  2. upserts canonical teams / fixtures / markets,
  3. writes latest odds to Redis hot state `odds:{fixture_id}:{market_id}`,
  4. appends an `odds_snapshots` row ONLY when a price moved meaningfully (the
     change-gate, NON-NEGOTIABLE #3), and
  5. enqueues one coalesced `detect_market` job per market that moved.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.models.core import Fixture, League, Market, Team
from app.models.odds import OddsSnapshot
from app.models.users import ReviewQueue
from app.services.cache import get_redis
from app.shared.db import ensure_daily_partition, get_sessionmaker

log = logging.getLogger("ingestor")

THE_ODDS_BASE = "https://api.the-odds-api.com/v4"
MARKETS = "h2h,totals"  # v1 main markets; props (corners/cards) come with the models in v2
KNOWN_MARKETS = {"h2h", "totals"}
HOT_STATE_TTL = 6 * 3600  # hot-state key lives ~6h past first sight
REVIEW_DEDUP_TTL = 24 * 3600  # don't re-queue the same unmatched raw within a day

EnqueueFn = Callable[[str, int], Awaitable[None]]

# Process-lived caches (the worker is long-running) to avoid a DB round-trip per tick.
_team_cache: dict[tuple[int, str], int] = {}
_market_cache: dict[tuple[str, float | None, str], int] = {}


def _combined_books() -> str:
    soft = [b.strip() for b in settings.soft_books.split(",") if b.strip()]
    return ",".join([*soft, settings.sharp_book])


def league_tier(has_live: bool, next_kickoff: datetime | None, now: datetime) -> str:
    """A league's polling urgency from its fixtures. 'fast' for live/imminent games,
    'medium' for later-today games, 'slow' when nothing's near."""
    if has_live:
        return "fast"
    if next_kickoff is not None:
        mins = (next_kickoff - now).total_seconds() / 60
        if mins <= settings.poll_near_window_min:
            return "fast"
        if mins <= settings.poll_upcoming_window_hours * 60:
            return "medium"
    return "slow"


def tier_cadence(tier: str) -> int:
    return {
        "fast": settings.poll_fast_seconds,
        "medium": settings.poll_medium_seconds,
        "slow": settings.poll_slow_seconds,
    }[tier]


async def _due_leagues(session, r, leagues, now: datetime):
    """Filter enabled leagues to those due to be polled this tick, by tier + last-poll time.
    Never-polled leagues are always due (bootstraps fixtures on first run)."""
    live_cutoff = now - timedelta(minutes=settings.poll_live_duration_min)
    rows = (
        await session.execute(
            select(
                Fixture.league_id,
                func.bool_or(
                    and_(Fixture.kickoff_utc <= now, Fixture.kickoff_utc > live_cutoff)
                ).label("has_live"),
                func.min(Fixture.kickoff_utc).filter(Fixture.kickoff_utc > now).label("next_ko"),
            ).group_by(Fixture.league_id)
        )
    ).all()
    timing = {lid: (bool(has_live), next_ko) for lid, has_live, next_ko in rows}

    now_ts = time.time()
    due = []
    for lg in leagues:
        has_live, next_ko = timing.get(lg.id, (False, None))
        tier = league_tier(has_live, next_ko, now)
        last = await r.get(f"lastpoll:{lg.id}")
        if last is None or now_ts - float(last) >= tier_cadence(tier):
            due.append(lg)
    return due


def _hot_key(fixture_id: str, market_id: int) -> str:
    return f"odds:{fixture_id}:{market_id}"


def canonical(market_key: str, outcome: dict, home: str, away: str):
    """Map a raw Odds API outcome to (market_type, line, selection) or None to skip."""
    if market_key == "h2h":
        name = outcome["name"]
        if name == home:
            sel = "home"
        elif name == away:
            sel = "away"
        else:
            sel = "draw"
        return "h2h", None, sel
    if market_key == "totals":
        sel = outcome["name"].strip().lower()  # over / under
        if sel not in ("over", "under"):
            return None
        return "total", outcome.get("point"), sel
    return None


async def _fetch_league(client: httpx.AsyncClient, sport_key: str, books: str) -> list[dict]:
    resp = await client.get(
        f"{THE_ODDS_BASE}/sports/{sport_key}/odds",
        params={
            "apiKey": settings.the_odds_api_key,
            "markets": MARKETS,
            "bookmakers": books,  # overrides regions; gets exactly soft books + Pinnacle
            "oddsFormat": "decimal",
        },
    )
    resp.raise_for_status()
    return resp.json()


async def _get_team_id(session, league_id: int, name: str) -> int:
    key = (league_id, name)
    if key in _team_cache:
        return _team_cache[key]
    stmt = (
        pg_insert(Team)
        .values(league_id=league_id, name=name)
        .on_conflict_do_nothing(index_elements=["league_id", "name"])
        .returning(Team.id)
    )
    tid = (await session.execute(stmt)).scalar()
    if tid is None:  # already existed
        tid = (
            await session.execute(
                select(Team.id).where(Team.league_id == league_id, Team.name == name)
            )
        ).scalar_one()
    _team_cache[key] = tid
    return tid


async def _get_market_id(session, mtype: str, line: float | None, period: str = "FT") -> int:
    # SELECT-first get-or-create. ON CONFLICT can't be used here because `line` is
    # nullable (NULLs never conflict), which would mint a duplicate market every call.
    key = (mtype, line, period)
    if key in _market_cache:
        return _market_cache[key]
    q = select(Market.id).where(Market.type == mtype, Market.period == period)
    q = q.where(Market.line.is_(None) if line is None else Market.line == line)
    mid = (await session.execute(q)).scalar()
    if mid is None:
        market = Market(type=mtype, line=line, period=period)
        session.add(market)
        await session.flush()
        mid = market.id
    _market_cache[key] = mid
    return mid


async def _upsert_fixture(session, event: dict, league_id: int, home_id: int, away_id: int):
    kickoff = datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))
    stmt = (
        pg_insert(Fixture)
        .values(
            id=event["id"],
            league_id=league_id,
            home_id=home_id,
            away_id=away_id,
            kickoff_utc=kickoff,
            status="scheduled",
        )
        .on_conflict_do_update(index_elements=["id"], set_={"kickoff_utc": kickoff})
    )
    await session.execute(stmt)


async def _queue_review(r, book: str, market_key: str, outcome: dict, fixture_id: str):
    """Build a ReviewQueue row for an unmatched market/selection, or None if we've already
    queued this raw shape within REVIEW_DEDUP_TTL (so it can't flood the queue)."""
    raw = f"{market_key}:{outcome.get('name', '')}"
    if not await r.set(f"reviewed:{raw}", 1, nx=True, ex=REVIEW_DEDUP_TTL):
        return None
    reason = "unknown_market" if market_key not in KNOWN_MARKETS else "unparseable_selection"
    return ReviewQueue(
        source=book,
        raw_name=raw,
        reason=reason,
        context={
            "fixture_id": fixture_id,
            "market_key": market_key,
            "outcome_name": outcome.get("name"),
            "point": outcome.get("point"),
        },
    )


async def ingest_once(enqueue: EnqueueFn | None = None) -> dict:
    """One ingestion tick. Fetches only the enabled leagues whose tier is due
    (kickoff-aware), so fast polling is spent on live/imminent games. Returns counters."""
    books = _combined_books()
    r = get_redis()
    Session = get_sessionmaker()
    await ensure_daily_partition()

    stats = {
        "events": 0,
        "changes": 0,
        "markets_dirty": 0,
        "leagues": 0,
        "enabled": 0,
        "errors": 0,
        "review": 0,
    }
    dirty: set[tuple[str, int]] = set()
    snapshots: list[OddsSnapshot] = []
    reviews: list[ReviewQueue] = []
    now = datetime.now(UTC)

    async with Session() as session:
        leagues = (
            (await session.execute(select(League).where(League.ingest_enabled.is_(True))))
            .scalars()
            .all()
        )
        stats["enabled"] = len(leagues)
        # Only poll leagues whose tier is due this tick (kickoff-aware).
        due = await _due_leagues(session, r, leagues, now)

        async with httpx.AsyncClient(timeout=20) as client:
            for lg in due:
                # Stamp now so a fetch (even a failing one) respects the cadence.
                await r.set(f"lastpoll:{lg.id}", time.time())
                try:
                    events = await _fetch_league(client, lg.sport_key, books)
                except Exception as exc:  # one bad league must not sink the whole poll
                    log.warning("ingest league %s failed: %s", lg.sport_key, exc)
                    stats["errors"] += 1
                    continue
                stats["leagues"] += 1

                for event in events:
                    stats["events"] += 1
                    home, away = event["home_team"], event["away_team"]
                    home_id = await _get_team_id(session, lg.id, home)
                    away_id = await _get_team_id(session, lg.id, away)
                    await _upsert_fixture(session, event, lg.id, home_id, away_id)
                    fid = event["id"]

                    for bm in event.get("bookmakers", []):
                        book = bm["key"]
                        for market in bm.get("markets", []):
                            mkey = market["key"]
                            for outcome in market.get("outcomes", []):
                                canon = canonical(mkey, outcome, home, away)
                                if canon is None:
                                    # Unmatched → review queue, never /dev/null (#6).
                                    review = await _queue_review(r, book, mkey, outcome, fid)
                                    if review is not None:
                                        reviews.append(review)
                                        stats["review"] += 1
                                    continue
                                mtype, line, sel = canon
                                price = outcome.get("price")
                                if not price or price <= 1:
                                    continue
                                mid = await _get_market_id(session, mtype, line)
                                key = _hot_key(fid, mid)
                                field = f"{book}:{sel}"
                                old = await r.hget(key, field)
                                changed = old is None or (
                                    abs(price - float(old)) / float(old) >= settings.move_threshold
                                )
                                if not changed:
                                    continue
                                stats["changes"] += 1
                                await r.hset(key, field, price)
                                await r.expire(key, HOT_STATE_TTL)
                                if mtype == "total":  # for the cross-market middle detector
                                    await r.sadd(f"fxtotals:{fid}", mid)
                                    await r.expire(f"fxtotals:{fid}", HOT_STATE_TTL)
                                snapshots.append(
                                    OddsSnapshot(
                                        fixture_id=fid,
                                        book=book,
                                        market_id=mid,
                                        selection=sel,
                                        decimal_odds=price,
                                        ts=now,
                                    )
                                )
                                dirty.add((fid, mid))

        if snapshots or reviews:
            session.add_all(snapshots)
            session.add_all(reviews)
            await session.commit()

    stats["markets_dirty"] = len(dirty)
    if enqueue is not None:
        for fid, mid in dirty:
            await enqueue(fid, mid)
    return stats
