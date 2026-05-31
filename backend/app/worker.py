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
from app.jobs.notify import send_match_reminders
from app.shared.metrics import emit
from app.workers.detect import detect_market


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


async def startup(ctx: dict) -> None:
    # Kick off the self-perpetuating poll loop once on boot.
    await ctx["redis"].enqueue_job("poll_odds", _job_id="poll_odds")


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [poll_odds, detect_market]
    on_startup = startup
    cron_jobs = [
        cron(send_match_reminders, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]
