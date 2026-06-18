import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from shared.config import settings
from shared.db import init_db
from shared.logger import logger
from tg_subscriber_bot.drip import drip_worker
from tg_subscriber_bot.handlers import router
from tg_subscriber_bot.payments_listener import payments_listener


async def main() -> None:
    if not settings.TG_SUBSCRIBER_BOT_TOKEN:
        logger.error("TG_SUBSCRIBER_BOT_TOKEN not set")
        return
    await init_db()
    bot = Bot(token=settings.TG_SUBSCRIBER_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    async def on_startup() -> None:
        logger.info("subscriber bot started")
        asyncio.create_task(drip_worker(bot))
        asyncio.create_task(payments_listener(bot))

    dp.startup.register(on_startup)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
