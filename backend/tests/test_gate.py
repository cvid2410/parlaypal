"""Unit tests for the CLV launch gate (NON-NEGOTIABLE #2): it must require statistical
confidence (Wilson lower bound), not just a high point estimate on a thin sample."""
from app.shared.clv import GATE_BEAT_THRESHOLD, LeagueCLV, wilson_lower_bound


def _lg(beats, n):
    return LeagueCLV(league_id=1, league="X", n=n, beats=beats, beat_pct=beats / n)


def test_wilson_lower_bound_basic():
    # Symmetric sanity: lower bound below the point estimate, within [0,1].
    lb = wilson_lower_bound(58, 100)
    assert 0.0 <= lb < 0.58
    # More data ⇒ tighter ⇒ higher lower bound for the same proportion.
    assert wilson_lower_bound(580, 1000) > wilson_lower_bound(58, 100)


def test_high_rate_thin_sample_does_not_pass():
    """21/36 = 58.3% looks like a pass on the point estimate, but the CI floor sits below
    52% — the gate must HOLD it (this is the underpowered-league trap)."""
    lg = _lg(21, 36)
    assert lg.beat_pct > GATE_BEAT_THRESHOLD          # point estimate clears the bar
    assert lg.lower_bound < GATE_BEAT_THRESHOLD        # but the confident floor does not
    assert lg.passes() is False


def test_same_rate_enough_sample_passes():
    """The same ~58% beat-rate on a big sample tightens the floor above 52% ⇒ PASS."""
    lg = _lg(int(0.583 * 600), 600)
    assert lg.lower_bound >= GATE_BEAT_THRESHOLD
    assert lg.passes() is True


def test_min_sample_floor_blocks_tiny_perfect_runs():
    """3/3 = 100% must never certify a league regardless of the CI."""
    assert _lg(3, 3).passes() is False
