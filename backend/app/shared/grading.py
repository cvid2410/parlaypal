"""Pure grading math: CLV (beat the closing line), bet result, and P&L in units.

CLV is the metric that matters (CLAUDE.md NON-NEGOTIABLE #2): if our +EV picks don't beat
the closing line, our fair-prob is wrong. It's computable purely from our own odds history
(no results feed). Win/loss needs the final score.
"""
from __future__ import annotations


def clv_beat(offered_decimal: float, closing_decimal: float | None) -> bool | None:
    """Did the price we alerted beat the sharp closing line?

    True when our decimal odds are longer (better payout) than the closing decimal odds for
    the same selection. None when there's no closing reference to compare against.
    """
    if not closing_decimal or closing_decimal <= 1:
        return None
    return offered_decimal > closing_decimal


def compute_result(home_score: int, away_score: int, market_type: str,
                  line: float | None, selection: str) -> str | None:
    """win | loss | push for a settled fixture, or None if not gradable."""
    if market_type == "h2h":
        winner = "home" if home_score > away_score else "away" if away_score > home_score else "draw"
        return "win" if selection == winner else "loss"
    if market_type == "total":
        if line is None:
            return None
        total = home_score + away_score
        if total == line:
            return "push"
        over = total > line
        if selection == "over":
            return "win" if over else "loss"
        if selection == "under":
            return "win" if not over else "loss"
    return None


def pnl_units(result: str | None, offered_decimal: float, stake_units: float = 1.0) -> float | None:
    """P&L in units for a 1-unit stake. Win pays (odds-1)*stake, loss -stake, push 0."""
    if result == "win":
        return stake_units * (offered_decimal - 1)
    if result == "loss":
        return -stake_units
    if result == "push":
        return 0.0
    return None
