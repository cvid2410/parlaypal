"""Backfill final scores for backtested fixtures so P&L can be graded (analysis tool).

The live resolver (scheduler.results) matches AF results by *exact* normalized team name,
which misses cross-feed name gaps ("Guadalajara" vs AF "Guadalajara Chivas"). For the
offline P&L study we can afford a more lenient match: scope candidates to the fixture's own
league (af_league_id) and day — only a handful of games — then match each side by token
SUBSET (our shorter name ⊆ AF's fuller name, or vice versa), requiring BOTH sides to align
on the same AF fixture. That pair constraint makes the looser match safe.

Reuses the cached fixtures_by_date (so re-running costs no API calls). After this, run
settle / scripts.replay_detect --settle to grade result + P&L from the new scores.

Run from backend/:  python -m scripts.backfill_results
"""

import asyncio
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.models.core import Fixture, League, Team
from app.models.signals import Signal
from app.services.af import FINISHED, fixtures_by_date
from app.shared.db import get_sessionmaker
from app.shared.normalize import norm_team


def _toks(name: str) -> set[str]:
    return set(norm_team(name).split())


def _side_match(ours: str, theirs: str) -> bool:
    """Our (often shorter) name's tokens are a subset of AF's, or vice versa."""
    o, t = _toks(ours), _toks(theirs)
    return bool(o) and bool(t) and (o <= t or t <= o)


async def main() -> None:
    Session = get_sessionmaker()
    home_t, away_t = aliased(Team), aliased(Team)
    async with Session() as session:
        rows = (
            await session.execute(
                select(Fixture, League.af_league_id, home_t.name, away_t.name)
                .join(League, League.id == Fixture.league_id)
                .join(home_t, home_t.id == Fixture.home_id)
                .join(away_t, away_t.id == Fixture.away_id)
                .where(
                    League.is_soft,
                    League.af_league_id.isnot(None),
                    Fixture.home_score.is_(None),
                    Fixture.id.in_(select(Signal.fixture_id)),  # only fixtures we graded
                )
            )
        ).all()

        # Group candidates by UTC day so each cached AF date is read once.
        by_date: dict[str, list] = defaultdict(list)
        for fx, af_lid, home, away in rows:
            by_date[fx.kickoff_utc.strftime("%Y-%m-%d")].append((fx, af_lid, home, away))

        matched = unmatched = 0
        for d, cands in sorted(by_date.items()):
            # AF finished results for the day, grouped by league id.
            by_league: dict[int, list] = defaultdict(list)
            for f in await fixtures_by_date(d):
                if f["fixture"]["status"]["short"] not in FINISHED:
                    continue
                g = f.get("goals", {})
                if g.get("home") is None or g.get("away") is None:
                    continue
                by_league[f["league"]["id"]].append(
                    (f["teams"]["home"]["name"], f["teams"]["away"]["name"], (g["home"], g["away"]))
                )
            for fx, af_lid, home, away in cands:
                hit = next(
                    (
                        sc
                        for afh, afa, sc in by_league.get(af_lid, [])
                        if _side_match(home, afh) and _side_match(away, afa)
                    ),
                    None,
                )
                if hit is None:
                    unmatched += 1
                    continue
                fx.home_score, fx.away_score = int(hit[0]), int(hit[1])
                matched += 1
        await session.commit()
        print(
            f"dates={len(by_date)} candidates={matched + unmatched} "
            f"matched={matched} unmatched={unmatched}"
        )


if __name__ == "__main__":
    asyncio.run(main())
