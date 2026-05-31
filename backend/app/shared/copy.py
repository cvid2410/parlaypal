"""Template copy engine (NON-NEGOTIABLE #1).

User-facing signal text comes ONLY from approved templates filled with computed values —
never a runtime LLM. For an individual +EV bet we never imply certainty of winning
("guaranteed", "lock", "can't lose", ...). Arbitrage may say "guaranteed profit" because
it mathematically is.

`explain` is a pure function of a context object so it's trivially testable and
deterministic: the same `dedup_hash` always picks the same template variant, so re-rendering
a signal yields identical text.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from app.shared.math import decimal_to_american

RG_FOOTER = (
    "For entertainment, not financial advice. Bet responsibly — if it stops being fun, "
    "step away. 1-800-GAMBLER."
)

_BOOK_LABELS = {
    "draftkings": "DraftKings",
    "fanduel": "FanDuel",
    "betmgm": "BetMGM",
    "pinnacle": "Pinnacle",
    "williamhill_us": "William Hill",
    "betrivers": "BetRivers",
    "caesars": "Caesars",
}

# Phrases that must never appear for an individual +EV bet. Checked by the lint test.
BANNED_EV_PHRASES = [
    "guaranteed", "guarantee", "can't lose", "cannot lose", "sure thing", "sure bet",
    "risk-free", "riskless", "no risk", "100%", "easy money", "free money", "lock",
]


def book_label(book: str) -> str:
    return _BOOK_LABELS.get(book, book.replace("_", " ").title())


def selection_label(market_type: str, line: float | None, selection: str,
                    home: str, away: str) -> str:
    if market_type == "h2h":
        return {"home": f"{home} to win", "away": f"{away} to win", "draw": "Draw"}.get(
            selection, selection
        )
    if market_type == "total":
        side = selection.capitalize()  # Over / Under
        return f"{side} {line} goals"
    return selection


@dataclass
class SignalCopyContext:
    kind: str  # ev | arb
    dedup_hash: str
    league_name: str
    home: str
    away: str
    market_type: str
    line: float | None
    selection: str
    country: str = ""
    # EV fields
    book: str = ""
    offered_decimal: float = 0.0
    fair_prob: float = 0.0
    edge_pct: float = 0.0
    kelly_frac: float = 0.0
    # ARB fields: list of {"selection","book","decimal","stake_frac"}
    legs: list[dict] = field(default_factory=list)

    @property
    def fixture_label(self) -> str:
        return f"{self.home} vs {self.away}"


_EV_TEMPLATES = [
    "{pick} is priced high at {book}. Sharp books imply a fair line near {fair_am}, but "
    "{book} still has {odds} — about {edge}% of value on your side. {stake}",
    "Value on {pick}. {book}'s {odds} beats the sharp fair price ({fair_am}) by roughly "
    "{edge}%. Over many bets that gap is your edge. {stake}",
    "{book} is slow to move on {pick}: {odds} versus a fair {fair_am}. That ~{edge}% "
    "overlay is where the long-run profit comes from. {stake}",
    "The math likes {pick} here — {book} offers {odds}, the sharp fair line is {fair_am}, "
    "an edge of about {edge}%. {stake}",
]

_ARB_TEMPLATES = [
    "Arbitrage on {fixture}: cover every outcome across books for a locked-in {profit}% "
    "profit no matter the result. {legs}",
    "Guaranteed-profit arb ({profit}%) on {fixture}. Split your stake across the books "
    "below and any result wins. {legs}",
    "Two books disagree on {fixture}. Back each outcome at the prices below for a "
    "mathematically guaranteed {profit}% return. {legs}",
]


def _variant(pool: list[str], dedup_hash: str) -> str:
    # Deterministic pick from any string (don't assume dedup_hash is hex) so copy
    # selection can never crash delivery.
    idx = int(hashlib.sha1(dedup_hash.encode()).hexdigest(), 16) % len(pool)
    return pool[idx]


def _stake_sentence(kelly_frac: float) -> str:
    if kelly_frac <= 0:
        return ""
    pct = kelly_frac * 100
    return f"Suggested stake: {pct:.1f}% of your bankroll (fractional Kelly)."


def explain(ctx: SignalCopyContext) -> dict:
    """Render a signal into {title, body, footer, fields} from approved templates."""
    if ctx.kind == "arb":
        legs_txt = " · ".join(
            f"{selection_label(ctx.market_type, ctx.line, leg['selection'], ctx.home, ctx.away)} "
            f"@ {book_label(leg['book'])} {decimal_to_american(leg['decimal'])} "
            f"(stake {leg['stake_frac'] * 100:.0f}%)"
            for leg in ctx.legs
        )
        body = _variant(_ARB_TEMPLATES, ctx.dedup_hash).format(
            fixture=ctx.fixture_label, profit=f"{ctx.edge_pct:.1f}", legs=legs_txt
        )
        title = f"Arbitrage — {ctx.fixture_label}"
        fields = {
            "league": ctx.league_name,
            "fixture": ctx.fixture_label,
            "profit_pct": round(ctx.edge_pct, 2),
            "legs": legs_txt,
        }
        return {"title": title, "body": body, "footer": RG_FOOTER, "fields": fields}

    # ---- EV ----
    pick = selection_label(ctx.market_type, ctx.line, ctx.selection, ctx.home, ctx.away)
    odds_am = decimal_to_american(ctx.offered_decimal)
    fair_am = decimal_to_american(1 / ctx.fair_prob) if ctx.fair_prob > 0 else "n/a"
    body = _variant(_EV_TEMPLATES, ctx.dedup_hash).format(
        pick=pick, book=book_label(ctx.book), odds=odds_am, fair_am=fair_am,
        edge=f"{ctx.edge_pct:.1f}", stake=_stake_sentence(ctx.kelly_frac),
    ).strip()
    title = f"Value Bet — {pick}"
    fields = {
        "league": ctx.league_name,
        "fixture": ctx.fixture_label,
        "pick": pick,
        "book": book_label(ctx.book),
        "odds": odds_am,
        "fair_odds": fair_am,
        "edge_pct": round(ctx.edge_pct, 2),
        "stake_pct": round(ctx.kelly_frac * 100, 2),
    }
    return {"title": title, "body": body, "footer": RG_FOOTER, "fields": fields}
