"""Template copy engine (NON-NEGOTIABLE #1).

User-facing signal text comes ONLY from approved templates filled with computed values -
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

from app.shared.math import format_odds

RG_FOOTER = (
    "For entertainment, not financial advice. Bet responsibly - if it stops being fun, "
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
    "guaranteed",
    "guarantee",
    "can't lose",
    "cannot lose",
    "sure thing",
    "sure bet",
    "risk-free",
    "riskless",
    "no risk",
    "100%",
    "easy money",
    "free money",
    "lock",
]


def book_label(book: str) -> str:
    return _BOOK_LABELS.get(book, book.replace("_", " ").title())


def selection_label(
    market_type: str, line: float | None, selection: str, home: str, away: str
) -> str:
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
    home_logo: str | None = None
    away_logo: str | None = None
    kickoff: str = ""  # fixture kickoff, ISO (shown on the card so the bettor knows game time)
    # EV fields
    book: str = ""
    offered_decimal: float = 0.0
    fair_prob: float = 0.0
    edge_pct: float = 0.0
    kelly_frac: float = 0.0
    # ARB / MIDDLE legs: list of {"selection","book","decimal","stake_frac"[,"line"]}
    legs: list[dict] = field(default_factory=list)
    window: list | None = None  # middle: integers that win both sides

    @property
    def fixture_label(self) -> str:
        return f"{self.home} vs {self.away}"


_EV_TEMPLATES = [
    "{pick} is priced high at {book}. Sharp books imply a fair line near {fair_am}, but "
    "{book} still has {odds} - about {edge}% of value on your side. {stake}",
    "Value on {pick}. {book}'s {odds} beats the sharp fair price ({fair_am}) by roughly "
    "{edge}%. Over many bets that gap is your edge. {stake}",
    "{book} is slow to move on {pick}: {odds} versus a fair {fair_am}. That ~{edge}% "
    "overlay is where the long-run profit comes from. {stake}",
    "The math likes {pick} here - {book} offers {odds}, the sharp fair line is {fair_am}, "
    "an edge of about {edge}%. {stake}",
]

_VALUE_TEMPLATES = [
    "{pick} is off-market at {book}: {odds} versus a market-consensus fair of {fair_am} - "
    "about {edge}% of value. The wider book market disagrees with {book} here. {stake}",
    "{book} is out of line on {pick} - {odds} when the consensus of books implies {fair_am} "
    "(~{edge}% edge). Confirm it's still up before you bet. {stake}",
    "Value on {pick}: {book}'s {odds} beats the market-consensus fair ({fair_am}) by about "
    "{edge}%. Over many such bets that gap is the edge. {stake}",
]

_PROMO_TEMPLATES = [
    "{book} boosted {pick} to {odds}. The fair price is {fair_am}, so the boost hands you "
    "about {edge}% of value the book is subsidizing. {stake}",
    "Odds boost: {book} is paying {odds} on {pick} (fair {fair_am}) - roughly {edge}% in your "
    "favor while the promo lasts. {stake}",
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


def _stake_value(kelly_frac: float, bankroll: float | None) -> str:
    """Stake as % of bankroll (always; NON-NEGOTIABLE #7) plus a concrete amount when the
    user has set a bankroll, so the ticket gives a number to act on, not just a fraction."""
    if kelly_frac <= 0:
        return "-"
    pct = kelly_frac * 100
    if bankroll and bankroll > 0:
        return f"{pct:.1f}% of bankroll (≈ {kelly_frac * bankroll:.0f})"
    return f"{pct:.1f}% of bankroll"


def action_ticket(
    ctx: SignalCopyContext, bankroll: float | None = None, odds_format: str = "american"
) -> dict:
    """The discrete inputs a human copies into their sportsbook, as structured rows - the
    prose in `explain()` says *why*, this says *what to do*. Built from the same context so
    it stays template-only (NON-NEGOTIABLE #1); never implies certainty for a single +EV bet.

    Returns {type, rows|legs, note?}:
      - single (ev/promo): rows = [{label, value}] → Book / Bet / Min odds / Stake.
      - multi  (arb/middle): legs = [{book, pick, odds, stake}] + a plain-language note.
    """
    if ctx.kind in ("arb", "middle"):
        legs = []
        for leg in ctx.legs:
            pick = selection_label(
                ctx.market_type, leg.get("line", ctx.line), leg["selection"], ctx.home, ctx.away
            )
            legs.append(
                {
                    "book": book_label(leg["book"]),
                    "pick": pick,
                    "odds": format_odds(leg["decimal"], odds_format),
                    # The split is the input you can't execute an arb/middle without.
                    "stake": f"{leg['stake_frac'] * 100:.0f}% of total stake",
                }
            )
        if ctx.kind == "arb":
            note = "Place every leg at the prices below to lock the profit regardless of result."
        else:
            win = ", ".join(str(n) for n in (ctx.window or []))
            note = (
                f"Place both legs. You win one side always - and BOTH if the final total "
                f"lands on {win}."
            )
        return {"type": "multi", "legs": legs, "note": note}

    # ev / promo - a single price at one book
    pick = selection_label(ctx.market_type, ctx.line, ctx.selection, ctx.home, ctx.away)
    verb = "Opt into the boost, then bet" if ctx.kind == "promo" else "Bet"
    return {
        "type": "single",
        "rows": [
            {"label": "Book", "value": book_label(ctx.book)},
            {"label": verb, "value": pick},
            # "or better" - this is a floor; below it the edge is gone.
            {
                "label": "Min odds",
                "value": f"{format_odds(ctx.offered_decimal, odds_format)} or better",
            },
            {"label": "Stake", "value": _stake_value(ctx.kelly_frac, bankroll)},
        ],
    }


def explain(ctx: SignalCopyContext, odds_format: str = "american") -> dict:
    """Render a signal into {title, body, footer, fields} from approved templates."""
    if ctx.kind == "middle":
        legs = {leg["selection"]: leg for leg in ctx.legs}
        over, under = legs.get("over", {}), legs.get("under", {})
        win = ", ".join(str(n) for n in (ctx.window or []))
        o_odds = format_odds(over.get("decimal", 2), odds_format)
        u_odds = format_odds(under.get("decimal", 2), odds_format)
        body = (
            f"Middle on {ctx.fixture_label}: back Over {over.get('line')} @ "
            f"{book_label(over.get('book', ''))} {o_odds} and "
            f"Under {under.get('line')} @ {book_label(under.get('book', ''))} "
            f"{u_odds}. If the final total lands on "
            f"{win}, BOTH win (+{ctx.edge_pct:.1f}%) - otherwise it's a small, known cost."
        )
        return {
            "title": f"Middle - {ctx.fixture_label}",
            "body": body,
            "footer": RG_FOOTER,
            "fields": {
                "league": ctx.league_name,
                "fixture": ctx.fixture_label,
                "middle_pct": round(ctx.edge_pct, 2),
                "window": ctx.window,
            },
        }

    if ctx.kind == "arb":
        legs_txt = " · ".join(
            f"{selection_label(ctx.market_type, ctx.line, leg['selection'], ctx.home, ctx.away)} "
            f"@ {book_label(leg['book'])} {format_odds(leg['decimal'], odds_format)} "
            f"(stake {leg['stake_frac'] * 100:.0f}%)"
            for leg in ctx.legs
        )
        body = _variant(_ARB_TEMPLATES, ctx.dedup_hash).format(
            fixture=ctx.fixture_label, profit=f"{ctx.edge_pct:.1f}", legs=legs_txt
        )
        title = f"Arbitrage - {ctx.fixture_label}"
        fields = {
            "league": ctx.league_name,
            "fixture": ctx.fixture_label,
            "profit_pct": round(ctx.edge_pct, 2),
            "legs": legs_txt,
        }
        return {"title": title, "body": body, "footer": RG_FOOTER, "fields": fields}

    # ---- EV / promo (boost) - both are a single-book price vs a fair line ----
    pick = selection_label(ctx.market_type, ctx.line, ctx.selection, ctx.home, ctx.away)
    odds_am = format_odds(ctx.offered_decimal, odds_format)
    fair_am = format_odds(1 / ctx.fair_prob, odds_format) if ctx.fair_prob > 0 else "n/a"
    pool = {"promo": _PROMO_TEMPLATES, "value": _VALUE_TEMPLATES}.get(ctx.kind, _EV_TEMPLATES)
    body = (
        _variant(pool, ctx.dedup_hash)
        .format(
            pick=pick,
            book=book_label(ctx.book),
            odds=odds_am,
            fair_am=fair_am,
            edge=f"{ctx.edge_pct:.1f}",
            stake=_stake_sentence(ctx.kelly_frac),
        )
        .strip()
    )
    title = f"Boost - {pick}" if ctx.kind == "promo" else f"Value Bet - {pick}"
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
