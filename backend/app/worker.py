"""ARQ worker: the odds poll loop + the detection consumer.

`poll_odds` re-schedules itself every `ingest_poll_seconds` (a fixed job_id means only one
is ever queued), giving a sub-minute poll loop that cron can't. Each pass enqueues one
`detect_market` job per market that moved meaningfully.
"""
from datetime import timedelta

from arq import cron
from arq.connections import RedisSettings

from app.config import settings
from app.ingestors.odds import ingest_once
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
    # Re-arm the loop. Fixed job_id => at most one queued poll at a time.
    await ctx["redis"].enqueue_job(
        "poll_odds",
        _job_id="poll_odds",
        _defer_by=timedelta(seconds=settings.ingest_poll_seconds),
    )
    return stats


async def settle_cron(ctx: dict) -> dict:
    return await settle_once()


async def startup(ctx: dict) -> None:
    # Kick off the self-perpetuating poll loop once on boot.
    await ctx["redis"].enqueue_job("poll_odds", _job_id="poll_odds")


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [poll_odds, detect_market, route_signal, deliver]
    on_startup = startup
    # Settlement runs every 10 min: grades CLV at kickoff, result/P&L once scored.
    # (Legacy WC send_match_reminders cron retired — full WC cleanup tracked separately.)
    cron_jobs = [cron(settle_cron, minute={0, 10, 20, 30, 40, 50})]
