"""Fan-out stub.

Phase 2.4 turns this into the real routing index (Redis sets per league/book →
intersect → filter by min_edge → enqueue delivery, NON-NEGOTIABLE #5). For the detection
spine it just records that a signal was accepted, so the end-to-end path is observable.
"""
from __future__ import annotations

import logging

from app.shared.metrics import emit

log = logging.getLogger("fanout")


async def handoff(signal_id: int, kind: str, edge_pct: float) -> None:
    emit("signal.accepted", signal_id=signal_id, kind=kind, edge_pct=round(edge_pct, 3))
    log.info("signal %s (%s, edge=%.2f%%) handed to fanout stub", signal_id, kind, edge_pct)
