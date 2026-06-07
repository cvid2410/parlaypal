"""Road A - clean CLV against a MULTI-BOOK CONSENSUS reference (the OddsJam method).

clean_clv.py used Pinnacle alone as the fair reference and found it disconfirmed. Pinnacle
isn't sharp on the soft tail - but maybe the *consensus of many books* is a better truth
estimate (OddsJam builds "fair %" from a sharp/low-vig consensus, not one book). This tests
that: does betting a book that's an outlier vs the de-vigged book consensus actually pay?

Per settled soft-league h2h fixture, at OPEN and CLOSE:
  per-book no-vig = shin-devig of that book's complete 3-way prices.
  consensus_fair[sel] = mean of per-book no-vig across books (EXCLUDING the book being
                        evaluated, so a book's own outlier can't define the line it beats).
  For each book b's opening price p on sel with ev_pct(p, consensus_open_excl_b[sel]) >= edge:
     beatCLV   : p > 1/consensus_close_excl_b[sel]   (beat the consensus close)
     cons_move : consensus_close[sel] - consensus_open[sel]  (did the crowd steam toward us?)
     pnl       : from final score (h2h, no push).

Liquidity gate: only fixtures with >= --min-books books at open (a real consensus). Per league
we print n, avg books, beatCLV%, mean cons_move (pp), realized ROI. Decisive cross-check is
beat% vs ROI - same as clean_clv.py.

Run from backend/:  python -m scripts.clv_consensus [--min-edge 2.0] [--min-books 5]
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
MAX_DEC = 12.0
# The genuinely-sharp, ~zero-vig venues (Pinnacle + the betting exchanges). With --sharp-only
# the consensus reference is built from JUST these, and we never bet them - the OddsJam-style
# "fair from a sharp reference" test, now possible because we backfilled exchange history.
SHARP_SET = frozenset(
    {"pinnacle", "betfair_ex_uk", "betfair_ex_eu", "smarkets", "betfair_sb_uk", "matchbook"}
)


def _outcome(hs: int, as_: int) -> str:
    return "home" if hs > as_ else "away" if as_ > hs else "draw"


def _book_novig(px: dict[str, float]) -> dict[str, float] | None:
    if not H2H.issubset(px) or any(d <= 1 or d > MAX_DEC for d in px.values()):
        return None
    nv = devig(px, "shin")
    return nv if H2H.issubset(nv) else None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-edge", type=float, default=2.0)
    ap.add_argument(
        "--min-books", type=int, default=5, help="liquidity gate: reference books at open"
    )
    ap.add_argument(
        "--sharp-only",
        action="store_true",
        help="build the consensus reference from the sharp/exchange subset only (and never bet "
        "those books) - the OddsJam-style sharp-reference test.",
    )
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

    by_fx: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for fid, book, sel, dec, ts in rows:
        by_fx[fid][book][sel].append((ts, dec))

    stats: dict[str, list] = defaultdict(list)
    nbooks_by_lg: dict[str, list] = defaultdict(list)
    for fid, books in by_fx.items():
        lg, ko, hs, as_ = fx_meta[fid]
        # per-book open price + per-book open/close no-vig
        open_price, open_nv, close_nv = {}, {}, {}
        for book, sels in books.items():
            o_px = {sel: sorted(v)[0][1] for sel, v in sels.items() if sel in H2H}
            c_px = {}
            for sel, v in sels.items():
                if sel in H2H:
                    pre = sorted([(t, d) for t, d in v if t <= ko])  # snapshots at/before kickoff
                    if pre:
                        c_px[sel] = pre[-1][1]  # latest <= kickoff = the close
            open_price[book] = o_px
            nv_o = _book_novig(o_px)
            nv_c = _book_novig(c_px)
            if nv_o:
                open_nv[book] = nv_o
            if nv_c:
                close_nv[book] = nv_c

        # The reference set: sharp/exchange subset only, or all books.
        ref_open = {b: nv for b, nv in open_nv.items() if not args.sharp_only or b in SHARP_SET}
        ref_close = {b: nv for b, nv in close_nv.items() if not args.sharp_only or b in SHARP_SET}
        if len(ref_open) < args.min_books or len(ref_close) < 2:
            continue
        nbooks_by_lg[lg].append(len(ref_open))
        # consensus sums (for leave-one-out exclusion when the bet book is in the reference)
        so = {sel: sum(nv[sel] for nv in ref_open.values()) for sel in H2H}
        sc = {sel: sum(nv[sel] for nv in ref_close.values()) for sel in H2H}
        no, nc = len(ref_open), len(ref_close)
        outcome = _outcome(hs, as_)

        for b, o_px in open_price.items():
            if args.sharp_only and b in SHARP_SET:
                continue  # never bet the reference books
            # consensus excluding b (only matters when b is itself in the reference)
            if b in ref_open and no > 1:
                cons_o = {sel: (so[sel] - ref_open[b][sel]) / (no - 1) for sel in H2H}
            else:
                cons_o = {sel: so[sel] / no for sel in H2H}
            if b in ref_close and nc > 1:
                cons_c = {sel: (sc[sel] - ref_close[b][sel]) / (nc - 1) for sel in H2H}
            else:
                cons_c = {sel: sc[sel] / nc for sel in H2H}
            for sel in H2H:
                p = o_px.get(sel)
                if p is None or p <= 1 or p > MAX_DEC:
                    continue
                if cons_o[sel] <= 0 or cons_c[sel] <= 0:
                    continue
                if ev_pct(p, cons_o[sel]) < args.min_edge:
                    continue
                beat = p > (1.0 / cons_c[sel])
                move = cons_c[sel] - cons_o[sel]
                pnl = (p - 1.0) if sel == outcome else -1.0
                stats[lg].append((beat, move, pnl))

    hdr = f"{'League':22}{'n':>6}{'books':>7}{'beatCLV%':>10}{'cons_move':>11}{'ROI%':>9}"
    ref = "SHARP/exchange subset" if args.sharp_only else "all books"
    print(f"reference: {ref} · min-edge {args.min_edge} · min-books {args.min_books}\n")
    print(hdr)
    print("-" * len(hdr))
    pool = []
    for lg in sorted(stats):
        rs = stats[lg]
        pool += rs
        n = len(rs)
        avgb = sum(nbooks_by_lg[lg]) / len(nbooks_by_lg[lg]) if nbooks_by_lg[lg] else 0
        beat = 100 * sum(b for b, _, _ in rs) / n
        mv = 100 * sum(m for _, m, _ in rs) / n
        roi = 100 * sum(p for _, _, p in rs) / n
        print(f"{lg:22}{n:>6}{avgb:>7.1f}{beat:>9.1f}%{mv:>10.2f}{roi:>8.1f}%")
    print("-" * len(hdr))
    n = len(pool)
    if n:
        beat = 100 * sum(b for b, _, _ in pool) / n
        mv = 100 * sum(m for _, m, _ in pool) / n
        roi = 100 * sum(p for _, _, p in pool) / n
        print(f"{'POOLED':22}{n:>6}{'':>7}{beat:>9.1f}%{mv:>10.2f}{roi:>8.1f}%")
    print(
        "\ncons_move = mean (close-open) consensus prob on the bet selection, pp"
        " (>0 = reference steamed toward us)."
        "\nbeat% high + ROI<0 => beating the reference close is still not edge."
    )


if __name__ == "__main__":
    asyncio.run(main())
