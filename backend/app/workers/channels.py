"""Delivery channels. v1: a local LogChannel (always on, for verification) and an optional
Discord webhook. SES email and per-user Twilio/web-push come later.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.shared.metrics import emit

log = logging.getLogger("deliver")


class LogChannel:
    name = "log"

    async def send(self, to: int, copy: dict) -> bool:
        log.info("[deliver:log] user=%s | %s — %s", to, copy["title"], copy["body"])
        emit("deliver.sent", channel="log", to=to, title=copy["title"])
        return True


class DiscordChannel:
    name = "discord"

    async def send(self, to: int, copy: dict) -> bool:
        if not settings.discord_webhook_url:
            emit("deliver.skipped", channel="discord", reason="no_webhook", to=to)
            return False
        payload = {
            "embeds": [
                {
                    "title": copy["title"],
                    "description": f"{copy['body']}\n\n_{copy['footer']}_",
                    "color": 0x1FD65F if copy["title"].startswith("Value") else 0xFFC94D,
                }
            ]
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.discord_webhook_url, json=payload)
            resp.raise_for_status()
        emit("deliver.sent", channel="discord", to=to, title=copy["title"])
        return True


_CHANNELS = {c.name: c for c in (LogChannel(), DiscordChannel())}


def get_channel(name: str):
    return _CHANNELS.get(name)
