import asyncio
from pathlib import Path

import httpx

from publisher.channels.base import Channel, PublishResult
from shared.config import settings
from shared.db import Draft
from shared.logger import logger


class InstagramReels(Channel):
    target = "instagram_reels"
    BASE = "https://graph.facebook.com/v21.0"

    async def publish(self, draft: Draft) -> PublishResult:
        if not settings.IG_ACCESS_TOKEN or not settings.IG_USER_ID:
            return PublishResult(success=False, error="IG credentials not set")
        if not draft.media_local_path or not Path(draft.media_local_path).exists():
            return PublishResult(success=False, error="No local video file for Reels")

        caption = _build_caption(draft)
        async with httpx.AsyncClient(timeout=120) as client:
            # Step 1: upload container
            r = await client.post(
                f"{self.BASE}/{settings.IG_USER_ID}/media",
                params={
                    "media_type": "REELS",
                    "caption": caption[:2200],
                    "video_url": draft.media_remote_url or "",
                    "share_to_feed": "true",
                    "access_token": settings.IG_ACCESS_TOKEN,
                },
            )
            if r.status_code != 200:
                return PublishResult(success=False, error=f"IG media init failed: {r.text}")
            container_id = r.json().get("id")
            if not container_id:
                return PublishResult(success=False, error="No container_id in IG response")

            # Step 2: poll until FINISHED
            for _ in range(20):
                await asyncio.sleep(10)
                status_r = await client.get(
                    f"{self.BASE}/{container_id}",
                    params={"fields": "status_code", "access_token": settings.IG_ACCESS_TOKEN},
                )
                status_code = status_r.json().get("status_code")
                if status_code == "FINISHED":
                    break
                if status_code == "ERROR":
                    return PublishResult(success=False, error="IG media processing ERROR")
            else:
                return PublishResult(success=False, error="IG media processing timeout")

            # Step 3: publish
            pub_r = await client.post(
                f"{self.BASE}/{settings.IG_USER_ID}/media_publish",
                params={"creation_id": container_id, "access_token": settings.IG_ACCESS_TOKEN},
            )
            if pub_r.status_code != 200:
                return PublishResult(success=False, error=f"IG publish failed: {pub_r.text}")
            media_id = pub_r.json().get("id")
        return PublishResult(success=True, remote_id=media_id)


def _build_caption(draft: Draft) -> str:
    caption = draft.caption or draft.title or ""
    if draft.hashtags:
        tags = " ".join(f"#{h.lstrip('#')}" for h in draft.hashtags.split())
        return f"{caption}\n\n{tags}"
    return caption
