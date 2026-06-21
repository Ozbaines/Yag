from aiogram import Router

from tg_admin_bot.handlers.commands import router as commands_router
from tg_admin_bot.handlers.dataset import router as dataset_router
from tg_admin_bot.handlers.review import router as review_router

router = Router()
router.include_router(commands_router)
router.include_router(review_router)
router.include_router(dataset_router)

__all__ = ["router"]
