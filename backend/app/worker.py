"""ARQ worker: the odds poll loop + the detection/delivery/settlement jobs.

The poll runs as a cron at the base tick (`poll_tick_seconds`) — cron is restart-safe and
won't collide on a job id the way a self-rescheduling loop does. Each tick fetches only the
leagues whose tier is due (kickoff-aware, see ingestors/odds.py) and enqueues one
`detect_market` job per market that moved meaningfully.
"""
from arq import cron
from arq.connections import RedisSettings

from app.config import settings
from app.ingestors.odds import ingest_once
from app.scheduler.logos import resolve_team_logos
from app.scheduler.results import resolve_results
from app.scheduler.settle import settle_once
from app.shared.metrics import emit
from app.workers.deliver import deliver
from app.workers.detect import detect_market
from app.workers.fanout import route_signal


async def poll_odds(ctx: dict) -> dict:
    async def _enqueue(fixture_id: str, market_id: int) -> None:
        await ctx["redis"].enqueue_job("detect_market", fixture_id, market_id)

    stats = await ingest_once(enqueue=_enqueue)
    emit("ingest.pass", **stats)
    return stats


async def settle_cron(ctx: dict) -> dict:
    # Backfill crests, pull final scores, then grade (CLV always; result/P&L once scored).
    await resolve_team_logos()
    await resolve_results()
    return await settle_once()


def _tick_seconds() -> set[int]:
    """Cron `second` set for the base tick. Tick should divide 60 (15/20/30); otherwise
    fall back to every 30s."""
    t = settings.poll_tick_seconds
    return set(range(0, 60, t)) if t and 60 % t == 0 else {0, 30}


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [detect_market, route_signal, deliver]
    cron_jobs = [
        # Kickoff-aware odds poll at the base tick (run immediately on boot).
        cron(poll_odds, second=_tick_seconds(), run_at_startup=True),
        # Settlement every 10 min: grade CLV at kickoff, result/P&L once scored.
        cron(settle_cron, minute={0, 10, 20, 30, 40, 50}),
    ]
