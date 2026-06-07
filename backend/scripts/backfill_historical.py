"""Backfill odds_snapshots from The Odds API *Historical* endpoint (offline backtest data).

Walks a date grid for one league and reuses the LIVE ingestor's canonical mapping and the
same meaningful-move change-gate, writing OddsSnapshot rows stamped at their *historical*
timestamp. This feeds the detection replay + the CLV gate (NON-NEGOTIABLE #2) WITHOUT
waiting weeks to accumulate live history - qualify a soft league before it ships.

Cost: historical calls bill 10x (10 x markets x regions). One call returns the whole
league at that timestamp, so cost scales with grid points, not fixtures. The real spend is
printed from the API's x-requests-* response headers as it runs.

Two sampling modes:
  * uniform (default): a fixed --stride-min grid across the whole window. Simple, but pays
    for dead air (hours with no games).
  * --match-day: a cheap coarse discovery pass finds kickoffs, then it samples densely ONLY
    in a [kickoff - --pre-hours, kickoff] window per game. Discovery snapshots are cached
    and ingested too (not wasted). Far fewer calls for the same useful coverage.

Reuses canonical()/_get_team_id/_get_market_id/_upsert_fixture from app.ingestors.odds so
the parse is identical to live; only the snapshot timestamp (historical, not now) and the
storage (no Redis hot state) differ.

Run from backend/:
  # uniform
  python -m scripts.backfill_historical --sport-key soccer_mexico_ligamx \
      --start 2026-03-01 --end 2026-04-15 --stride-min 30
  # match-day (recommended) - discover games daily, sample 6h before each kickoff
  python -m scripts.backfill_historical --sport-key soccer_mexico_ligamx \
      --start 2026-03-01 --end 2026-04-15 --match-day --stride-min 20 --pre-hours 6
  # estimate first, spending nothing:
  python -m scripts.backfill_historical --sport-key soccer_mexico_ligamx \
      --start 2026-03-01 --end 2026-04-15 --stride-min 30 --dry-run
"""

import argparse
import asyncio
import logging
from datetime import UTC, date, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.ingestors.odds import (
    MARKETS,
    THE_ODDS_BASE,
    _combined_books,
    _get_market_id,
    _get_team_id,
    _upsert_fixture,
    canonical,
)
from app.models.core import League
from app.models.odds import OddsSnapshot
from app.shared.db import ensure_daily_partition, get_sessionmaker

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("backfill")


def _parse_dt(s: str) -> datetime:
    """ISO date or datetime → tz-aware UTC datetime. Bare dates are taken as 00:00 UTC."""
    s = s.strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.strptime(s, "%Y-%m-%d")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _uniform_grid(start: datetime, end: datetime, stride_min: int) -> list[datetime]:
    out, when = [], start
    step = timedelta(minutes=stride_min)
    while when <= end:
        out.append(when)
        when += step
    return out


