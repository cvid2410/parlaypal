"""Books catalog sync — fill `region` (and refresh title/last_seen + apply curated policy)
from The Odds API.

Region is the one book attribute no per-book payload carries — The Odds API only tells you a
book's region by *which region you queried under*. So we query ONE region at a time (the same
`settings.odds_regions` live ingestion uses) and tag each book with the region it appears in.
Cheap: 1 market x 1 region per sport. A couple of active sports surface ~all books; region is
learned once and converges across runs.

Then we upsert each book with its curated overrides (pickable / category / affiliate links)
from app.shared.books — the manual policy layer the API can't provide.
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.models.core import Book, League
from app.shared.books import BOOK_OVERRIDES, override_for
from app.shared.db import get_sessionmaker

log = logging.getLogger("books")

THE_ODDS_BASE = "https://api.the-odds-api.com/v4"


async def _sample_sports(session, limit: int = 3) -> list[str]:
    """A few enabled leagues — enough to surface essentially every book."""
    return list(
        (
            await session.execute(
                select(League.sport_key).where(League.ingest_enabled.is_(True)).limit(limit)
            )
        )
        .scalars()
        .all()
    )


async def sync_books() -> dict:
    if not settings.the_odds_api_key:
        return {"skipped": "no api key"}
    regions = [r.strip() for r in settings.odds_regions.split(",") if r.strip()]
    Session = get_sessionmaker()
    seen: dict[str, dict] = {}  # key -> {title, region}

    async with Session() as session:
        sports = await _sample_sports(session)
        async with httpx.AsyncClient(timeout=20) as client:
            for sport in sports:
                for region in regions:
                    try:
                        resp = await client.get(
                            f"{THE_ODDS_BASE}/sports/{sport}/odds",
                            params={
                                "apiKey": settings.the_odds_api_key,
                                "markets": "h2h",  # 1 market x 1 region = 1 credit
                                "regions": region,
                                "oddsFormat": "decimal",
                            },
                        )
                        resp.raise_for_status()
                    except Exception as exc:
                        log.warning("books sync %s/%s failed: %s", sport, region, exc)
                        continue
                    for event in resp.json():
                        for bm in event.get("bookmakers", []):
                            # first region a book shows up under wins (each key = one region)
                            seen.setdefault(bm["key"], {"title": bm["title"], "region": region})

        for key, meta in seen.items():
            ov = override_for(key)
            row = {
                "title": ov.get("name", meta["title"]),
                "region": meta["region"],
                "pickable": ov.get("pickable", True),
                "category": ov.get("category"),
                "affiliate_promo": ov.get("promo"),
                "affiliate_url": ov.get("url"),
            }
            await session.execute(
                pg_insert(Book)
                .values(key=key, **row)
                .on_conflict_do_update(
                    index_elements=["key"], set_={**row, "last_seen": func.now()}
                )
            )

        # Curated policy applies to ALL override keys, even ones the sample didn't surface
        # this run (e.g. DK/FD/MGM may not appear in a small league's region call) — so
        # affiliate links and the not-pickable denylist are deterministic, not sample-dependent.
        for key, ov in BOOK_OVERRIDES.items():
            vals: dict = {
                "pickable": ov.get("pickable", True),
                "category": ov.get("category"),
                "affiliate_promo": ov.get("promo"),
                "affiliate_url": ov.get("url"),
            }
            if "name" in ov:
                vals["title"] = ov["name"]
            await session.execute(update(Book).where(Book.key == key).values(**vals))
        await session.commit()

    return {"books_seen": len(seen), "regions": len(regions), "sports": len(sports)}
