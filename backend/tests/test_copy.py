import hashlib
import re

import pytest

from app.shared.copy import (
    BANNED_EV_PHRASES,
    RG_FOOTER,
    SignalCopyContext,
    explain,
)


def _hash(seed: str) -> str:
    return hashlib.sha1(seed.encode()).hexdigest()


def _ev_ctx(seed: str, edge: float = 9.1) -> SignalCopyContext:
    return SignalCopyContext(
        kind="ev",
        dedup_hash=_hash(seed),
        league_name="Liga MX",
        home="Tigres UANL",
        away="Atlas",
        market_type="h2h",
        line=None,
        selection="home",
        book="fanduel",
        offered_decimal=2.35,
        fair_prob=0.5,
        edge_pct=edge,
        kelly_frac=0.031,
    )


def _contains(body: str, phrase: str) -> bool:
    if " " in phrase or "%" in phrase or "-" in phrase:
        return phrase.lower() in body.lower()
    return re.search(rf"\b{re.escape(phrase)}\b", body, re.IGNORECASE) is not None


@pytest.mark.parametrize("i", range(40))
def test_ev_copy_never_implies_certainty(i):
    """Across every variant + a spread of edges, EV copy carries no certainty language."""
    ctx = _ev_ctx(f"seed-{i}", edge=2.0 + i)
    out = explain(ctx)
    full = out["title"] + " " + out["body"]
    for phrase in BANNED_EV_PHRASES:
        assert not _contains(full, phrase), f"banned phrase {phrase!r} in EV copy: {full!r}"


def test_ev_copy_renders_computed_values():
    out = explain(_ev_ctx("vals", edge=9.1))
    assert "Tigres UANL to win" in out["body"]
    assert "FanDuel" in out["body"]
    assert "9.1%" in out["body"]
    assert "+135" in out["body"]  # 2.35 decimal -> +135
    assert out["footer"] == RG_FOOTER
    assert out["fields"]["edge_pct"] == 9.1


def test_copy_is_deterministic():
    a = explain(_ev_ctx("same"))
    b = explain(_ev_ctx("same"))
    assert a["body"] == b["body"]


def test_different_hash_can_pick_different_variant():
    bodies = {explain(_ev_ctx(f"v{i}"))["body"] for i in range(20)}
    assert len(bodies) > 1  # variants actually rotate


def test_arb_copy_may_say_guaranteed_and_lists_legs():
    ctx = SignalCopyContext(
        kind="arb",
        dedup_hash=_hash("arb1"),
        league_name="Série A",
        home="Flamengo",
        away="Palmeiras",
        market_type="h2h",
        line=None,
        selection="home+away+draw",
        edge_pct=3.2,
        legs=[
            {"selection": "home", "book": "draftkings", "decimal": 2.18, "stake_frac": 0.46},
            {"selection": "away", "book": "betmgm", "decimal": 2.05, "stake_frac": 0.54},
        ],
    )
    out = explain(ctx)
    assert "guaranteed" in out["body"].lower() or "locked-in" in out["body"].lower()
    assert "DraftKings" in out["body"] and "BetMGM" in out["body"]
    assert "3.2%" in out["body"]
    assert out["footer"] == RG_FOOTER


def test_totals_selection_label():
    ctx = _ev_ctx("tot")
    ctx.market_type = "total"
    ctx.line = 2.5
    ctx.selection = "over"
    out = explain(ctx)
    assert "Over 2.5 goals" in out["body"]