def _aligned(t: datetime, start: datetime, stride_min: int) -> datetime:
    """Snap `t` down to the global stride grid anchored at `start`, so per-game windows that
    overlap collapse onto shared timestamps (one call covers every game live at that moment)."""
    step = timedelta(minutes=stride_min)
    return start + ((t - start) // step) * step


async def _fetch_historical(client, sport_key, books, markets, when):
    """One historical snapshot for `sport_key` at/just-before `when`. Returns (json, headers).
    The data array is the same event shape as the live /odds endpoint."""
    resp = await client.get(
        f"{THE_ODDS_BASE}/historical/sports/{sport_key}/odds",
        params={
            "apiKey": settings.the_odds_api_key,
            "markets": markets,
            "bookmakers": books,  # exactly soft books + Pinnacle, same as live
            "oddsFormat": "decimal",
            "date": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    resp.raise_for_status()
    return resp.json(), resp.headers


async def _ingest_snapshot(session, payload, league, last_price, ensured) -> tuple:
    """Parse one historical snapshot into OddsSnapshot rows using the live canonical map and
    the same move-threshold gate. Stamps rows at the snapshot's historical timestamp."""
    events = payload.get("data", []) or []
    snap_ts = _parse_dt(payload["timestamp"])

    d = snap_ts.date()
    if d not in ensured:  # one partition per historical day
        await ensure_daily_partition(snap_ts)
        ensured.add(d)

    rows: list[dict] = []
    counts = {"events": 0, "changes": 0, "skipped": 0}
    for event in events:
        counts["events"] += 1
        home, away = event["home_team"], event["away_team"]
        home_id = await _get_team_id(session, league.id, home)
        away_id = await _get_team_id(session, league.id, away)
        await _upsert_fixture(session, event, league.id, home_id, away_id)
        fid = event["id"]

        for bm in event.get("bookmakers", []):
            book = bm["key"]
            for market in bm.get("markets", []):
                mkey = market["key"]
                for outcome in market.get("outcomes", []):
                    canon = canonical(mkey, outcome, home, away)
                    if canon is None:
                        counts["skipped"] += 1
                        continue
                    mtype, line, sel = canon
                    price = outcome.get("price")
                    if not price or price <= 1:
                        continue
                    mid = await _get_market_id(session, mtype, line)
                    key = (fid, book, mid, sel)
                    old = last_price.get(key)
                    # Same meaningful-move gate as the live ingestor (NON-NEGOTIABLE #3),
                    # compared against the last value we stored in this walk.
                    changed = old is None or abs(price - old) / old >= settings.move_threshold
                    if not changed:
                        continue
                    last_price[key] = price
                    counts["changes"] += 1
                    rows.append(
                        {
                            "fixture_id": fid,
                            "book": book,
                            "market_id": mid,
                            "selection": sel,
                            "decimal_odds": price,
                            "ts": snap_ts,
                        }
                    )

    if rows:
        # Idempotent: re-runs (or a finer stride hitting the same snapshot) collide on the PK.
        await session.execute(
            pg_insert(OddsSnapshot)
            .values(rows)
            .on_conflict_do_nothing(
                index_elements=["fixture_id", "book", "market_id", "selection", "ts"]
            )
        )
    await session.commit()
    return snap_ts, counts


def _kickoffs_from(payload: dict, kickoffs: dict) -> None:
    """Record each event's kickoff (commence_time) from a snapshot payload."""
    for event in payload.get("data", []) or []:
        if "commence_time" in event:
            kickoffs[event["id"]] = event["commence_time"]


async def _discover(client, sport_key, books, markets, start, end, stride_hours):
    """Coarse pass: fetch one snapshot per `stride_hours` to learn kickoffs. Caches the
    payloads (keyed by request time) so the chronological pass ingests them for free."""
    cache: dict[datetime, tuple] = {}
    kickoffs: dict[str, str] = {}
    grid = _uniform_grid(start, end, stride_hours * 60)
    log.info("Discovery: %d coarse calls (every %dh) to find kickoffs…", len(grid), stride_hours)
    for when in grid:
        try:
            payload, headers = await _fetch_historical(client, sport_key, books, markets, when)
        except httpx.HTTPStatusError as exc:
            log.warning(
                "  discover [%s] HTTP %s - skipped",
                when.strftime("%Y-%m-%d %H:%M"),
                exc.response.status_code,
            )
            continue
        cache[when] = (payload, headers)
        _kickoffs_from(payload, kickoffs)
        log.info(
            "  discover [%s] events=%d cost=%s remaining=%s",
            when.strftime("%Y-%m-%d %H:%M"),
            len(payload.get("data", []) or []),
            headers.get("x-requests-last", "?"),
            headers.get("x-requests-remaining", "?"),
        )
    return cache, kickoffs


def _dense_grid(kickoffs, start, end, stride_min, pre_hours):
    """Request times covering [kickoff - pre_hours, kickoff] per game, snapped to the global
    stride grid (overlapping windows collapse to shared timestamps)."""
    step = timedelta(minutes=stride_min)
    dense: set[datetime] = set()
    for ko_raw in kickoffs.values():
        ko = _parse_dt(ko_raw)
        w_start = _aligned(max(start, ko - timedelta(hours=pre_hours)), start, stride_min)
        w_end = min(end, ko)
        t = w_start
        while t <= w_end:
            if t >= start:
                dense.add(t)
            t += step
    return dense


async def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill historical odds for one league.")
    ap.add_argument("--sport-key", required=True, help="Odds API sport key (must be seeded)")
    ap.add_argument("--start", required=True, help="ISO date/datetime (UTC), inclusive")
    ap.add_argument("--end", help="ISO date/datetime (UTC), inclusive; default now")
    ap.add_argument(
        "--stride-min",
        type=int,
        default=30,
        help="minutes between snapshots (coarse = cheaper; default 30)",
    )
    ap.add_argument("--markets", default=MARKETS, help=f"comma markets (default {MARKETS})")
    ap.add_argument(
        "--books",
        default="",
        help="comma bookmaker keys to fetch (default: soft books + Pinnacle). Use this to "
        "backfill a specific subset, e.g. the sharp exchanges for a CLV reference. Cost is "
        "10 x markets x ceil(len(books)/10).",
    )
    ap.add_argument(
        "--match-day",
        action="store_true",
        help="discover kickoffs then sample only around games (recommended)",
    )
    ap.add_argument(
        "--pre-hours",
        type=int,
        default=6,
        help="[match-day] hours before kickoff to start sampling (default 6)",
    )
    ap.add_argument(
        "--discover-stride-hours",
        type=int,
        default=24,
        help="[match-day] hours between discovery calls (default 24)",
    )
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds between calls")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="estimate call count / credit cost without backfilling",
    )
    args = ap.parse_args()

    start = _parse_dt(args.start)
    end = _parse_dt(args.end) if args.end else datetime.now(UTC)
    if end < start:
        ap.error("--end is before --start")
    n_markets = len([m for m in args.markets.split(",") if m.strip()])

    print(f"League sport_key : {args.sport_key}")
    print(f"Window           : {start:%Y-%m-%d %H:%M} → {end:%Y-%m-%d %H:%M} UTC")
    print(f"Mode             : {'match-day' if args.match_day else 'uniform'}")

    if args.match_day:
        n_discover = len(_uniform_grid(start, end, args.discover_stride_hours * 60))
        print(f"Discovery calls  : {n_discover} (every {args.discover_stride_hours}h)")
        print(f"Dense sampling   : {args.stride_min} min stride, {args.pre_hours}h pre-kickoff")
        print(
            f"Est. credit cost : discovery >= {n_discover * 10 * n_markets}; "
            f"dense unknown until games are discovered (10 x {n_markets} markets x regions/call)"
        )
        if args.dry_run:
            print(
                "\n--dry-run: discovery would spend credits to find games, so dense cost "
                "can't be estimated dry. Run a short window live to gauge it."
            )
            return
    else:
        grid = _uniform_grid(start, end, args.stride_min)
        print(f"Stride / grid pts: {args.stride_min} min / {len(grid)} calls")
        print(
            f"Est. credit cost : >= {len(grid) * 10 * n_markets} "
            f"(10 x {n_markets} markets x regions); actual prints per call below"
        )
        if args.dry_run:
            print("\n--dry-run: no API calls made. Re-run without --dry-run to backfill.")
            return

    if not settings.the_odds_api_key:
        ap.error("THE_ODDS_API_KEY is not set")

    Session = get_sessionmaker()
    async with Session() as session:
        league = (
            await session.execute(select(League).where(League.sport_key == args.sport_key))
        ).scalar_one_or_none()
        if league is None:
            ap.error(f"league '{args.sport_key}' not seeded - add it to seed_leagues and re-run")

        books = args.books.strip() or _combined_books()
        last_price: dict[tuple, float] = {}
        ensured: set[date] = set()
        seen_ts: set[datetime] = set()
        total = {"events": 0, "changes": 0, "skipped": 0}
        calls = errors = 0

        async with httpx.AsyncClient(timeout=30) as client:
            cache: dict[datetime, tuple] = {}
            if args.match_day:
                cache, kickoffs = await _discover(
                    client,
                    args.sport_key,
                    books,
                    args.markets,
                    start,
                    end,
                    args.discover_stride_hours,
                )
                calls += len(cache)
                dense = _dense_grid(kickoffs, start, end, args.stride_min, args.pre_hours)
                request_times = sorted(set(cache) | dense)
                print(
                    f"Discovered {len(kickoffs)} kickoffs → {len(request_times)} total calls "
                    f"({len(request_times) - len(cache)} new dense + {len(cache)} cached)."
                )
            else:
                request_times = _uniform_grid(start, end, args.stride_min)

            for rt in request_times:
                if rt in cache:
                    payload, headers = cache[rt]  # discovery snapshot, already paid for
                else:
                    try:
                        payload, headers = await _fetch_historical(
                            client, args.sport_key, books, args.markets, rt
                        )
                    except httpx.HTTPStatusError as exc:
                        errors += 1
                        log.warning(
                            "  [%s] HTTP %s - skipped",
                            rt.strftime("%Y-%m-%d %H:%M"),
                            exc.response.status_code,
                        )
                        if errors >= 5 and calls == 0:
                            ap.error("first 5 calls all failed - check key/plan/coverage; aborting")
                        continue
                    calls += 1

                returned = _parse_dt(payload["timestamp"])
                if returned in seen_ts:  # finer stride hit the same snapshot; gate would no-op
                    continue
                seen_ts.add(returned)

                snap_ts, counts = await _ingest_snapshot(
                    session, payload, league, last_price, ensured
                )
                for k in total:
                    total[k] += counts[k]
                log.info(
                    "  [%s] snap=%s events=%2d changes=%3d skip=%2d  cost=%s remaining=%s",
                    rt.strftime("%Y-%m-%d %H:%M"),
                    snap_ts.strftime("%m-%d %H:%M"),
                    counts["events"],
                    counts["changes"],
                    counts["skipped"],
                    headers.get("x-requests-last", "?"),
                    headers.get("x-requests-remaining", "?"),
                )
                if args.sleep and rt not in cache:
                    await asyncio.sleep(args.sleep)

        print(f"\nDone. calls={calls} errors={errors} distinct_snapshots={len(seen_ts)}")
        print(
            f"  events={total['events']} snapshot_rows_written={total['changes']} "
            f"unmatched_skipped={total['skipped']}"
        )
        print(
            "Next: python -m scripts.replay_detect --sport-key "
            f"{args.sport_key} --start {start:%Y-%m-%d} --end {end:%Y-%m-%d} --settle --report"
        )


if __name__ == "__main__":
    asyncio.run(main())
