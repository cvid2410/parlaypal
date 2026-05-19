import json
import asyncio
from datetime import datetime, timezone, timedelta
from arq import ArqRedis
from pywebpush import webpush, WebPushException
from app.config import settings
from app.services.cache import get_redis
from app.services.api_football import fetch_matches


async def send_match_reminders(ctx: dict):
    if not settings.vapid_private_key:
        return

    redis: ArqRedis = ctx["redis"]
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(minutes=25)
    window_end = now + timedelta(minutes=35)

    matches = await fetch_matches()
    upcoming = [
        m for m in matches
        if m["status"] == "scheduled"
        and window_start <= datetime.fromisoformat(m["date"]) <= window_end
    ]

    if not upcoming:
        return

    # Collect all subscriptions
    app_redis = await get_redis()
    keys = [k async for k in app_redis.scan_iter("push:sub:*")]
    if not keys:
        return

    subs_raw = await app_redis.mget(*keys)
    subs = [json.loads(s) for s in subs_raw if s]

    for match in upcoming:
        sent_key = f"push:sent:{match['id']}"
        if await app_redis.exists(sent_key):
            continue

        payload = json.dumps({
            "title": "⚽ Match Starting Soon",
            "body": f"{match['home_team']} vs {match['away_team']} kicks off in ~30 minutes",
            "icon": "/favicon.ico",
        })

        await asyncio.gather(*[_send(sub, payload) for sub in subs], return_exceptions=True)
        await app_redis.set(sent_key, "1", ex=7200)


async def _send(sub: dict, payload: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _send_sync, sub, payload)


def _send_sync(sub: dict, payload: str):
    try:
        webpush(
            subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]},
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": f"mailto:{settings.vapid_claim_email}"},
        )
    except WebPushException:
        pass
