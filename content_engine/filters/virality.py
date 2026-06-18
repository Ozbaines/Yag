import asyncio
import json
from dataclasses import dataclass

from content_engine.sources.base import RawItem
from shared.llm import claude
from shared.logger import logger


VIRALITY_SYSTEM = """Ты — главред Telegram-канала про вирусные ролики (русскоязычная аудитория, 18–35).

Твоя задача — оценить, насколько контент достоин публикации в канал, и подготовить пост.

Критерии вирусности (по убыванию веса):
1. Эмоциональный пик: смех, шок, восхищение, "вау-эффект"
2. Уникальность: редкое/неожиданное действие, кадр, ситуация
3. Понятность без контекста: видно из превью/первых секунд, что происходит
4. Релевантность аудитории: интересно русскоязычному зрителю
5. Качество: не мутный камкордер, не реклама, не политика, не NSFW, не насилие

Скоринг:
- 9-10: топ, обязательно публиковать
- 7-8: хорошо, можно публиковать
- 5-6: средне, нужна редактура/обрезка
- 0-4: не публиковать

Подпись: 1-2 короткие строки на русском, в разговорном тоне, без воды, без "смотрите видео" — пусть само завирусится. Можно эмодзи в меру.

Хэштеги: 3-5 релевантных русских хэштегов через пробел, без решёток.
"""

VIRALITY_USER_TEMPLATE = """Источник: {source}
URL: {url}
Заголовок: {title}
Описание: {description}
Длительность: {duration} сек
Просмотры: {views}
Лайки: {likes}
Доп: {extra}

Верни JSON:
{{
  "score": <число 0-10>,
  "reason": "<краткое обоснование 1-2 предложения>",
  "caption_ru": "<подпись для поста на русском>",
  "hashtags": "<3-5 хэштегов через пробел без #>",
  "publish": <true|false>
}}
"""


@dataclass
class Virality:
    score: float
    reason: str
    caption: str
    hashtags: str
    publish: bool


class ViralityFilter:
    async def evaluate(self, item: RawItem) -> Virality | None:
        user = VIRALITY_USER_TEMPLATE.format(
            source=item.source,
            url=item.url,
            title=item.title,
            description=item.description or "(нет)",
            duration=item.duration_sec or "?",
            views=item.view_count or "?",
            likes=item.like_count or "?",
            extra=json.dumps(item.extra, ensure_ascii=False)[:500],
        )
        try:
            data = await claude.complete_json(
                system=VIRALITY_SYSTEM,
                user=user,
                max_tokens=300,
            )
            await asyncio.sleep(8)
        except Exception as e:
            logger.error("Claude virality eval failed for {}: {}", item.source_id, e)
            await asyncio.sleep(15)
            return None

        try:
            return Virality(
                score=float(data.get("score", 0)),
                reason=str(data.get("reason", "")),
                caption=str(data.get("caption_ru", "")),
                hashtags=str(data.get("hashtags", "")),
                publish=bool(data.get("publish", False)),
            )
        except (TypeError, ValueError) as e:
            logger.error("Bad virality payload for {}: {} | {}", item.source_id, e, data)
            return None
