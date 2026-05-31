"""Certify (or un-certify) a league for user-facing +EV (NON-NEGOTIABLE #2).

Flipping ev_certified is the ONLY thing that lets a league's +EV signals reach users. Do it
only after the backtest CLV gate passes (Wilson lower bound >= threshold over a real sample
— see scripts.clv_report / replay_detect). Also enables ingest so the league is polled live.

Run from backend/:
  python -m scripts.certify_league soccer_sweden_superettan --on
  python -m scripts.certify_league soccer_sweden_superettan --off
"""
import argparse
import asyncio

from sqlalchemy import select

from app.models.core import League
from app.shared.db import get_sessionmaker


async def main() -> None:
    ap = argparse.ArgumentParser(description="Toggle a league's +EV certification.")
    ap.add_argument("sport_key", help="Odds API sport key, e.g. soccer_sweden_superettan")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--on", action="store_true", help="certify (EV reaches users)")
    g.add_argument("--off", action="store_true", help="un-certify (EV internal-only)")
    ap.add_argument("--keep-ingest", action="store_true",
                    help="don't touch ingest_enabled (default: --on also enables ingest)")
    args = ap.parse_args()
    certify = args.on

    async with get_sessionmaker()() as s:
        lg = (await s.execute(
            select(League).where(League.sport_key == args.sport_key)
        )).scalar_one_or_none()
        if lg is None:
            ap.error(f"league '{args.sport_key}' not found")
        if certify and not lg.is_soft:
            ap.error(f"{lg.name} is is_soft=False — +EV doesn't apply to sharp leagues")

        lg.ev_certified = certify
        # Certifying a league it must actually be polled to produce live signals.
        if certify and not args.keep_ingest:
            lg.ingest_enabled = True
        await s.commit()
        print(f"{lg.name}: ev_certified={lg.ev_certified} ingest_enabled={lg.ingest_enabled}")


if __name__ == "__main__":
    asyncio.run(main())
