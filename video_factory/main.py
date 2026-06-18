import asyncio

from shared.db import Draft, DraftStatus, get_session, init_db
from shared.logger import logger
from shared.queue import Q_PUBLISH, Q_VIDEO_PROCESS, pop, push
from video_factory.clipper import process_video
from video_factory.downloader import download_video
from video_factory.transcriber import transcribe


async def handle(draft_id: int) -> None:
    async with get_session() as s:
        draft = await s.get(Draft, draft_id)
        if not draft:
            logger.warning("video_factory: draft {} not found", draft_id)
            return
        url = draft.source_url

    logger.info("video_factory: processing draft {} url={}", draft_id, url)

    # 1. Download
    raw_path = await download_video(url)
    if not raw_path:
        async with get_session() as s:
            d = await s.get(Draft, draft_id)
            if d:
                d.status = DraftStatus.failed
                d.extra = {**(d.extra or {}), "vf_error": "download failed"}
        logger.error("video_factory: download failed for draft {}", draft_id)
        return

    # 2. Transcribe (may return empty list if Whisper not installed)
    segments = await transcribe(raw_path)

    # 3. Find best clip + cut to vertical
    clip_path = await process_video(raw_path, segments)
    if not clip_path:
        async with get_session() as s:
            d = await s.get(Draft, draft_id)
            if d:
                d.media_local_path = str(raw_path)  # fallback to full video
        clip_path = raw_path

    # 4. Persist and hand back to publisher
    async with get_session() as s:
        d = await s.get(Draft, draft_id)
        if d:
            d.media_local_path = str(clip_path)
    await push(Q_PUBLISH, {"draft_id": draft_id})
    logger.info("video_factory: done draft {} clip={}", draft_id, clip_path)


async def main() -> None:
    await init_db()
    logger.info("video_factory started")
    while True:
        try:
            payload = await pop(Q_VIDEO_PROCESS, timeout=10)
            if not payload:
                continue
            draft_id = payload.get("draft_id")
            if draft_id:
                await handle(draft_id)
        except Exception:
            logger.exception("video_factory loop error")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
