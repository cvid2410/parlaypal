"""Pure-logic tests for the detection core (no I/O — no Postgres/Redis needed).

Guards the arb path against the two ways a non-arb can masquerade as one: a junk/suspended
quote used as a 'best' leg, and an incomplete market (a 3-way h2h missing a selection).
"""
from app.shared.detect_core import find_opportunities

COMMON = dict(is_soft=False, sharp_ref_book="pinnacle", min_edge_pct=2.0,
              kelly_fraction=0.25, edge_bucket_pct=1.0)


def _arbs(by_book, market_type, **over):
    return [o for o in find_opportunities("fx", 1, by_book, market_type=market_type,
                                          **{**COMMON, **over})
            if o.kind == "arb"]


def test_junk_quote_does_not_manufacture_arb():
    # A complete 2-way total at 1.5/1.5 is NOT an arb; a suspend-marker 101.0 on a leg must
    # not become the 'best' price and fake one (NON-NEGOTIABLE #1).
    by_book = {
        "fanduel": {"over": 1.5, "under": 1.5},
        "betmgm":  {"over": 1.5, "under": 101.0},
    }
    assert _arbs(by_book, "total") == []


def test_incomplete_three_way_market_no_arb():
    # h2h is 3-way. With only home+away present (draw missing/suspended), a 2-way 'arb'
    # (1/2.2 + 1/2.1 = 0.93 < 1) is a coin-flip dressed as guaranteed profit — both lose on a
    # draw. Must not fire even though the two present legs would "arb".
    by_book = {
        "fanduel": {"home": 2.2, "away": 2.1},
        "betmgm":  {"home": 2.2, "away": 2.1},
    }
    assert _arbs(by_book, "h2h") == []


def test_junk_quote_falls_back_to_real_best_price():
    # Complete 3-way; a junk price on one book's draw is ignored and the genuine arb fires.
    by_book = {
        "fanduel": {"home": 3.0, "draw": 4.0, "away": 4.0},
        "betmgm":  {"home": 3.0, "draw": 999.0, "away": 4.0},  # junk draw ignored
    }
    arbs = _arbs(by_book, "h2h")
    assert len(arbs) == 1
    assert arbs[0].meta["legs"]["draw"]["odds"] == 4.0


def test_genuine_arb_still_fires():
    by_book = {
        "fanduel": {"home": 3.0, "draw": 4.0, "away": 4.0},  # 1/3+1/4+1/4 = 0.833 < 1
        "betmgm":  {"home": 2.9, "draw": 3.9, "away": 3.9},
    }
    arbs = _arbs(by_book, "h2h")
    assert len(arbs) == 1 and arbs[0].edge_pct > 0


def test_max_offered_odds_is_configurable():
    # With the default cap, a (real but long) 15.0 leg is dropped → market incomplete → no arb.
    by_book = {
        "fanduel": {"over": 1.5, "under": 1.5},
        "betmgm":  {"over": 1.5, "under": 15.0},
    }
    assert _arbs(by_book, "total", max_offered_odds=12.0) == []
    # Raising the cap lets 15.0 back in; 1/1.5 + 1/15.0 = 0.733 < 1 → arb.
    assert len(_arbs(by_book, "total", max_offered_odds=20.0)) == 1
