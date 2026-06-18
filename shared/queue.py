"""Redis-backed lightweight queue helpers for cross-service messaging."""
import json
from typing import Any

from redis.asyncio import Redis

from shared.config import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


# Queue names
Q_DRAFT_REVIEW = "yag:queue:draft_review"        # content_engine -> tg_admin_bot
Q_PUBLISH = "yag:queue:publish"                  # tg_admin_bot -> publisher
Q_VIDEO_PROCESS = "yag:queue:video_process"      # publisher -> video_factory
Q_PAYMENT_EVENT = "yag:queue:payment_event"      # payments -> tg_subscriber_bot


async def push(queue: str, payload: dict[str, Any]) -> None:
    r = get_redis()
    await r.rpush(queue, json.dumps(payload, default=str))


async def pop(queue: str, timeout: int = 5) -> dict[str, Any] | None:
    r = get_redis()
    item = await r.blpop(queue, timeout=timeout)
    if item is None:
        return None
    _, raw = item
    return json.loads(raw)
