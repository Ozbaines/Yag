import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from publisher.channels.instagram_reels import InstagramReels
from publisher.channels.tg_channel import TelegramChannel
from publisher.channels.youtube_shorts import YouTubeShorts
from publisher.channels.base import Channel
from shared.config import settings
from shared.db import Draft, DraftStatus, Publication, PublicationTarget, get_session, init_db
from shared.logger import logger
from shared.queue import Q_PUBLISH, Q_VIDEO_PROCESS, pop, push

CHANNELS: list[Channel] = [
    TelegramChannel(),
    InstagramReels(),
    YouTubeShorts(),
]


async def process_draft(draft_id: int) -> None:
    async with get_session() as s:
        d = await s.get(Draft, draft_id)
        if not d:
            logger.warning("publisher: draft {} not found", draft_id)
            return

        # If video has no local path yet, ask video_factory to download/clip it first
        if not d.media_local_path:
            await push(Q_VIDEO_PROCESS, {"draft_id": draft_id})
            # Re-enqueue self to be picked up after video_factory is done
            # The video_factory will push back to Q_PUBLISH when done
            return

    # Publish to all channels
    for channel in CHANNELS:
        try:
            async with get_session() as s:
                draft = await s.get(Draft, draft_id)
                if not draft:
                    break
                result = await channel.publish(draft)
                pub = Publication(
                    draft_id=draft_id,
                    target=PublicationTarget(channel.target),
                    remote_id=result.remote_id,
                    remote_url=result.remote_url,
                    success=result.success,
                    error=result.error,
                )
                s.add(pub)
                if not result.success:
                    logger.error("channel {} failed for draft {}: {}", channel.target, draft_id, result.error)
                else:
                    logger.info("published draft {} -> {} ({})", draft_id, channel.target, result.remote_id)
        except Exception as e:
            logger.exception("channel {} crashed for draft {}: {}", channel.target, draft_id, e)

    # Mark draft published if at least one channel succeeded
    async with get_session() as s:
        draft = await s.get(Draft, draft_id)
        pubs = (await s.execute(select(Publication).where(Publication.draft_id == draft_id))).scalars().all()
        if draft and any(p.success for p in pubs):
            draft.status = DraftStatus.published
            draft.published_at = datetime.now(timezone.utc)


async def main() -> None:
    await init_db()
    logger.info("publisher started")
    while True:
        try:
            payload = await pop(Q_PUBLISH, timeout=10)
            if not payload:
                continue
            draft_id = payload.get("draft_id")
            if draft_id:
                await process_draft(draft_id)
        except Exception:
            logger.exception("publisher loop error")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
