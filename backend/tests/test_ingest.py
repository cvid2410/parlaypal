import uuid

from app.ingestors.odds import _queue_review, canonical
from app.services.cache import get_redis


def test_canonical_h2h_and_totals():
    assert canonical("h2h", {"name": "Tigres"}, "Tigres", "Atlas") == ("h2h", None, "home")
    assert canonical("h2h", {"name": "Atlas"}, "Tigres", "Atlas") == ("h2h", None, "away")
    assert canonical("h2h", {"name": "Draw"}, "Tigres", "Atlas") == ("h2h", None, "draw")
    assert canonical("totals", {"name": "Over", "point": 2.5}, "T", "A") == ("total", 2.5, "over")
    assert canonical("totals", {"name": "Under", "point": 2.5}, "T", "A") == ("total", 2.5, "under")


def test_canonical_unknown_market_is_none():
    assert canonical("spreads", {"name": "Tigres -1.5"}, "Tigres", "Atlas") is None
    assert canonical("totals", {"name": "Yes"}, "T", "A") is None  # not over/under


async def test_queue_review_dedup():
    r = get_redis()
    raw_market = f"spreads_{uuid.uuid4().hex[:8]}"
    outcome = {"name": "Tigres -1.5", "point": -1.5}
    try:
        first = await _queue_review(r, "draftkings", raw_market, outcome, "fx1")
        assert first is not None
        assert first.reason == "unknown_market"
        assert first.context["market_key"] == raw_market
        # Same raw shape again within TTL → deduped.
        second = await _queue_review(r, "draftkings", raw_market, outcome, "fx1")
        assert second is None
    finally:
        await r.delete(f"reviewed:{raw_market}:Tigres -1.5")
