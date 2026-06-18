import asyncio
import hashlib
from datetime import datetime, timezone

from sqlalchemy import select

from content_engine.filters.virality import ViralityFilter
from content_engine.sources import ALL_SOURCES
from content_engine.sources.base import RawItem
from shared.db import Draft, DraftStatus, DraftType, get_session, init_db
from shared.logger import logger
from shared.queue import Q_DRAFT_REVIEW, push

MIN_PUBLISH_SCORE = 8.0


async def already_seen(source_id: str) -> bool:
    async with get_session() as s:
        res = await s.execute(select(Draft.id).where(Draft.source_id == source_id))
        return res.scalar() is not None


async def save_draft(item: RawItem, score: float, caption: str, hashtags: str, reason: str) -> Draft | None:
    async with get_session() as s:
        draft = Draft(
            source=item.source,
            source_id=item.source_id,
            source_url=item.url,
            type=DraftType.video,
            title=item.title,
            original_text=item.description,
            caption=caption,
            hashtags=hashtags,
            thumbnail_url=item.thumbnail_url,
            duration_sec=item.duration_sec,
            virality_score=score,
            claude_reasoning=reason,
            status=DraftStatus.pending_review,
            extra={
                "view_count": item.view_count,
                "like_count": item.like_count,
                **(item.extra or {}),
            },
        )
        s.add(draft)
        await s.flush()
        draft_id = draft.id
        return draft if draft_id else None


async def run_once() -> None:
    vf = ViralityFilter()
    seen_hashes: set[str] = set()

    for source in ALL_SOURCES:
        try:
            items = await source.fetch(limit=5)
        except Exception as e:
            logger.exception("Source {} crashed: {}", source.name, e)
            continue

        for item in items:
            title_hash = hashlib.sha256(item.title.lower().strip().encode()).hexdigest()[:16]
            if title_hash in seen_hashes:
                continue
            seen_hashes.add(title_hash)

            if await already_seen(item.source_id):
                continue

            verdict = await vf.evaluate(item)
            if not verdict:
                continue
            if not verdict.publish or verdict.score < MIN_PUBLISH_SCORE:
                logger.info("Skipped {} score={} reason={}", item.source_id, verdict.score, verdict.reason[:80])
                continue

            draft = await save_draft(item, verdict.score, verdict.caption, verdict.hashtags, verdict.reason)
            if not draft:
                continue
            await push(Q_DRAFT_REVIEW, {"draft_id": draft.id})
            logger.info("Queued draft {} score={} | {}", draft.id, verdict.score, item.title[:60])


async def main() -> None:
    await init_db()
    logger.info("content_engine started (single run, limit=40, min_score={})", MIN_PUBLISH_SCORE)
    try:
        await run_once()
    except Exception:
        logger.exception("content_engine cycle failed")
    logger.info("content_engine done")


if __name__ == "__main__":
    asyncio.run(main())
