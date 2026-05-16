import json
import redis.asyncio as redis
from app.config import settings

_pool: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.from_url(settings.redis_url, decode_responses=True)
    return _pool


async def get_cached(key: str) -> dict | list | None:
    r = get_redis()
    raw = await r.get(key)
    return json.loads(raw) if raw else None


async def set_cached(key: str, value: dict | list, ttl: int) -> None:
    r = get_redis()
    await r.set(key, json.dumps(value), ex=ttl)
