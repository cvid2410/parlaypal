"""Shared API-Football client. One cached call per date powers both the results resolver
and the Scores tab (no duplicate API spend)."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.config import settings
from app.services.cache import get_cached, set_cached

AF_BASE = "https://v3.football.api-sports.io"
FINISHED = {"FT", "AET", "PEN", "AWD", "WO"}
LIVE = {"1H", "2H", "HT", "ET", "BT", "P", "LIVE", "INT", "SUSP"}


async def fixtures_by_date(date_str: str) -> list[dict]:
    """Raw API-Football fixtures for a UTC date. Cached: today briefly, past dates long."""
    key = f"afraw:{date_str}"
    cached = await get_cached(key)
    if cached is not None:
        return cached
    if not settings.api_football_key:
        return []
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{AF_BASE}/fixtures",
            headers={"x-apisports-key": settings.api_football_key},
            params={"date": date_str, "timezone": "UTC"},
        )
        resp.raise_for_status()
        raw = resp.json().get("response", [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await set_cached(key, raw, ttl=120 if date_str == today else 86400)
    return raw


def status_of(short: str) -> str:
    if short in FINISHED:
        return "finished"
    if short in LIVE:
        return "live"
    return "scheduled"
