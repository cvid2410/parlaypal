from arq import cron
from arq.connections import RedisSettings
from app.config import settings
from app.jobs.notify import send_match_reminders


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    cron_jobs = [
        cron(send_match_reminders, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]
