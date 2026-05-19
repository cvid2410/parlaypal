import hashlib
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.services.cache import get_redis

router = APIRouter()

SUB_TTL = 60 * 60 * 24 * 30  # 30 days


def _sub_key(endpoint: str) -> str:
    h = hashlib.md5(endpoint.encode()).hexdigest()
    return f"push:sub:{h}"


class SubscribeRequest(BaseModel):
    endpoint: str
    keys: dict  # p256dh, auth


@router.get("/push/vapid-public-key")
async def get_vapid_public_key():
    if not settings.vapid_public_key:
        raise HTTPException(status_code=503, detail="Push not configured")
    return {"public_key": settings.vapid_public_key}


@router.post("/push/subscribe", status_code=204)
async def subscribe(req: SubscribeRequest):
    if not settings.vapid_public_key:
        raise HTTPException(status_code=503, detail="Push not configured")
    redis = await get_redis()
    key = _sub_key(req.endpoint)
    value = json.dumps({"endpoint": req.endpoint, "keys": req.keys})
    await redis.set(key, value, ex=SUB_TTL)


@router.post("/push/unsubscribe", status_code=204)
async def unsubscribe(req: SubscribeRequest):
    redis = await get_redis()
    await redis.delete(_sub_key(req.endpoint))
