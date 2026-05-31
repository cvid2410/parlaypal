"""Fan-out / routing (2.4, NON-NEGOTIABLE #5).

For an accepted signal: find eligible users via the precomputed routing index (no full-table
scan), filter by each user's min_edge, gate by tier (free → delayed delivery, paid → live),
and enqueue one idempotent `deliver` job per (signal, user, channel).
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.config import settings
from app.models.core import Fixture
from app.models.signals import Signal
from app.services.cache import get_redis
from app.shared.metrics import emit
from app.shared.routing import PAID_TIERS, eligible_users, user_route_meta
from app.shared.db import get_sessionmaker


async def route_signal(ctx: dict, signal_id: int) -> dict:
    r = get_redis()
    arq = ctx.get("redis") if isinstance(ctx, dict) else None
    Session = get_sessionmaker()

    async with Session() as session:
        sig = (
            await session.execute(select(Signal).where(Signal.id == signal_id))
        ).scalar_one_or_none()
        if sig is None:
            return {"eligible": 0, "enqueued": 0}
        league_id = (
            await session.execute(
                select(Fixture.league_id).where(Fixture.id == sig.fixture_id)
            )
        ).scalar_one()

    users = await eligible_users(r, league_id, sig.book, sig.kind)
    enqueued = 0
    for uid in users:
        meta = await user_route_meta(r, uid)
        if meta is None or sig.edge_pct < meta["min_edge"]:
            continue
        defer = 0 if meta["tier"] in PAID_TIERS else settings.free_delay_seconds
        for channel in meta["channels"]:
            if arq is not None:
                await arq.enqueue_job(
                    "deliver", signal_id, uid, channel,
                    _job_id=f"deliver:{signal_id}:{uid}:{channel}",
                    _defer_by=timedelta(seconds=defer),
                )
            enqueued += 1

    emit("fanout.routed", signal_id=signal_id, kind=sig.kind,
         eligible=len(users), enqueued=enqueued)
    return {"eligible": len(users), "enqueued": enqueued}
