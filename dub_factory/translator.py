import asyncio

from shared.llm import claude
from shared.logger import logger

_SCORE_SYSTEM = """Ты — редактор вирусного контента. Оцени видео по заголовку и статистике.
Верни JSON: {"score": <0-10>, "publish": <true|false>}
Критерии: эмоциональный пик, уникальность, понятность без контекста, виральность для русской аудитории.
Порог публикации — 7 и выше."""

_HISTORY_CLIPS_SYSTEM = """Ты — режиссёр монтажа исторических документальных фильмов.
Дан транскрипт видео с таймингами [Xs] (X = секунда от начала).

Задача: выбрать 12-16 отрывков, которые вместе составят связный документальный фильм ~10 минут.
Требования:
- Каждый отрывок 35-60 секунд
- Суммарная длительность 550-650 секунд (~10 минут)
- Хронологический порядок, связное повествование от начала до конца
- Начни с самого интригующего момента, заверши выводом/итогом
- Покрой все ключевые сюжетные точки

ВАЖНО: start_sec и end_sec — только числа секунд (целые или дробные). Никаких формул или вычислений.

Верни только JSON:
{
  "clips": [{"start_sec": 120.0, "end_sec": 175.0, "topic": "краткая тема"}],
  "title": "заголовок до 100 символов",
  "caption": "подпись 2-3 предложения",
  "hashtags": "5-7 хэштегов через пробел без #"
}"""

_NARRATE_SYSTEM = """Ты — профессиональный закадровый диктор исторического документального фильма.
Переведи данный английский отрывок транскрипта на живой литературный русский язык.
Адаптируй для устной речи: естественные паузы, выразительные формулировки.
Верни ТОЛЬКО перевод без пояснений."""

_TRANSLATE_SYSTEM = """Ты — профессиональный переводчик и редактор русскоязычного Telegram-канала.

Тебе дан транскрипт видео на иностранном языке (сегменты с таймингами).
Задача:
1. Переведи каждый сегмент на живой разговорный русский язык
2. Сохрани тайминги (start/end) без изменений
3. Также создай короткую подпись-описание для поста (1-2 предложения, разговорный тон)
4. Придумай 3-5 русских хэштегов

Верни JSON:
{
  "segments": [{"start": <float>, "end": <float>, "text": "<перевод>"}],
  "caption": "<подпись для поста>",
  "hashtags": "<хэштеги через пробел без #>"
}"""


async def quick_score(title: str, views: int, likes: int, duration: int, region: str) -> tuple[float, bool]:
    try:
        data = await claude.complete_json(
            system=_SCORE_SYSTEM,
            user=f"Заголовок: {title}\nПросмотры: {views}\nЛайки: {likes}\nДлительность: {duration}с\nРегион: {region}",
            max_tokens=80,
        )
        await asyncio.sleep(4)
        score = float(data.get("score", 0))
        publish = bool(data.get("publish", False))
        return score, publish
    except Exception as e:
        logger.error("quick_score failed: {}", e)
        await asyncio.sleep(15)
        return 0.0, False


async def select_history_clips(
    segments: list[dict], total_sec: float
) -> tuple[dict | None, str]:
    """Ask LLM to pick historical clips. Returns (clip_plan_dict, llm_input_text)."""
    if not segments:
        return None, ""
    # Sample evenly across the full video (max 120 segments ≈ ~3k tokens)
    step = max(1, len(segments) // 120)
    sampled = segments[::step][:120]
    lines = [f"[{s['start']:.0f}s] {s['text'].strip()}" for s in sampled]
    llm_input = (
        f"Длительность видео: {total_sec:.0f}с\n\nТранскрипт (каждый ~{step * 5}с):\n"
        + "\n".join(lines)
    )
    try:
        data = await claude.complete_json(
            system=_HISTORY_CLIPS_SYSTEM,
            user=llm_input,
            max_tokens=2048,
        )
        await asyncio.sleep(4)
        clips = data.get("clips", [])
        if not clips:
            return None, llm_input
        return data, llm_input
    except Exception as e:
        logger.error("select_history_clips failed: {}", e)
        await asyncio.sleep(15)
        return None, llm_input


async def narrate_clip(segments: list[dict]) -> str:
    """Translate English transcript segments into Russian narration text."""
    if not segments:
        return ""
    text = " ".join(s["text"].strip() for s in segments if s.get("text", "").strip())
    if not text:
        return ""
    try:
        result = await claude.complete(
            system=_NARRATE_SYSTEM,
            user=text,
            max_tokens=1024,
        )
        await asyncio.sleep(4)
        return result.strip()
    except Exception as e:
        logger.error("narrate_clip failed: {}", e)
        await asyncio.sleep(15)
        return ""


async def translate_segments(segments: list[dict]) -> tuple[list[dict], str, str]:
    """Translate Whisper segments to Russian. Returns (ru_segments, caption, hashtags)."""
    if not segments:
        return [], "", ""

    # Limit segments to avoid token overflow
    clip_segs = segments[:40]
    lines = [f"[{s['start']:.1f}-{s['end']:.1f}] {s['text'].strip()}" for s in clip_segs]
    try:
        data = await claude.complete_json(
            system=_TRANSLATE_SYSTEM,
            user="Транскрипт:\n" + "\n".join(lines),
            max_tokens=3000,
        )
        await asyncio.sleep(4)
        ru_segs = data.get("segments", [])
        caption = str(data.get("caption", ""))
        hashtags = str(data.get("hashtags", ""))
        # Fallback: if no segments parsed, build from raw caption
        if not ru_segs and caption:
            logger.warning("translate_segments: no segments parsed, using caption only")
        return ru_segs, caption, hashtags
    except Exception as e:
        logger.error("translate_segments failed: {}", e)
        await asyncio.sleep(15)
        return [], "", ""
