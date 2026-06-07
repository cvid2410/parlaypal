"""Layer 3 — clean CLV: detect +EV at the OPEN, grade against the TRUE close.

The old gate detected ~2h before kickoff and graded vs a sharp line ~2h later that barely
moved, so beat-CLV ≈ the selection condition re-measured (tautological). Now that the live
pipeline has captured true opening lines (~9-day avg lead), we can detect at the open and grade
against the actual close — so "beat the close" is a real, temporally-independent prediction.

Per settled soft-league h2h fixture:
  open_fair  = shin-devig of the EARLIEST complete 3-way Pinnacle snapshot
  close_fair = shin-devig of the LATEST  complete 3-way Pinnacle snapshot <= kickoff
  For each soft book's opening price p on selection sel with ev_pct(p, open_fair[sel]) >= edge:
     clean beat-CLV : p > 1/close_fair[sel]          (did we beat the true sharp close?)
     sharp_move     : close_fair[sel] - open_fair[sel]  (did Pinnacle steam toward our pick?)
     result / pnl   : from the final score (h2h, no push).

Per league we print: n, clean beat-CLV%, mean sharp_move (pp), realized ROI. The decisive
cross-check is beat% vs ROI: if a static Pinnacle makes beat% high while ROI is negative, CLV
is still tautological and CANNOT certify the league.

Run from backend/:  python -m scripts.clean_clv [--min-edge 2.0]
"""

import argparse
import asyncio
from collections import defaultdict

from sqlalchemy import select

from app.models.core import Fixture, League, Market
from app.models.odds import OddsSnapshot
from app.shared.db import get_sessionmaker
from app.shared.math import devig, ev_pct

H2H = frozenset({"home", "draw", "away"})
SHARP = "pinnacle"
MAX_DEC = 12.0  # junk/suspended-quote guard (same as detection)


def _outcome(hs: int, as_: int) -> str:
    return "home" if hs > as_ else "away" if as_ > hs else "draw"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-edge", type=float, default=2.0)
    args = ap.parse_args()

    Session = get_sessionmaker()
    async with Session() as s:
        h2h_mid = (
            await s.execute(select(Market.id).where(Market.type == "h2h"))
        ).scalar_one_or_none()
        if h2h_mid is None:
            print("no h2h market")
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
        fids = list(fx_meta)

        rows = []
        for i in range(0, len(fids), 300):
            rows += (
                await s.execute(
                    select(
                        OddsSnapshot.fixture_id,
                        OddsSnapshot.book,
                        OddsSnapshot.selection,
                        OddsSnapshot.decimal_odds,
                        OddsSnapshot.ts,
                    ).where(
                        OddsSnapshot.market_id == h2h_mid,
                        OddsSnapshot.fixture_id.in_(fids[i : i + 300]),
                    )
                )
            ).all()

    # fixture -> book -> selection -> ordered [(ts, dec)]
    by_fx: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for fid, book, sel, dec, ts in rows:
        by_fx[fid][book][sel].append((ts, dec))

    # per league: list of (beat_bool, sharp_move, pnl)
    stats: dict[str, list] = defaultdict(list)
    for fid, books in by_fx.items():
        lg, ko, hs, as_ = fx_meta[fid]
        pin = books.get(SHARP)
        if not pin or not H2H.issubset(pin):
            continue
        # Pinnacle open = earliest ts where all 3 present; close = latest ts <= ko, all 3 present
        pin_ts = sorted({t for sel in pin for t, _ in pin[sel]})
        open_px, close_px = {}, {}
        for ts in pin_ts:
            px = {sel: d for sel in H2H for t, d in pin[sel] if t == ts}
            if H2H.issubset(px):
                if not open_px:
                    open_px = px
                if ts <= ko:
                    close_px = px
        if not (H2H.issubset(open_px) and H2H.issubset(close_px)):
            continue
        open_fair = devig(open_px, "shin")
        close_fair = devig(close_px, "shin")
        if not (H2H.issubset(open_fair) and H2H.issubset(close_fair)):
            continue
        outcome = _outcome(hs, as_)

        for book, sels in books.items():
            if book == SHARP:
                continue
            for sel, series in sels.items():
                if sel not in H2H:
                    continue
                p = sorted(series)[0][1]  # the book's opening price on this selection
                if p > MAX_DEC or p <= 1:
                    continue
                edge = ev_pct(p, open_fair[sel])
                if edge < args.min_edge:
                    continue
                beat = p > (1.0 / close_fair[sel])
                sharp_move = close_fair[sel] - open_fair[sel]
                pnl = (p - 1.0) if sel == outcome else -1.0
                stats[lg].append((beat, sharp_move, pnl))

    hdr = f"{'League':22}{'n':>6}{'beatCLV%':>10}{'sharp_move':>12}{'ROI%':>9}"
    print(hdr)
    print("-" * len(hdr))
    pool = []
    for lg in sorted(stats):
        rs = stats[lg]
        pool += rs
        n = len(rs)
        beat = 100 * sum(b for b, _, _ in rs) / n
        mv = 100 * sum(m for _, m, _ in rs) / n  # in probability points
        roi = 100 * sum(p for _, _, p in rs) / n
        print(f"{lg:22}{n:>6}{beat:>9.1f}%{mv:>11.2f}{roi:>8.1f}%")
    print("-" * len(hdr))
    n = len(pool)
    if n:
        beat = 100 * sum(b for b, _, _ in pool) / n
        mv = 100 * sum(m for _, m, _ in pool) / n
        roi = 100 * sum(p for _, _, p in pool) / n
        print(f"{'POOLED':22}{n:>6}{beat:>9.1f}%{mv:>11.2f}{roi:>8.1f}%")
    print(
        "\nbeatCLV% = soft open price > sharp no-vig CLOSE (temporally independent)."
        "\nsharp_move = mean (close-open) prob on the bet selection, pp (>0 = sharp toward us)."
        "\nROI% = realized return. beat% high + ROI<0 => CLV still tautological, cannot certify."
    )


if __name__ == "__main__":
    asyncio.run(main())
