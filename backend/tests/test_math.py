import math

import pytest

from app.shared.math import (
    american_to_decimal,
    decimal_to_american,
    devig_multi,
    ev_pct,
    find_arb,
    find_arb_multi,
    find_middle,
    kelly,
    no_vig_prob,
    shin_devig,
)


def test_american_to_decimal():
    assert american_to_decimal(100) == pytest.approx(2.0)
    assert american_to_decimal(150) == pytest.approx(2.5)
    assert american_to_decimal(-200) == pytest.approx(1.5)
    assert american_to_decimal(-110) == pytest.approx(1.9090909)


def test_decimal_to_american_roundtrip():
    for a in (-250, -110, 100, 135, 547):
        assert decimal_to_american(american_to_decimal(a)) == (f"+{a}" if a > 0 else str(a))


def test_no_vig_prob_symmetric():
    # A perfectly balanced -110/-110 market devigs to 50/50.
    d = american_to_decimal(-110)
    assert no_vig_prob(d, d) == pytest.approx(0.5)


def test_no_vig_prob_favorite():
    # -200 fav vs +170 dog → fav true prob should sit just under the raw 66.7% implied.
    fav, dog = american_to_decimal(-200), american_to_decimal(170)
    p = no_vig_prob(fav, dog)
    assert 0.62 < p < 0.66


def test_ev_pct_positive_when_offered_beats_fair():
    # Fair prob 50%; a +120 (decimal 2.2) offer is clearly +EV.
    assert ev_pct(2.2, 0.5) == pytest.approx(10.0)
    # A -130 (decimal ~1.769) offer at 50% true is -EV.
    assert ev_pct(american_to_decimal(-130), 0.5) < 0


def test_find_arb_detects_gap():
    # +110 / +110 → inverse sum = 0.952 < 1 → arb.
    d = american_to_decimal(110)
    arb = find_arb(d, d)
    assert arb is not None
    assert arb["profit_pct"] == pytest.approx((1 - 2 * (1 / d)) * 100)
    assert arb["stake_a_frac"] == pytest.approx(0.5)
    assert arb["stake_b_frac"] == pytest.approx(0.5)


def test_find_arb_none_when_vig_present():
    # Standard -110/-110 has a hold → no arb.
    d = american_to_decimal(-110)
    assert find_arb(d, d) is None


def test_find_arb_uneven_split():
    a, b = american_to_decimal(150), american_to_decimal(-120)
    arb = find_arb(a, b)
    # -120 side is the favorite → it should carry the larger stake.
    if arb is not None:
        assert arb["stake_b_frac"] > arb["stake_a_frac"]


def test_devig_multi_3way_sums_to_one():
    # A 3-way soccer h2h with a typical hold.
    probs = devig_multi({"home": 1.8, "draw": 3.6, "away": 4.5})
    assert sum(probs.values()) == pytest.approx(1.0)
    # Home is the shortest price → highest fair prob.
    assert probs["home"] > probs["draw"] > probs["away"]


def test_shin_devig_3way_oracle():
    # Independent iterative Shin solve for an asymmetric 1X2 [1.30, 5.50, 11.00]. Shin pulls
    # the longshots down vs multiplicative — matching this (and NOT the multiplicative column)
    # proves the joint n-way z-solve + input convention, not pairwise-plus-renorm.
    p = shin_devig({"home": 1.30, "draw": 5.50, "away": 11.00})
    assert p["home"] == pytest.approx(0.750905, abs=1e-5)
    assert p["draw"] == pytest.approx(0.169398, abs=1e-5)
    assert p["away"] == pytest.approx(0.079697, abs=1e-5)
    assert sum(p.values()) == pytest.approx(1.0, abs=1e-9)
    # Distinct from multiplicative (the failure mode): Shin favorite > multiplicative favorite.
    assert p["home"] > devig_multi({"home": 1.30, "draw": 5.50, "away": 11.00})["home"]


def test_shin_devig_2way_matches_closed_form():
    # At n=2 Shin's normalisation drops to the closed-form regime; agrees with no_vig_prob.
    p = shin_devig({"a": 1.91, "b": 1.91})
    assert p["a"] == pytest.approx(0.5, abs=1e-9)


def test_shin_devig_no_overround_normalises():
    # No overround (implied probs already sum to 1) → no vig to model, just normalise.
    p = shin_devig({"home": 3.0, "draw": 3.0, "away": 3.0})
    assert p["home"] == pytest.approx(1 / 3, abs=1e-9)
    assert sum(p.values()) == pytest.approx(1.0, abs=1e-9)


def test_shin_devig_never_returns_garbage_on_extreme_book():
    # Extreme favourite + large overround: the guard must return either valid probs that sum
    # to 1, or {} (ungradable) — never a bisection-collapsed plausible-but-wrong vector.
    p = shin_devig({"home": 1.02, "draw": 40.0, "away": 40.0})
    assert p == {} or (
        sum(p.values()) == pytest.approx(1.0, abs=1e-9) and all(0 < v < 1 for v in p.values())
    )


def test_devig_multi_matches_2way():
    # For a 2-way market, devig_multi agrees with no_vig_prob.
    a, b = american_to_decimal(-200), american_to_decimal(170)
    probs = devig_multi({"a": a, "b": b})
    assert probs["a"] == pytest.approx(no_vig_prob(a, b))


def test_find_arb_multi_3way():
    # Best price per outcome from different books leaves a gap → arb.
    arb = find_arb_multi({"home": 3.0, "draw": 4.0, "away": 4.0})
    assert arb is not None  # 1/3 + 1/4 + 1/4 = 0.833 < 1
    assert sum(arb["stake_fracs"].values()) == pytest.approx(1.0)
    assert arb["profit_pct"] == pytest.approx((1 - (1 / 3 + 1 / 4 + 1 / 4)) * 100)


def test_find_arb_multi_none_with_hold():
    assert find_arb_multi({"home": 1.8, "draw": 3.6, "away": 4.5}) is None


def test_find_middle_basic():
    # Over 1.5 @ 2.0 and Under 2.5 @ 2.0 → total of 2 wins both. s=1.0 → free middle.
    m = find_middle(2.0, 1.5, 2.0, 2.5)
    assert m is not None
    assert m["window"] == [2]
    assert m["hold"] == pytest.approx(1.0)
    assert m["miss_pnl_pct"] == pytest.approx(0.0)  # break-even on a miss
    assert m["middle_pnl_pct"] == pytest.approx(100.0)  # doubles if it middles


def test_find_middle_wide_window():
    m = find_middle(2.0, 1.5, 2.0, 3.5)
    assert m["window"] == [2, 3]


def test_find_middle_none():
    assert find_middle(2.0, 2.5, 2.0, 1.5) is None  # over line >= under line
    assert find_middle(2.0, 1.5, 2.0, 2.0) is None  # no integer strictly between


def test_kelly_sizing_and_floor():
    # +EV edge → positive fractional stake.
    f = kelly(0.55, 2.0, fraction=0.25)
    assert f == pytest.approx(0.25 * (0.55 * 1 - 0.45) / 1)
    assert f > 0
    # -EV → clamped to zero, never bet.
    assert kelly(0.40, 2.0) == 0.0
    assert not math.isnan(kelly(0.40, 2.0))
