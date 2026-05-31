"""Replay detection over backfilled odds_snapshots → signals → CLV gate (NON-NEGOTIABLE #2).

This is the offline backtest. It reconstructs each market's book→selection prices as they
evolved in history and runs the SAME detect_core.find_opportunities the live worker runs,
so a gate verdict means something about what we actually ship. The live flap-dedup is
replicated in-memory; signals are written with their historical `created_at` so the
existing settle.py grades CLV against the closing sharp line already in the snapshots.

CLV (did we beat the close) is computable from odds alone and is the gate. Win/loss P&L
needs final scores (not set by the odds backfill) — so result/pnl stay null here; pull
scores from API-Football later for the P&L sanity check. The gate doesn't need them.

Idempotent with --reset (clears prior signals+grades for the in-window fixtures first).
Only EV + arb are replayed (what find_opportunities covers); middles/promos are separate.

Run from backend/:
  python -m scripts.replay_detect --sport-key soccer_mexico_ligamx \
      --start 2026-03-01 --end 2026-04-15 --reset --settle --report
  # sweep a different edge threshold without touching config:
  python -m scripts.replay_detect --sport-key soccer_mexico_ligamx \
      --start 2026-03-01 --end 2026-04-15 --reset --settle --report --min-edge 3.0
"""

import argparse
import asyncio
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from itertools import groupby

from sqlalchemy import delete, select

from app.config import settings
from app.models.core import Fixture, League, Market
from app.models.odds import OddsSnapshot
from app.models.signals import Signal, SignalGrade
from app.scheduler.settle import settle_once
from app.shared.clv import GATE_BEAT_THRESHOLD, GATE_MIN_SAMPLE, clv_report_by_league
from app.shared.db import get_sessionmaker
from app.shared.detect_core import find_opportunities


def _parse_dt(s: str) -> datetime:
    s = s.strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.strptime(s, "%Y-%m-%d")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class _Dedup:
    """In-memory twin of detect._alert_allowed: emit on first sight or a strictly improved
    edge bucket, and let a scope re-fire once its last emit is older than the TTL."""

    def __init__(self, ttl_seconds: int):
        self.ttl = timedelta(seconds=ttl_seconds)
        self.best: dict[str, tuple[int, datetime]] = {}

    def allowed(self, scope: str, bucket: int, ts: datetime) -> bool:
        cur = self.best.get(scope)
        if cur is not None and (ts - cur[1]) <= self.ttl and bucket <= cur[0]:
            return False
        self.best[scope] = (bucket, ts)
        return True


