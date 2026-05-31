"""CLV reporting + the launch gate (3.3, NON-NEGOTIABLE #2).

A league must demonstrably beat the closing line on graded signals before it's served to
users. This computes beat-CLV% per league and a pass/fail against a threshold + minimum
sample size.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Integer, cast, func, select

from app.models.core import Fixture, League
from app.models.signals import Signal, SignalGrade

# Defaults: a league must beat closing on a majority of a meaningful sample.
GATE_MIN_SAMPLE = 20
GATE_BEAT_THRESHOLD = 0.52


@dataclass
class LeagueCLV:
    league_id: int
    league: str
    n: int          # graded signals with a CLV verdict
    beats: int      # how many beat closing
    beat_pct: float

    def passes(self, min_sample: int = GATE_MIN_SAMPLE,
              threshold: float = GATE_BEAT_THRESHOLD) -> bool:
        return self.n >= min_sample and self.beat_pct >= threshold


async def clv_report_by_league(session) -> list[LeagueCLV]:
    rows = (await session.execute(
        select(
            League.id,
            League.name,
            func.count().label("n"),
            func.coalesce(func.sum(cast(SignalGrade.beat_clv, Integer)), 0).label("beats"),
        )
        .select_from(SignalGrade)
        .join(Signal, SignalGrade.signal_id == Signal.id)
        .join(Fixture, Signal.fixture_id == Fixture.id)
        .join(League, Fixture.league_id == League.id)
        .where(SignalGrade.beat_clv.isnot(None))
        .group_by(League.id, League.name)
        .order_by(League.name)
    )).all()
    out = []
    for lid, name, n, beats in rows:
        out.append(LeagueCLV(league_id=lid, league=name, n=int(n), beats=int(beats),
                             beat_pct=(int(beats) / int(n)) if n else 0.0))
    return out
