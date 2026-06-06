"""Public client config — the sportsbook list the settings picker renders.

Served from the auto-synced `books` catalog (see models.core.Book + scheduler/books.py), not a
hardcoded list, so it reflects every book we actually ingest. Only `pickable` books are
offered; affiliate books (promo/url present) sort first. The frontend renders a logo at
`/books/{key}.svg` with a name fallback.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Book
from app.shared.db import get_db

router = APIRouter()


@router.get("/config")
async def get_config(db: AsyncSession = Depends(get_db)):
    rows = (
        (
            await db.execute(
                select(Book)
                .where(Book.pickable.is_(True))
                # affiliate books (have a url) first, then alphabetical by display name
                .order_by(Book.affiliate_url.is_(None), Book.title)
            )
        )
        .scalars()
        .all()
    )
    return {
        "books": [
            {
                "key": b.key,
                "name": b.title,
                "promo": b.affiliate_promo,
                "url": b.affiliate_url,
                "category": b.category,
            }
            for b in rows
        ]
    }