async def _replay_fixture(
    session, fx: Fixture, lg: League, dedup: _Dedup, min_edge: float, max_lead_min: float | None
) -> list[Signal]:
    """Sweep one fixture's snapshots in time order, detecting on each market as it moves —
    mirroring the live 'detect the market that just changed' path.

    With `max_lead_min`, only emit signals detected within that many minutes of kickoff: the
    realizability window. State is still reconstructed from ALL snapshots (so prices are
    correct when we do detect), but detection/dedup only run inside the window — simulating
    'only alert near kickoff', where the soft price is actually bettable and the CLV test
    isn't confounded by hours of unrelated line drift before the close."""
    snaps = (
        (
            await session.execute(
                select(OddsSnapshot)
                .where(OddsSnapshot.fixture_id == fx.id)
                .order_by(OddsSnapshot.ts)
            )
        )
        .scalars()
        .all()
    )

    # state[market_id][book][selection] = decimal — the reconstructed hot state at 'now'.
    state: dict[int, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    out: list[Signal] = []

    # Market type per id — find_opportunities needs it to reject incomplete markets, exactly
    # as the live worker does (parity is what keeps the CLV gate honest).
    mids_all = {s.market_id for s in snaps}
    market_type: dict[int, str] = (
        dict(
            (
                await session.execute(select(Market.id, Market.type).where(Market.id.in_(mids_all)))
            ).all()
        )
        if mids_all
        else {}
    )

    for ts, group in groupby(snaps, key=lambda s: s.ts):
        dirty: set[int] = set()
        for s in group:
            state[s.market_id][s.book][s.selection] = s.decimal_odds
            dirty.add(s.market_id)
        if max_lead_min is not None:
            lead = (fx.kickoff_utc - ts).total_seconds() / 60
            if lead < 0 or lead > max_lead_min:  # before window / after kickoff → keep state, skip
                continue
        for mid in dirty:
            opps = find_opportunities(
                fx.id,
                mid,
                state[mid],
                is_soft=lg.is_soft,
                sharp_ref_book=lg.sharp_ref_book,
                min_edge_pct=min_edge,
                kelly_fraction=settings.kelly_fraction,
                edge_bucket_pct=settings.edge_bucket_pct,
                market_type=market_type.get(mid, ""),
                max_offered_odds=settings.max_offered_odds,
                max_edge_pct=settings.max_edge_pct,
                devig_method=settings.devig_method,
            )
            for opp in opps:
                if not dedup.allowed(opp.scope, opp.bucket, ts):
                    continue
                out.append(
                    Signal(
                        fixture_id=fx.id,
                        market_id=mid,
                        selection=opp.selection,
                        book=opp.book,
                        kind=opp.kind,
                        offered_odds=opp.offered_odds,
                        fair_prob=opp.fair_prob,
                        edge_pct=opp.edge_pct,
                        kelly_frac=opp.kelly_frac,
                        ttl_sec=settings.signal_ttl_seconds,
                        dedup_hash=opp.dedup_hash,
                        status="live",
                        meta=opp.meta,
                        created_at=ts,  # historical detection time (overrides server default)
                    )
                )
    return out


def _print_report(report) -> None:
    if not report:
        print("\nNo graded signals (nothing settled / no EV with a closing reference).")
        return
    print(f"\n{'League':24} {'n':>5} {'beats':>6} {'beat%':>7} {'lo95%':>7}  gate")
    print("-" * 60)
    for r in report:
        print(
            f"{r.league:24} {r.n:>5} {r.beats:>6} {r.beat_pct * 100:>6.1f}% "
            f"{r.lower_bound * 100:>6.1f}%  {'PASS' if r.passes() else 'hold'}"
        )
    print(
        f"\nGate: Wilson lower bound (1-sided 95%) of beat-CLV >= {GATE_BEAT_THRESHOLD * 100:.0f}% "
        f"over >= {GATE_MIN_SAMPLE} graded signals (NON-NEGOTIABLE #2)."
    )


async def main() -> None:
    ap = argparse.ArgumentParser(description="Replay detection over backfilled snapshots.")
    ap.add_argument("--sport-key", help="limit to one league (default: all leagues)")
    ap.add_argument("--start", required=True, help="kickoff window start, ISO (UTC)")
    ap.add_argument("--end", required=True, help="kickoff window end, ISO (UTC)")
    ap.add_argument(
        "--min-edge",
        type=float,
        default=settings.min_edge_pct,
        help=f"+EV threshold %% to replay (default {settings.min_edge_pct})",
    )
    ap.add_argument(
        "--max-lead-min",
        type=float,
        default=None,
        help="only emit signals detected within N minutes of kickoff "
        "(realizability window; default: no filter)",
    )
    ap.add_argument(
        "--reset",
        action="store_true",
        help="delete prior signals+grades for in-window fixtures first",
    )
    ap.add_argument("--settle", action="store_true", help="run settle_once() after replay")
    ap.add_argument("--report", action="store_true", help="print the CLV gate report after")
    args = ap.parse_args()

    start, end = _parse_dt(args.start), _parse_dt(args.end)
    Session = get_sessionmaker()

    async with Session() as session:
        fq = (
            select(Fixture, League)
            .join(League, Fixture.league_id == League.id)
            .where(Fixture.kickoff_utc >= start, Fixture.kickoff_utc <= end)
        )
        if args.sport_key:
            fq = fq.where(League.sport_key == args.sport_key)
        rows = (await session.execute(fq)).all()
        if not rows:
            print("No fixtures in window — backfill snapshots first.")
            return
        lead_desc = f", lead<={args.max_lead_min}min" if args.max_lead_min else ""
        print(
            f"Replaying {len(rows)} fixtures, min_edge={args.min_edge}%, "
            f"devig={settings.devig_method}{lead_desc}"
            + (f", league={args.sport_key}" if args.sport_key else " (all leagues)")
        )

        if args.reset:
            fids = [fx.id for fx, _ in rows]
            await session.execute(
                delete(SignalGrade).where(
                    SignalGrade.signal_id.in_(select(Signal.id).where(Signal.fixture_id.in_(fids)))
                )
            )
            await session.execute(delete(Signal).where(Signal.fixture_id.in_(fids)))
            await session.commit()

        dedup = _Dedup(settings.signal_ttl_seconds)
        produced = {"ev": 0, "arb": 0}
        for fx, lg in rows:
            sigs = await _replay_fixture(session, fx, lg, dedup, args.min_edge, args.max_lead_min)
            for s in sigs:
                produced[s.kind] = produced.get(s.kind, 0) + 1
            session.add_all(sigs)
        await session.commit()
        print(f"Signals produced: ev={produced.get('ev', 0)} arb={produced.get('arb', 0)}")

    if args.settle:
        stats = await settle_once()
        print(f"Settle: {stats}")
    if args.report:
        async with Session() as session:
            _print_report(await clv_report_by_league(session))


if __name__ == "__main__":
    asyncio.run(main())
