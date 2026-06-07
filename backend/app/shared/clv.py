"""CLV reporting + the launch gate (3.3, NON-NEGOTIABLE #2).

A league must demonstrably beat the closing line on graded signals before it's served to
users. This computes beat-CLV% per league and a pass/fail against a threshold + minimum
sample size.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy import Integer, cast, func, select

from app.models.core import Fixture, League
from app.models.signals import Signal, SignalGrade

# A league must beat closing on a meaningful sample - AND we must be statistically confident
# the *true* beat-rate clears the bar, not just the point estimate. A high observed beat-rate
# on few signals (e.g. 21/36 = 58%) has a wide confidence interval that can sit below 52%;
# certifying on the point estimate would greenlight underpowered leagues and users would bet
# real money on noise (NON-NEGOTIABLE #2). So the gate requires the lower confidence bound.
GATE_MIN_SAMPLE = 20
GATE_BEAT_THRESHOLD = 0.52
# One-sided 95% (z=1.6449): passing ⇔ we reject H0 "true beat-rate ≤ 52%" at α=0.05.
GATE_CONFIDENCE_Z = 1.6449


def wilson_lower_bound(beats: int, n: int, z: float = GATE_CONFIDENCE_Z) -> float:
    """Lower bound of the Wilson score interval for a binomial proportion. Preferred over the
    normal (Wald) approximation: it stays in [0,1] and is accurate at small n / extreme p."""
    if n <= 0:
        return 0.0
    phat = beats / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (phat + z2 / (2 * n)) / denom
    margin = z * math.sqrt((phat * (1 - phat) + z2 / (4 * n)) / n) / denom
    return max(0.0, center - margin)


@dataclass
class LeagueCLV:
    league_id: int
    league: str
    n: int  # graded signals with a CLV verdict
    beats: int  # how many beat closing
    beat_pct: float

    @property
    def lower_bound(self) -> float:
        """Confident floor on the true beat-rate (Wilson). This is what the gate tests."""
        return wilson_lower_bound(self.beats, self.n)

    def passes(
        self, min_sample: int = GATE_MIN_SAMPLE, threshold: float = GATE_BEAT_THRESHOLD
    ) -> bool:
        return self.n >= min_sample and self.lower_bound >= threshold


async def clv_report_by_league(session) -> list[LeagueCLV]:
    rows = (
        await session.execute(
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
        )
    ).all()
    out = []
    for lid, name, n, beats in rows:
        out.append(
            LeagueCLV(
                league_id=lid,
                league=name,
                n=int(n),
                beats=int(beats),
                beat_pct=(int(beats) / int(n)) if n else 0.0,
            )
        )
    return out
