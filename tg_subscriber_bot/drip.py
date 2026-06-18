import asyncio
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from shared.config import settings
from shared.db import Subscriber, SubscriberState, get_session
from shared.logger import logger
from tg_subscriber_bot.campaigns import WARMING_STEPS

CHECK_INTERVAL_SEC = 60


def _kb_for_step(cta_label: str | None) -> InlineKeyboardMarkup | None:
    if not cta_label:
        return None
    if "PRO" in cta_label:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cta_label, callback_data="buy_pro")],
        ])
    if settings.TG_CHANNEL_URL:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cta_label, url=settings.TG_CHANNEL_URL)],
        ])
    return None


async def drip_worker(bot: Bot) -> None:
    """Cycles subscribers through warming steps based on time since join."""
    logger.info("drip_worker started")
    while True:
        try:
            await _tick(bot)
        except Exception:
            logger.exception("drip_worker tick failed")
        await asyncio.sleep(CHECK_INTERVAL_SEC)


async def _tick(bot: Bot) -> None:
    now = datetime.now(timezone.utc)
    async with get_session() as s:
        warming = (await s.execute(
            select(Subscriber).where(Subscriber.state == SubscriberState.warming)
        )).scalars().all()

    for sub in warming:
        next_step_idx = sub.drip_step  # 1..N -> next is sub.drip_step (after step 1, schedule step 2)
        if next_step_idx >= len(WARMING_STEPS) + 1:
            continue
        try:
            step = WARMING_STEPS[next_step_idx - 1] if next_step_idx <= len(WARMING_STEPS) else None
        except IndexError:
            step = None
        if step is None:
            continue
        if not sub.joined_at:
            continue
        joined = sub.joined_at if sub.joined_at.tzinfo else sub.joined_at.replace(tzinfo=timezone.utc)
        if now - joined < timedelta(seconds=step.delay_sec):
            continue
        kb = _kb_for_step(step.cta_label)
        try:
            await bot.send_message(sub.tg_id, step.text, reply_markup=kb)
            async with get_session() as s2:
                fresh = await s2.get(Subscriber, sub.id)
                if fresh:
                    fresh.drip_step = next_step_idx + 1
                    if fresh.drip_step > len(WARMING_STEPS):
                        # Stop warming until paid event flips state
                        pass
            logger.info("drip step {} -> tg_id={}", next_step_idx, sub.tg_id)
        except Exception as e:
            logger.warning("drip send failed tg_id={}: {}", sub.tg_id, e)
