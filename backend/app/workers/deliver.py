"""Delivery job (2.5). Idempotent per (signal, user, channel) via `alerts_sent`
(NON-NEGOTIABLE #4): claim-first, so a retried/duplicate job never double-sends.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.signals import Signal
from app.models.users import AlertSent
from app.shared.copy import explain
from app.shared.db import get_sessionmaker
from app.shared.metrics import emit
from app.shared.signal_view import signal_context
from app.workers.channels import get_channel


async def _release_claim(Session, signal_id: int, user_id: int, channel: str) -> None:
    """Undo the alerts_sent claim so a retry can re-attempt delivery. Keeps the table's
    invariant honest: a row means the alert was actually delivered, not merely attempted."""
    async with Session() as session:
        await session.execute(
            delete(AlertSent).where(
                AlertSent.signal_id == signal_id,
                AlertSent.user_id == user_id,
                AlertSent.channel == channel,
            )
        )
        await session.commit()


async def deliver(ctx: dict, signal_id: int, user_id: int, channel: str) -> bool:
    Session = get_sessionmaker()
    async with Session() as session:
        # Claim first: insert the alerts_sent row; a conflict means already delivered. This is
        # what prevents a double-send (NON-NEGOTIABLE #4) - a retry only re-sends after a
        # definitively failed attempt has released the claim below.
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

        sig = (
            await session.execute(select(Signal).where(Signal.id == signal_id))
        ).scalar_one_or_none()
        copy_ctx = await signal_context(session, sig) if sig else None

    # Orphaned signal / unknown channel: nothing is deliverable and a retry won't help, so the
    # claim stays (we don't reprocess forever). Genuine send failures DO release the claim.
    if copy_ctx is None:
        return False
    ch = get_channel(channel)
    if ch is None:
        emit("deliver.unknown_channel", channel=channel)
        return False

    copy = explain(copy_ctx)
    try:
        sent = await ch.send(user_id, copy)
    except Exception:
        # Transient failure (e.g. webhook 5xx/429 raised by raise_for_status): release the
        # claim and re-raise so the ARQ retry re-attempts instead of silently dropping it.
        await _release_claim(Session, signal_id, user_id, channel)
        raise
    if not sent:
        await _release_claim(Session, signal_id, user_id, channel)
    return sent
