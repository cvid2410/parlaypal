"""Dev helper: run a single ingest pass against the live Odds API, then run detection on
every market that moved. Prints a summary. Not used in production (the worker loop is).

Run from backend/:  python -m scripts.ingest_once
"""

import asyncio

from sqlalchemy import func, select

from app.ingestors.odds import ingest_once
from app.models.odds import OddsSnapshot
from app.models.signals import Signal
from app.shared.db import get_sessionmaker
from app.workers.detect import detect_market


async def main() -> None:
    dirty: list[tuple[str, int]] = []

    async def collect(fixture_id: str, market_id: int) -> None:
        dirty.append((fixture_id, market_id))

    stats = await ingest_once(enqueue=collect)
    print("ingest stats:", stats)
    print("markets that moved:", len(dirty))

    total_ev = total_arb = 0
    for fid, mid in dirty:
        s = await detect_market({}, fid, mid)
        total_ev += s["ev"]
        total_arb += s["arb"]
    print(f"detection produced: ev={total_ev} arb={total_arb}")

    async with get_sessionmaker()() as session:
        snaps = (await session.execute(select(func.count()).select_from(OddsSnapshot))).scalar()
        sigs = (await session.execute(select(func.count()).select_from(Signal))).scalar()
        print(f"db totals: odds_snapshots={snaps} signals={sigs}")


if __name__ == "__main__":
    asyncio.run(main())
