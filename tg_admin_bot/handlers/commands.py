from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy import func, select

from shared.config import settings
from shared.db import Draft, DraftStatus, get_session

router = Router()


def _is_admin(msg: Message) -> bool:
    return msg.from_user is not None and msg.from_user.id == settings.TG_ADMIN_USER_ID


@router.message(CommandStart())
async def cmd_start(msg: Message) -> None:
    if not _is_admin(msg):
        await msg.answer("Этот бот только для админа канала.")
        return
    await msg.answer(
        "YAg admin bot готов.\n\n"
        "Команды:\n"
        "/stats — статистика драфтов\n"
        "/pending — последние ожидающие\n"
        "/help — помощь"
    )


@router.message(Command("help"))
async def cmd_help(msg: Message) -> None:
    if not _is_admin(msg):
        return
    await msg.answer(
        "Драфты приходят сюда автоматически.\n"
        "✅ Accept — отправит в канал и в Reels/Shorts\n"
        "❌ Reject — отбросить\n"
        "✏️ Edit — после нажатия пришли новый текст подписи\n"
        "🔁 Rewrite — Claude перепишет подпись"
    )


@router.message(Command("stats"))
async def cmd_stats(msg: Message) -> None:
    if not _is_admin(msg):
        return
    async with get_session() as s:
        rows = (await s.execute(
            select(Draft.status, func.count(Draft.id)).group_by(Draft.status)
        )).all()
    lines = ["📊 Статистика драфтов:"]
    for status, cnt in rows:
        lines.append(f"  {status.value}: {cnt}")
    await msg.answer("\n".join(lines) if rows else "Пока пусто.")


@router.message(Command("pending"))
async def cmd_pending(msg: Message) -> None:
    if not _is_admin(msg):
        return
    async with get_session() as s:
        rows = (await s.execute(
            select(Draft)
            .where(Draft.status == DraftStatus.pending_review)
            .order_by(Draft.created_at.desc())
            .limit(10)
        )).scalars().all()
    if not rows:
        await msg.answer("Ожидающих драфтов нет.")
        return
    lines = [f"📥 Ожидают ({len(rows)}):"]
    for d in rows:
        lines.append(f"#{d.id} [{d.virality_score}] {d.title[:60]}")
    await msg.answer("\n".join(lines))
