"""Line-shopping / odds board.

For any fixture we're tracking, show the best available price per market+selection across
books (and the full per-book breakdown). No edge claim — just "where's the best number" —
so it works on every league, including big-5 + the World Cup where there's no signal.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.auth import get_current_user
from app.models.core import Fixture, League, Market, Team
from app.models.users import User
from app.services.af import league_fixtures as af_league_fixtures
from app.services.af import status_of
from app.services.cache import get_redis
from app.shared.copy import book_label, selection_label
from app.shared.db import get_db
from app.shared.math import decimal_to_american
from app.shared.normalize import norm_team

router = APIRouter(tags=["lines"])


@router.get("/lines/{fixture_id}")
async def lines(
    fixture_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    fx = await db.get(Fixture, fixture_id)
    if fx is None:
        raise HTTPException(status_code=404, detail="Fixture not found")
    league = await db.get(League, fx.league_id)
    home = await db.get(Team, fx.home_id)
    away = await db.get(Team, fx.away_id)

    r = get_redis()
    keys = [k async for k in r.scan_iter(match=f"odds:{fixture_id}:*")]
    mids = [int(k.rsplit(":", 1)[-1]) for k in keys]
    markets = (
        {
            m.id: m
            for m in (await db.execute(select(Market).where(Market.id.in_(mids)))).scalars().all()
        }
        if mids
        else {}
    )

    out = []
    for k in keys:
        mid = int(k.rsplit(":", 1)[-1])
        m = markets.get(mid)
        if m is None:
            continue
        by_sel: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for field, val in (await r.hgetall(k)).items():
            book, _, sel = field.partition(":")
            by_sel[sel].append((book, float(val)))
        selections = []
        for sel, books in by_sel.items():
            books.sort(key=lambda x: -x[1])
            best_book, best_dec = books[0]
            selections.append(
                {
                    "selection": sel,
                    "label": selection_label(m.type, m.line, sel, home.name, away.name),
                    "best_book": book_label(best_book),
                    "best_odds": decimal_to_american(best_dec),
                    "books": [
                        {"book": book_label(b), "odds": decimal_to_american(d)} for b, d in books
                    ],
                }
            )
        out.append({"market_id": mid, "type": m.type, "line": m.line, "selections": selections})

    # h2h first, then totals by line
    out.sort(key=lambda x: (x["type"] != "h2h", x["line"] if x["line"] is not None else 0))
    return {
        "fixture_id": fixture_id,
        "league": league.name,
        "country": league.country,
        "home": home.name,
        "away": away.name,
        "home_logo": home.logo,
        "away_logo": away.logo,
        "kickoff": fx.kickoff_utc.isoformat(),
        "markets": out,
    }


@router.get("/leagues/{league_id}/fixtures")
async def league_fixtures(
    league_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Upcoming fixtures for a league (browse → odds board). Lets users line-shop big
    leagues / WC where we generate no signals."""
    now = datetime.now(UTC)
    rows = (
        await db.execute(
            select(Fixture, Team.name, Team.logo)
            .join(Team, Team.id == Fixture.home_id)
            .where(Fixture.league_id == league_id, Fixture.kickoff_utc >= now)
            .order_by(Fixture.kickoff_utc)
            .limit(40)
        )
    ).all()
    # second pass for away names/logos
    fixtures = []
    for fx, home_name, home_logo in rows:
        away = await db.get(Team, fx.away_id)
        fixtures.append(
            {
                "id": fx.id,
                "home": home_name,
                "home_logo": home_logo,
                "away": away.name,
                "away_logo": away.logo,
                "kickoff": fx.kickoff_utc.isoformat(),
            }
        )
    return {"count": len(fixtures), "fixtures": fixtures}


@router.get("/leagues/{league_id}/schedule")
async def league_schedule(
    league_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """The league's full upcoming schedule from API-Football (every team, whether or not we
    price it). Each row carries AF team ids (→ team pages) and, where we can match it to one
    of our priceable fixtures by normalized team names + day, our fixture id (→ odds board)."""
    lg = (await db.execute(select(League).where(League.id == league_id))).scalar_one_or_none()
    if lg is None:
        raise HTTPException(status_code=404, detail="League not found")
    if lg.af_league_id is None:
        return {"available": False, "fixtures": []}

    af_fx = await af_league_fixtures(lg.af_league_id)

    # Index our upcoming, priceable fixtures by (norm home, norm away, UTC day) for the badge.
    home_t, away_t = aliased(Team), aliased(Team)
    rows = (
        await db.execute(
            select(Fixture.id, home_t.name, away_t.name, Fixture.kickoff_utc)
            .join(home_t, home_t.id == Fixture.home_id)
            .join(away_t, away_t.id == Fixture.away_id)
            .where(Fixture.league_id == league_id, Fixture.kickoff_utc >= datetime.now(UTC))
        )
    ).all()
    priceable = {
        (norm_team(h), norm_team(a), ko.astimezone(UTC).date().isoformat()): fid
        for fid, h, a, ko in rows
    }

    out = []
    for f in af_fx:
        home, away = f["teams"]["home"], f["teams"]["away"]
        ko = f["fixture"]["date"]
        match_key = (norm_team(home["name"]), norm_team(away["name"]), ko[:10])
        out.append(
            {
                "home": home["name"],
                "home_logo": home.get("logo"),
                "home_af_id": home.get("id"),
                "away": away["name"],
                "away_logo": away.get("logo"),
                "away_af_id": away.get("id"),
                "kickoff": ko,
                "status": status_of(f["fixture"]["status"]["short"]),
                # our fixture id when we can price this game, else None (informational only)
                "fixture_id": priceable.get(match_key),
            }
        )
    return {"available": bool(out), "fixtures": out}
