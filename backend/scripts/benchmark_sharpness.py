"""Layer-2 prototype: is Pinnacle a sharp benchmark on each league? (v2 spec)

CLV means nothing unless the sharp close is actually sharp. Epistemically-prior test
(advisor): does Pinnacle's CLOSING no-vig line predict outcomes better than its OPENING
line on this specific league? If the line sharpens toward the truth, Pinnacle is a valid
benchmark there; if not (or we can't tell), the league is no-serve.

Operationalised per league on backtested h2h (1X2) data we already have:
  * open  = earliest COMPLETE 3-way Pinnacle h2h snapshot, shin-devigged → prob vector.
  * close = latest complete 3-way snapshot at/before kickoff.
  * outcome = home/draw/away from the final score.
  * Brier(p) = sum_sel (p_sel - 1[sel==outcome])^2  (lower = better calibrated).
  * Per league: paired (Brier_open - Brier_close) → mean + t-stat. t > 1.65 ⇒ the close is
    significantly sharper ⇒ Pinnacle moves informatively here ⇒ SHARP. Also report movement
    toward the winner (close_p[winner] - open_p[winner]) and absolute Brier for context.

Verdict: SHARP (t>1.65, n>=30) · NOT-SHARP (t<-1.65) · INDETERMINATE (otherwise / thin) — and
INDETERMINATE ≡ no-serve (can't distinguish a sharp open from no money ever arriving).

Run from backend/:  python -m scripts.benchmark_sharpness
"""

import asyncio
import math
from collections import defaultdict

from sqlalchemy import select

from app.models.core import Fixture, League, Market
from app.models.odds import OddsSnapshot
from app.shared.db import get_sessionmaker
from app.shared.math import devig

H2H = frozenset({"home", "draw", "away"})
MIN_N = 30


def _outcome(hs: int, as_: int) -> str:
    return "home" if hs > as_ else "away" if as_ > hs else "draw"


def _brier(p: dict[str, float], outcome: str) -> float:
    return sum((p.get(sel, 0.0) - (1.0 if sel == outcome else 0.0)) ** 2 for sel in H2H)


async def main() -> None:
    Session = get_sessionmaker()
    async with Session() as s:
        h2h_mid = (
            await s.execute(select(Market.id).where(Market.type == "h2h"))
        ).scalar_one_or_none()
        if h2h_mid is None:
            print("no h2h market seeded")
            return

        fixtures = (
            await s.execute(
                select(
                    Fixture.id,
                    League.name,
                    Fixture.kickoff_utc,
                    Fixture.home_score,
                    Fixture.away_score,
                )
                .join(League, League.id == Fixture.league_id)
                .where(League.is_soft, Fixture.home_score.isnot(None))
            )
        ).all()
        fx_meta = {fid: (lg, ko, hs, as_) for fid, lg, ko, hs, as_ in fixtures}
        if not fx_meta:
            print("no scored soft fixtures")
            return

        # All Pinnacle h2h snapshots for those fixtures (batched IN-lists, no SQL sort — we
        # sort per fixture in Python; a global ORDER BY over the firehose exhausts /dev/shm).
        fids = list(fx_meta)
        rows = []
        for i in range(0, len(fids), 300):
            rows += (
                await s.execute(
                    select(
                        OddsSnapshot.fixture_id,
                        OddsSnapshot.selection,
                        OddsSnapshot.decimal_odds,
                        OddsSnapshot.ts,
                    ).where(
                        OddsSnapshot.book == "pinnacle",
                        OddsSnapshot.market_id == h2h_mid,
                        OddsSnapshot.fixture_id.in_(fids[i : i + 300]),
                    )
                )
            ).all()

    # fixture -> ordered list of (ts, {sel: dec}) where each entry is one timestamp's prices
    by_fx_ts: dict[str, dict] = defaultdict(lambda: defaultdict(dict))
    for fid, sel, dec, ts in rows:
        by_fx_ts[fid][ts][sel] = dec

    # Per-league paired samples: (brier_open, brier_close, winner_move)
    samples: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    for fid, ts_map in by_fx_ts.items():
        lg, ko, hs, as_ = fx_meta[fid]
        # complete 3-way snapshots only, in time order
        complete = [(ts, px) for ts, px in sorted(ts_map.items()) if H2H.issubset(px) and ts <= ko]
        if len(complete) < 2:
            continue
        p_open = devig(complete[0][1], "shin")
        p_close = devig(complete[-1][1], "shin")
        if not (H2H.issubset(p_open) and H2H.issubset(p_close)):
            continue
        outcome = _outcome(hs, as_)
        samples[lg].append(
            (_brier(p_open, outcome), _brier(p_close, outcome), p_close[outcome] - p_open[outcome])
        )

    cols = f"{'n':>5}{'Brier_open':>11}{'Brier_close':>12}{'t(impr)':>9}{'win_move':>10}"
    print(f"{'League':20}{cols}  verdict")
    print("-" * 86)
    pooled = []
    for lg in sorted(samples):
        rows_ = samples[lg]
        n = len(rows_)
        pooled += rows_
        bo = sum(r[0] for r in rows_) / n
        bc = sum(r[1] for r in rows_) / n
        diffs = [r[0] - r[1] for r in rows_]  # open - close; >0 means close is sharper
        md = sum(diffs) / n
        sd = (sum((d - md) ** 2 for d in diffs) / (n - 1)) ** 0.5 if n > 1 else 0.0
        t = md / (sd / math.sqrt(n)) if sd > 0 else 0.0
        wm = sum(r[2] for r in rows_) / n
        if n < MIN_N:
            verdict = "INDET (thin)"
        elif t > 1.65:
            verdict = "SHARP"
        elif t < -1.65:
            verdict = "NOT-SHARP"
        else:
            verdict = "INDET (no signal)"
        print(f"{lg:20}{n:>5}{bo:>11.3f}{bc:>12.3f}{t:>9.2f}{wm:>10.3f}  {verdict}")

    n = len(pooled)
    bo = sum(r[0] for r in pooled) / n
    bc = sum(r[1] for r in pooled) / n
    diffs = [r[0] - r[1] for r in pooled]
    md = sum(diffs) / n
    sd = (sum((d - md) ** 2 for d in diffs) / (n - 1)) ** 0.5
    t = md / (sd / math.sqrt(n))
    print("-" * 86)
    print(f"{'POOLED':20}{n:>5}{bo:>11.3f}{bc:>12.3f}{t:>9.2f}{'':>10}")
    print(
        "\nSHARP = close significantly better calibrated than open (Pinnacle moves toward truth)."
        "\nINDETERMINATE ≡ no-serve (can't tell a sharp open from no information arriving)."
    )


if __name__ == "__main__":
    asyncio.run(main())
