import pytest

from app.shared.grading import clv_beat, compute_result, pnl_units


def test_clv_beat():
    assert clv_beat(2.35, 2.20) is True  # we got longer odds than close → beat
    assert clv_beat(1.80, 2.00) is False  # close was longer → we didn't beat
    assert clv_beat(2.35, None) is None  # no closing reference
    assert clv_beat(2.35, 1.0) is None


def test_compute_result_h2h():
    assert compute_result(2, 1, "h2h", None, "home") == "win"
    assert compute_result(2, 1, "h2h", None, "away") == "loss"
    assert compute_result(2, 1, "h2h", None, "draw") == "loss"
    assert compute_result(1, 1, "h2h", None, "draw") == "win"
    assert compute_result(0, 3, "h2h", None, "away") == "win"


def test_compute_result_totals():
    assert compute_result(2, 1, "total", 2.5, "over") == "win"  # 3 > 2.5
    assert compute_result(2, 1, "total", 2.5, "under") == "loss"
    assert compute_result(1, 0, "total", 2.5, "under") == "win"  # 1 < 2.5
    assert compute_result(2, 1, "total", 3.0, "over") == "push"  # 3 == 3
    assert compute_result(2, 1, "total", 3.0, "under") == "push"


def test_pnl_units():
    assert pnl_units("win", 2.35) == pytest.approx(1.35)
    assert pnl_units("loss", 2.35) == -1.0
    assert pnl_units("push", 2.35) == 0.0
    assert pnl_units(None, 2.35) is None
