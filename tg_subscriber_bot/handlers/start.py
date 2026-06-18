from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from shared.config import settings
from shared.db import Subscriber, SubscriberState, get_session
from shared.logger import logger

router = Router()


def _kb_channel_and_pro() -> InlineKeyboardMarkup:
    rows = []
    if settings.TG_CHANNEL_URL:
        rows.append([InlineKeyboardButton(text="🔥 Канал с роликами", url=settings.TG_CHANNEL_URL)])
    rows.append([InlineKeyboardButton(text="💎 PRO-доступ", callback_data="buy_pro")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(CommandStart(deep_link=True))
@router.message(CommandStart())
async def cmd_start(msg: Message) -> None:
    if not msg.from_user:
        return
    user = msg.from_user
    utm = None
    if msg.text and " " in msg.text:
        utm = msg.text.split(" ", 1)[1][:128]

    async with get_session() as s:
        existing = (await s.execute(select(Subscriber).where(Subscriber.tg_id == user.id))).scalar_one_or_none()
        if existing:
            existing.last_seen_at = datetime.now(timezone.utc)
            sub = existing
        else:
            sub = Subscriber(
                tg_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                state=SubscriberState.warming,
                drip_step=1,
                utm_source=utm,
                last_seen_at=datetime.now(timezone.utc),
            )
            s.add(sub)

    await msg.answer(
        f"Привет, {user.first_name or 'друг'} 👋\n\n"
        "Это <b>YAg</b> — мы собираем самые вирусные ролики со всего интернета "
        "и кидаем их в канал каждый день.\n\n"
        "Без воды. Только то, что реально цепляет.",
        reply_markup=_kb_channel_and_pro(),
    )
    logger.info("Subscriber start: tg_id={} utm={}", user.id, utm)


@router.callback_query(F.data == "buy_pro")
async def cb_buy_pro(cb) -> None:
    if not cb.from_user:
        return
    site = (
        f"{settings.TG_SUBSCRIBER_BOT_USERNAME and 'https://' or ''}"
    )
    # Send to landing
    landing = "https://yag.example/checkout"  # set via NEXT_PUBLIC_SITE_URL in landing
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить PRO", url=landing)],
    ])
    await cb.message.answer(
        "PRO-доступ открывает закрытый канал, ранний доступ и тематические подборки.\n\n"
        "Жми кнопку — оформление займёт минуту.",
        reply_markup=kb,
    )
    await cb.answer()


@router.message(Command("status"))
async def cmd_status(msg: Message) -> None:
    if not msg.from_user:
        return
    async with get_session() as s:
        sub = (await s.execute(select(Subscriber).where(Subscriber.tg_id == msg.from_user.id))).scalar_one_or_none()
    if not sub:
        await msg.answer("Ты ещё не зарегистрирован. Жми /start.")
        return
    paid = sub.paid_until and sub.paid_until > datetime.now(timezone.utc)
    await msg.answer(
        f"Статус: {sub.state.value}\n"
        f"PRO: {'✅ до ' + sub.paid_until.strftime('%Y-%m-%d') if paid else '❌'}"
    )
