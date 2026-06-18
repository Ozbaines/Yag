import asyncio
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import select

from shared.db import Subscriber, SubscriberState, get_session
from shared.logger import logger
from shared.queue import Q_PAYMENT_EVENT, pop


async def payments_listener(bot: Bot) -> None:
    """Listens for payment events from the payments service and grants access."""
    logger.info("payments_listener started")
    while True:
        try:
            payload = await pop(Q_PAYMENT_EVENT, timeout=10)
            if not payload:
                continue
            tg_id = payload.get("tg_id")
            status = payload.get("status")
            days = int(payload.get("days", 30))
            product = payload.get("product_code", "pro")

            if not tg_id or status != "succeeded":
                continue

            async with get_session() as s:
                sub = (await s.execute(select(Subscriber).where(Subscriber.tg_id == tg_id))).scalar_one_or_none()
                if not sub:
                    sub = Subscriber(tg_id=tg_id, state=SubscriberState.paid)
                    s.add(sub)
                sub.state = SubscriberState.paid
                base = sub.paid_until if sub.paid_until and sub.paid_until > datetime.now(timezone.utc) else datetime.now(timezone.utc)
                sub.paid_until = base + timedelta(days=days)

            try:
                await bot.send_message(
                    tg_id,
                    f"🎉 Оплата прошла! PRO-доступ активирован до "
                    f"{(datetime.now(timezone.utc) + timedelta(days=days)).strftime('%d.%m.%Y')}.\n\n"
                    "Ссылка на закрытый канал придёт следующим сообщением.",
                )
            except Exception as e:
                logger.warning("payment notify failed tg_id={}: {}", tg_id, e)
        except Exception:
            logger.exception("payments_listener loop error")
            await asyncio.sleep(2)
