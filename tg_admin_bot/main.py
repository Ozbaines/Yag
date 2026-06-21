import asyncio
import html

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, URLInputFile

from shared.config import settings
from shared.db import Draft, get_session, init_db
from shared.logger import logger
from shared.queue import Q_DRAFT_REVIEW, pop
from tg_admin_bot.handlers import router
from tg_admin_bot.handlers.review import _format_draft
from tg_admin_bot.keyboards import draft_review_kb_with_source, dubbed_review_kb


async def draft_dispatcher(bot: Bot) -> None:
    """Pulls drafts from Redis queue and pushes them to the admin chat."""
    logger.info("admin draft dispatcher started")
    while True:
        try:
            payload = await pop(Q_DRAFT_REVIEW, timeout=10)
            if not payload:
                continue
            draft_id = payload.get("draft_id")
            if not draft_id:
                continue
            async with get_session() as s:
                d = await s.get(Draft, draft_id)
                if not d:
                    continue
                kb = draft_review_kb_with_source(d.id, d.source_url)
                text = _format_draft(d)
                thumb = d.thumbnail_url

            try:
                local_path = d.media_local_path
                is_dubbed = (d.extra or {}).get("dubbed", False)
                kb = dubbed_review_kb(d.id, d.source_url) if is_dubbed else kb

                if is_dubbed and local_path and __import__("pathlib").Path(local_path).exists():
                    # Send actual dubbed video file
                    await bot.send_video(
                        chat_id=settings.TG_ADMIN_USER_ID,
                        video=FSInputFile(local_path),
                        caption=text,
                        reply_markup=kb,
                        supports_streaming=True,
                    )
                elif thumb:
                    await bot.send_photo(
                        chat_id=settings.TG_ADMIN_USER_ID,
                        photo=URLInputFile(thumb),
                        caption=text,
                        reply_markup=kb,
                    )
                else:
                    await bot.send_message(
                        chat_id=settings.TG_ADMIN_USER_ID,
                        text=text,
                        reply_markup=kb,
                        disable_web_page_preview=False,
                    )
            except Exception as e:
                logger.error("send draft #{} failed: {}", draft_id, e)
                await bot.send_message(
                    chat_id=settings.TG_ADMIN_USER_ID,
                    text=text,
                    reply_markup=kb,
                )
        except Exception:
            logger.exception("draft_dispatcher loop error")
            await asyncio.sleep(2)


async def main() -> None:
    if not settings.TG_ADMIN_BOT_TOKEN or not settings.TG_ADMIN_USER_ID:
        logger.error("TG_ADMIN_BOT_TOKEN and TG_ADMIN_USER_ID must be set")
        return
    await init_db()
    bot = Bot(token=settings.TG_ADMIN_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    async def on_startup() -> None:
        logger.info("admin bot started, admin_id={}", settings.TG_ADMIN_USER_ID)
        asyncio.create_task(draft_dispatcher(bot))

    dp.startup.register(on_startup)
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "chat_member"], drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
