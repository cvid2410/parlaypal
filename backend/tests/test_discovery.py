"""Dynamic sport-key discovery: classification (pure) + register/enable/disable (integration)."""

import uuid

import pytest
from sqlalchemy import select

from app.models.core import League
from app.scheduler.discovery import classify, discover_sports, is_soccer_match_sport
from app.shared.db import get_sessionmaker


def test_classify():
    # curated map
    assert classify("soccer_conmebol_copa_libertadores", "Copa Libertadores") == (
        "Copa Libertadores",
        "South America",
        True,
    )
    assert classify("soccer_epl", "EPL") == ("Premier League", "England", False)  # sharp → not soft
    assert classify("soccer_fifa_world_cup", "FIFA World Cup")[2] is False
    # unknown key → fall back to parsing the title
    assert classify("soccer_intl_friendlies", "Friendlies - International") == (
        "Friendlies",
        "International",
        True,
    )
    assert classify("soccer_made_up", "Made Up League") == ("Made Up League", "", True)


def test_is_soccer_match_sport():
    assert is_soccer_match_sport({"group": "Soccer", "key": "soccer_x"}) is True
    assert is_soccer_match_sport({"group": "Soccer", "key": "soccer_x_winner"}) is False  # outright
    assert is_soccer_match_sport({"group": "Basketball", "key": "nba"}) is False


def _sport(key, title="X", active=True):
    return {"key": key, "group": "Soccer", "title": title, "active": active, "has_outrights": False}


async def test_discovery_registers_and_toggles():
    Session = get_sessionmaker()
    tag = uuid.uuid4().hex[:8]
    stale_key = f"soccer_stale_{tag}"  # exists + enabled, but NOT in the active list → disable
    new_key = f"soccer_new_{tag}"  # not in DB, active → register

    async with Session() as s:
        # keep all currently-enabled real leagues "active" in the fake list so we don't touch them
        enabled_keys = (
            (await s.execute(select(League.sport_key).where(League.ingest_enabled.is_(True))))
            .scalars()
            .all()
        )
        s.add(
            League(
                name="Stale", country="X", sport_key=stale_key, is_soft=True, ingest_enabled=True
            )
        )
        await s.commit()

    fake = [_sport(k) for k in enabled_keys] + [_sport(new_key, "New League - Wonderland")]

    try:
        stats = await discover_sports(fetch=lambda: _async(fake), manage_disable=True)
        assert stats["added"] >= 1
        async with Session() as s:
            new_lg = (
                await s.execute(select(League).where(League.sport_key == new_key))
            ).scalar_one()
            assert new_lg.is_soft is True and new_lg.ingest_enabled is True
            assert new_lg.country == "Wonderland"
            stale = (
                await s.execute(select(League).where(League.sport_key == stale_key))
            ).scalar_one()
            assert stale.ingest_enabled is False  # dormant → disabled
    finally:
        async with Session() as s:
            from sqlalchemy import delete

            await s.execute(delete(League).where(League.sport_key.in_([stale_key, new_key])))
            await s.commit()


async def _async(value):
    return value
