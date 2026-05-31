"""Delivery job (2.5). Idempotent per (signal, user, channel) via `alerts_sent`
(NON-NEGOTIABLE #4): claim-first, so a retried/duplicate job never double-sends.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.signals import Signal
from app.models.users import AlertSent
from app.shared.copy import explain
from app.shared.db import get_sessionmaker
from app.shared.metrics import emit
from app.shared.signal_view import signal_context
from app.workers.channels import get_channel


async def deliver(ctx: dict, signal_id: int, user_id: int, channel: str) -> bool:
    Session = get_sessionmaker()
    async with Session() as session:
        # Claim first: insert the alerts_sent row; a conflict means already delivered.
        claim = (
            pg_insert(AlertSent)
            .values(signal_id=signal_id, user_id=user_id, channel=channel)
            .on_conflict_do_nothing(constraint="pk_alerts_sent")
        )
        res = await session.execute(claim)
        await session.commit()
        if res.rowcount == 0:
            emit("deliver.duplicate", signal_id=signal_id, user_id=user_id, channel=channel)
            return False

        sig = (await session.execute(select(Signal).where(Signal.id == signal_id))).scalar_one_or_none()
        copy_ctx = await signal_context(session, sig) if sig else None

    if copy_ctx is None:
        return False
    ch = get_channel(channel)
    if ch is None:
        emit("deliver.unknown_channel", channel=channel)
        return False
    copy = explain(copy_ctx)
    return await ch.send(user_id, copy)
