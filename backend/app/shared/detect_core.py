"""Pure detection core — the devig→EV→arb logic with NO I/O.

Factored out of `workers/detect.py` so the exact same opportunity-finding runs in two
places: the live consumer (reads Redis hot state, writes signals, routes) and the offline
backtest replay (feeds reconstructed historical state, grades against the closing line).
If these ever diverged, the CLV gate (NON-NEGOTIABLE #2) would validate something we don't
actually ship — so detection lives here, and both callers depend on it.

Input is the per-market book→selection→decimal map; output is a list of `Opportunity`
candidates including their dedup scope/bucket/hash. The caller owns the side effects:
flap-dedup (`_alert_allowed`), persistence, and fan-out.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from app.shared.math import devig, ev_pct, find_arb_multi, kelly


@dataclass
class Opportunity:
    kind: str  # "ev" | "arb"
    selection: str
    book: str
    offered_odds: float
    fair_prob: float
    edge_pct: float
    kelly_frac: float
    # Dedup inputs the caller needs (NON-NEGOTIABLE #3): `scope` identifies the opportunity
    # sans edge magnitude; `bucket` is the quantised edge; `dedup_hash` persists on the row.
    scope: str
    bucket: int
    dedup_hash: str
    meta: dict = field(default_factory=dict)


# A market's full selection set, so we never treat an incomplete market as a complete one: a
# soccer h2h missing its draw price is NOT a 2-way market, and an "arb" priced across only
# home+away is a coin-flip dressed up as guaranteed profit (it loses both legs on a draw).
# Likewise the sharp devig is only valid over the whole market. Unknown types fall back to
# ">= 2 selections" — we can't assert completeness we don't know.
MARKET_SELECTIONS: dict[str, frozenset[str]] = {
    "h2h": frozenset({"home", "draw", "away"}),
    "total": frozenset({"over", "under"}),
}


def _complete(market_type: str, present) -> bool:
    """True if `present` covers every selection the market type requires."""
    expected = MARKET_SELECTIONS.get(market_type)
    present = set(present)
    if expected is None:
        return len(present) >= 2
    return expected.issubset(present)


def _bucket(value: float, edge_bucket_pct: float) -> int:
    return int(value // edge_bucket_pct)


def _dedup_hash(*parts) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()


def find_opportunities(
    fixture_id: str,
    market_id: int,
    by_book: dict[str, dict[str, float]],
    *,
    is_soft: bool,
    sharp_ref_book: str,
    min_edge_pct: float,
    kelly_fraction: float,
    edge_bucket_pct: float,
    market_type: str = "",
    max_offered_odds: float = 12.0,
    max_edge_pct: float = 20.0,
    devig_method: str = "shin",
) -> list[Opportunity]:
    """All opportunities in one market's current prices. Order is EV (soft only) then arb,
    matching the live consumer so dedup side effects apply identically."""
    opps: list[Opportunity] = []
    sharp = by_book.get(sharp_ref_book)

    # ---- +EV vs the sharp fair line (soft leagues only — sharp/big leagues have no
    # soft-book edge; mechanical signals like arb still run for them below) ----
    if is_soft and sharp and _complete(market_type, sharp):
        fair = devig(sharp, devig_method)
        for book, sels in by_book.items():
            if book == sharp_ref_book:
                continue
            for sel, dec in sels.items():
                p = fair.get(sel)
                if p is None:
                    continue
                # Junk/suspended quote (e.g. decimal ~101) — not a bettable price, drop it
                # before it manufactures a fake edge.
                if dec > max_offered_odds:
                    continue
                edge = ev_pct(dec, p)
                if edge < min_edge_pct or edge > max_edge_pct:
                    continue
                bucket = _bucket(edge, edge_bucket_pct)
                opps.append(
                    Opportunity(
                        kind="ev",
                        selection=sel,
                        book=book,
                        offered_odds=dec,
                        fair_prob=p,
                        edge_pct=edge,
                        kelly_frac=kelly(p, dec, kelly_fraction),
                        scope=f"ev:{fixture_id}:{market_id}:{sel}:{book}",
                        bucket=bucket,
                        dedup_hash=_dedup_hash(fixture_id, market_id, sel, book, bucket),
                        meta={"sharp_book": sharp_ref_book},
                    )
                )

    # ---- cross-book arbitrage (best price per selection across all books) ----
    best: dict[str, tuple[str, float]] = {}
    for book, sels in by_book.items():
        for sel, dec in sels.items():
            # Same junk/suspended-quote guard the +EV path uses (line ~78): a book parks an
            # absurd price (e.g. decimal ~101) to effectively suspend a selection. Without
            # this, that price becomes the "best" leg and manufactures a fake arb whose price
            # isn't actually bettable (NON-NEGOTIABLE #1).
            if dec > max_offered_odds:
                continue
            if sel not in best or dec > best[sel][1]:
                best[sel] = (book, dec)
    if _complete(market_type, best):
        arb = find_arb_multi({sel: dec for sel, (_, dec) in best.items()})
        if arb is not None:
            profit = arb["profit_pct"]
            bucket = _bucket(profit, edge_bucket_pct)
            legs = {
                sel: {"book": bk, "odds": dec, "stake_frac": arb["stake_fracs"][sel]}
                for sel, (bk, dec) in best.items()
            }
            opps.append(
                Opportunity(
                    kind="arb",
                    selection="+".join(sorted(best)),
                    book="multi",
                    offered_odds=0.0,
                    fair_prob=0.0,
                    edge_pct=profit,
                    kelly_frac=0.0,
                    scope=f"arb:{fixture_id}:{market_id}",
                    bucket=bucket,
                    dedup_hash=_dedup_hash(fixture_id, market_id, "arb", bucket),
                    meta={"legs": legs},
                )
            )

    return opps
