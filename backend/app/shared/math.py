"""Core betting math (reference implementations from CLAUDE.md).

All probability/EV math works in DECIMAL odds. American is display-only.
"""
from __future__ import annotations


def american_to_decimal(o: float) -> float:
    """American odds → decimal odds. +150 -> 2.5, -200 -> 1.5."""
    return 1 + (o / 100 if o > 0 else 100 / abs(o))


def decimal_to_american(dec: float) -> str:
    """Decimal odds → American display string. 2.5 -> '+150', 1.5 -> '-200'."""
    if dec >= 2.0:
        return f"+{int(round((dec - 1) * 100))}"
    return str(int(round(-100 / (dec - 1))))


def no_vig_prob(dec_a: float, dec_b: float) -> float:
    """Devig a 2-way market → true probability of side A.

    Strips the bookmaker margin by normalising the two implied probabilities.
    """
    ia, ib = 1 / dec_a, 1 / dec_b
    return ia / (ia + ib)


def ev_pct(your_dec: float, true_prob: float) -> float:
    """Expected value (percent) of taking `your_dec` when truth is `true_prob`. >0 is +EV."""
    return (your_dec * true_prob - 1) * 100


def find_arb(dec_a: float, dec_b: float) -> dict | None:
    """2-way arbitrage. Returns profit % + stake split, or None if no arb.

    An arb exists when the inverse odds sum to < 1 (the book pair leaves a gap).
    """
    margin = 1 - (1 / dec_a + 1 / dec_b)
    if margin <= 0:
        return None
    inv_a, inv_b = 1 / dec_a, 1 / dec_b
    return {
        "profit_pct": margin * 100,
        "stake_a_frac": inv_a / (inv_a + inv_b),
        "stake_b_frac": inv_b / (inv_a + inv_b),
    }


def kelly(true_prob: float, dec_odds: float, fraction: float = 0.25) -> float:
    """Fractional Kelly stake as a fraction of bankroll. Clamped at 0 (never bet -EV)."""
    b = dec_odds - 1
    if b <= 0:
        return 0.0
    f = (true_prob * b - (1 - true_prob)) / b
    return max(0.0, f * fraction)


def devig_multi(odds_by_sel: dict[str, float]) -> dict[str, float]:
    """Devig an N-way market → fair probability per selection.

    Generalises `no_vig_prob` to soccer's 3-way h2h (home/draw/away) and any other
    market by normalising the implied probabilities across all selections.
    """
    inv = {sel: 1 / dec for sel, dec in odds_by_sel.items() if dec and dec > 1}
    total = sum(inv.values())
    if total <= 0:
        return {}
    return {sel: v / total for sel, v in inv.items()}


def find_middle(over_dec: float, over_line: float,
               under_dec: float, under_line: float) -> dict | None:
    """A totals 'middle': back Over at a low line and Under at a high line so a final total
    landing strictly between wins BOTH. Returns the window + P&L, or None if no middle.

    With equal-payout staking (s = 1/over_dec + 1/under_dec):
      - exactly one side wins → return 1/s per unit staked  → miss P&L = (1/s - 1)
      - both win (it middles)  → return 2/s                 → middle P&L = (2/s - 1)
    s < 1 means it's also an arb (profits even on a miss).
    """
    import math as _m
    if over_line >= under_line:
        return None
    window = [n for n in range(_m.floor(over_line) + 1, _m.ceil(under_line))
              if over_line < n < under_line]
    if not window:
        return None
    s = 1 / over_dec + 1 / under_dec
    return {
        "window": window,
        "hold": s,
        "miss_pnl_pct": (1 / s - 1) * 100,
        "middle_pnl_pct": (2 / s - 1) * 100,
        "stake_over_frac": (1 / over_dec) / s,
        "stake_under_frac": (1 / under_dec) / s,
    }


def find_arb_multi(best_odds_by_sel: dict[str, float]) -> dict | None:
    """N-way arbitrage across the best price per selection.

    Returns profit % + per-selection stake fractions, or None if the inverse-odds sum
    is >= 1 (no arb). Works for 2-way (over/under) and 3-way (home/draw/away).
    """
    inv = {sel: 1 / dec for sel, dec in best_odds_by_sel.items() if dec and dec > 1}
    total = sum(inv.values())
    if total <= 0 or total >= 1:
        return None
    return {
        "profit_pct": (1 - total) * 100,
        "stake_fracs": {sel: v / total for sel, v in inv.items()},
    }
