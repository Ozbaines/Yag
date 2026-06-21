"""
One-shot history dub pipeline:
  fetch next Timeline Channel video (or specific URL) → dub with Russian narration → send to admin bot

Usage:
  python -m dub_factory.main                        # next unseen from channel
  python -m dub_factory.main https://youtu.be/...   # specific video
"""
import asyncio
import sys

from sqlalchemy import select

from dub_factory.dubber import dub_history_video
from dub_factory.sources import fetch_next_channel_video, fetch_video_info
from shared.db import Draft, DraftStatus, DraftType, get_session, init_db
from shared.logger import logger
from shared.queue import Q_DRAFT_REVIEW, push


async def already_seen(source_id: str) -> bool:
    async with get_session() as s:
        res = await s.execute(select(Draft.id).where(Draft.source_id == source_id))
        return res.scalar() is not None


async def _mark_failed(item: dict) -> None:
    async with get_session() as s:
        existing = await s.execute(select(Draft.id).where(Draft.source_id == item["source_id"]))
        if existing.scalar():
            return  # already recorded
        draft = Draft(
            source="timeline_dub",
            source_id=item["source_id"],
            source_url=item["url"],
            type=DraftType.video,
            title=item.get("title", ""),
            status=DraftStatus.rejected,
            virality_score=0.0,
        )
        s.add(draft)
        await s.flush()


async def save_draft(item: dict, result: dict) -> int | None:
    async with get_session() as s:
        draft = Draft(
            source="timeline_dub",
            source_id=item["source_id"],
            source_url=item["url"],
            type=DraftType.video,
            title=result["title"],
            caption=result["caption"],
            hashtags=result["hashtags"],
            thumbnail_url=item.get("thumbnail_url"),
            duration_sec=result["duration"],
            virality_score=0.0,
            media_local_path=result["local_path"],
            status=DraftStatus.pending_review,
            extra={
                "dubbed": True,
                "tts_ok": result["tts_ok"],
                "source_title": item["title"],
                "channel": "TimelineChannel",
            },
        )
        s.add(draft)
        await s.flush()
        return draft.id


async def main() -> None:
    await init_db()

    explicit_url = sys.argv[1] if len(sys.argv) > 1 else None

    if explicit_url:
        logger.info("dub_factory: explicit URL mode — {}", explicit_url)
        item = await fetch_video_info(explicit_url)
        if not item:
            logger.error("Could not fetch info for {}", explicit_url)
            return
        # Force re-process even if previously seen/rejected
        async with get_session() as s:
            await s.execute(
                __import__("sqlalchemy").delete(Draft).where(Draft.source_id == item["source_id"])
            )
    else:
        logger.info("dub_factory: channel mode")
        item = await fetch_next_channel_video(already_seen)
        if not item:
            logger.info("No new videos to process")
            return

    logger.info("Processing: {}", item["title"][:70])
    try:
        result = await dub_history_video(item)
    except Exception as e:
        logger.exception("dub_history_video failed: {}", e)
        result = None

    if not result:
        logger.error("Pipeline returned nothing for {}", item["url"])
        await _mark_failed(item)
        return

    draft_id = await save_draft(item, result)
    if draft_id:
        from dub_factory.dataset import save_entry as save_dataset_entry
        ds = result.get("_dataset", {})
        await save_dataset_entry(
            draft_id=draft_id,
            source_url=item["url"],
            source_title=item["title"],
            transcript_input=ds.get("transcript_input", ""),
            clips_output=ds.get("clips_output", {}),
            narrations=ds.get("narrations", []),
            clip_count=ds.get("clip_count", 0),
            duration_sec=result["duration"],
        )
        await push(Q_DRAFT_REVIEW, {"draft_id": draft_id})
        logger.info("Queued dubbed draft #{} | {}", draft_id, result["title"][:60])

    logger.info("dub_factory done")


if __name__ == "__main__":
    asyncio.run(main())
