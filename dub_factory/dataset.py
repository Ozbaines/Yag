"""Dataset collection for dubbed videos — used for future LLM fine-tuning."""
import json
from datetime import datetime, timezone

from sqlalchemy import func, select

from shared.config import settings
from shared.db import DubDataset, get_session
from shared.logger import logger

RATING_LABELS = {1: "👎 Плохо", 2: "👍 Хорошо", 3: "⭐ Отлично"}


async def save_entry(
    *,
    draft_id: int,
    source_url: str,
    source_title: str,
    transcript_input: str,
    clips_output: dict,
    narrations: list[dict],
    clip_count: int,
    duration_sec: int,
) -> int | None:
    """Create a dataset entry after a video is successfully dubbed."""
    try:
        async with get_session() as s:
            entry = DubDataset(
                draft_id=draft_id,
                source_url=source_url,
                source_title=source_title,
                llm_model=settings.OPENAI_COMPAT_MODEL,
                transcript_input=transcript_input,
                clips_output=clips_output,
                narrations=narrations,
                clip_count=clip_count,
                duration_sec=duration_sec,
            )
            s.add(entry)
            await s.flush()
            logger.info("dataset entry #{} saved for draft #{}", entry.id, draft_id)
            return entry.id
    except Exception as e:
        logger.error("save_entry failed: {}", e)
        return None


async def rate_entry(draft_id: int, rating: int) -> bool:
    """Set admin rating (1/2/3) for a dataset entry identified by draft_id."""
    try:
        async with get_session() as s:
            res = await s.execute(
                select(DubDataset).where(DubDataset.draft_id == draft_id)
            )
            entry = res.scalar_one_or_none()
            if not entry:
                return False
            entry.rating = rating
            entry.rated_at = datetime.now(timezone.utc)
            logger.info(
                "dataset entry for draft #{} rated: {} ({})",
                draft_id,
                rating,
                RATING_LABELS.get(rating, "?"),
            )
            return True
    except Exception as e:
        logger.error("rate_entry failed: {}", e)
        return False


async def export_jsonl(min_rating: int = 2) -> str:
    """
    Export rated entries as JSONL for LLM fine-tuning.
    Only entries with rating >= min_rating are included (default: 👍 and ⭐).
    Format: OpenAI/llama chat messages — system + user (transcript) + assistant (clips JSON).
    """
    from dub_factory.translator import _HISTORY_CLIPS_SYSTEM

    try:
        async with get_session() as s:
            res = await s.execute(
                select(DubDataset)
                .where(DubDataset.rating >= min_rating)
                .order_by(DubDataset.created_at)
            )
            entries = res.scalars().all()
    except Exception as e:
        logger.error("export_jsonl query failed: {}", e)
        return ""

    lines = []
    for e in entries:
        record = {
            "messages": [
                {"role": "system", "content": _HISTORY_CLIPS_SYSTEM},
                {"role": "user", "content": e.transcript_input},
                {
                    "role": "assistant",
                    "content": json.dumps(e.clips_output, ensure_ascii=False),
                },
            ],
            "_meta": {
                "source_url": e.source_url,
                "source_title": e.source_title,
                "rating": e.rating,
                "rating_label": RATING_LABELS.get(e.rating or 0, "?"),
                "clip_count": e.clip_count,
                "llm_model": e.llm_model,
            },
        }
        lines.append(json.dumps(record, ensure_ascii=False))
    return "\n".join(lines)


async def get_stats() -> dict:
    """Return rating distribution for the /dataset_stats command."""
    try:
        async with get_session() as s:
            rows = (
                await s.execute(
                    select(DubDataset.rating, func.count(DubDataset.id)).group_by(
                        DubDataset.rating
                    )
                )
            ).all()
            total = (
                await s.execute(select(func.count(DubDataset.id)))
            ).scalar() or 0
        return {"total": total, "by_rating": {r: c for r, c in rows}}
    except Exception as e:
        logger.error("get_stats failed: {}", e)
        return {"total": 0, "by_rating": {}}
