"""Seed a batch of settled, graded signals so the Results tab renders with real shape.
Idempotent: wipes any prior demo-results data first. Dev/demo only.

Run from backend/:  python -m scripts.seed_demo_results        (seed)
                    python -m scripts.seed_demo_results clean   (remove)
"""
import asyncio
import datetime as dt
import sys

from sqlalchemy import delete, select

from app.ingestors.odds import _get_market_id
from app.models.core import Fixture, League, Team
from app.models.signals import Signal, SignalGrade

from app.shared.db import get_sessionmaker

SPORT_KEY = "demo_results"

# (selection, offered, beat_clv, result, pnl_units) — an upward, honest mix (8W/4L).
SPECS = [
    ("home", 2.10, True, "win", 1.10), ("over", 1.95, True, "win", 0.95),
    ("away", 1.90, False, "loss", -1.0), ("home", 2.30, True, "win", 1.30),
    ("draw", 3.20, True, "win", 2.20), ("under", 1.85, False, "loss", -1.0),
    ("home", 2.05, True, "win", 1.05), ("away", 2.40, False, "loss", -1.0),
    ("over", 2.00, True, "win", 1.00), ("home", 1.95, True, "win", 0.95),
    ("draw", 3.10, False, "loss", -1.0), ("away", 2.20, True, "win", 1.20),
]


async def _wipe(session) -> None:
    lg = (await session.execute(select(League).where(League.sport_key == SPORT_KEY))).scalar_one_or_none()
    if lg is None:
        return
    fids = (await session.execute(select(Fixture.id).where(Fixture.league_id == lg.id))).scalars().all()
    sids = (await session.execute(select(Signal.id).where(Signal.fixture_id.in_(fids)))).scalars().all()
    if sids:
        await session.execute(delete(SignalGrade).where(SignalGrade.signal_id.in_(sids)))
        await session.execute(delete(Signal).where(Signal.id.in_(sids)))
    await session.execute(delete(Fixture).where(Fixture.league_id == lg.id))
    await session.execute(delete(Team).where(Team.league_id == lg.id))
    await session.execute(delete(League).where(League.id == lg.id))


async def main(clean: bool) -> None:
    Session = get_sessionmaker()
    async with Session() as s:
        await _wipe(s)
        await s.commit()
        if clean:
            print("demo results removed")
            return
        lg = League(name="Liga MX", country="Mexico", sport_key=SPORT_KEY,
                    is_soft=True, ingest_enabled=False)
        s.add(lg)
        await s.flush()
        h = Team(league_id=lg.id, name="Tigres UANL")
        a = Team(league_id=lg.id, name="Atlas")
        s.add_all([h, a])
        await s.flush()
        now = dt.datetime.now(dt.timezone.utc)
        for i, (sel, odds, beat, result, pnl) in enumerate(SPECS):
            fid = f"demo_res_{i}"
            mtype = "total" if sel in ("over", "under") else "h2h"
            line = 2.5 if mtype == "total" else None
            s.add(Fixture(id=fid, league_id=lg.id, home_id=h.id, away_id=a.id,
                          kickoff_utc=now - dt.timedelta(hours=(len(SPECS) - i) * 6),
                          home_score=2, away_score=1))
            mid = await _get_market_id(s, mtype, line)
            sig = Signal(fixture_id=fid, market_id=mid, selection=sel, book="fanduel",
                         kind="ev", offered_odds=odds, fair_prob=0.5, edge_pct=5.0,
                         kelly_frac=0.02, ttl_sec=1800, dedup_hash=f"demo_{i}",
                         status="settled", created_at=now - dt.timedelta(hours=(len(SPECS) - i) * 6))
            s.add(sig)
            await s.flush()
            s.add(SignalGrade(signal_id=sig.id, closing_odds=odds - 0.1, beat_clv=beat,
                              result=result, pnl_units=pnl))
        await s.commit()
        print(f"seeded {len(SPECS)} settled signals under demo league '{lg.name}'")


if __name__ == "__main__":
    asyncio.run(main(len(sys.argv) > 1 and sys.argv[1] == "clean"))
