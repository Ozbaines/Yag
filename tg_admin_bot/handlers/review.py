from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from shared.config import settings
from shared.db import Draft, DraftStatus, get_session
from shared.llm import claude
from shared.logger import logger
from shared.queue import Q_PUBLISH, push
from tg_admin_bot.keyboards import draft_review_kb_with_source

router = Router()


class EditState(StatesGroup):
    waiting_caption = State()


def _is_admin(uid: int) -> bool:
    return uid == settings.TG_ADMIN_USER_ID


def _format_draft(d: Draft) -> str:
    return (
        f"🎬 <b>Draft #{d.id}</b> · score {d.virality_score}\n"
        f"📡 {d.source} | ⏱ {d.duration_sec or '?'}с\n\n"
        f"<b>{d.title[:200] if d.title else '(no title)'}</b>\n\n"
        f"📝 <i>{d.caption or '(no caption)'}</i>\n\n"
        f"#{(d.hashtags or '').replace(' ', ' #')}\n\n"
        f"💡 {d.claude_reasoning or ''}"
    )


@router.callback_query(F.data.startswith("d:approve:"))
async def cb_approve(cb: CallbackQuery) -> None:
    if not cb.from_user or not _is_admin(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return
    draft_id = int(cb.data.split(":")[2])
    async with get_session() as s:
        d = await s.get(Draft, draft_id)
        if not d:
            await cb.answer("Draft не найден", show_alert=True)
            return
        d.status = DraftStatus.approved
        d.approved_at = datetime.now(timezone.utc)
    await push(Q_PUBLISH, {"draft_id": draft_id})
    await cb.answer("✅ Отправлено в publisher", show_alert=True)
    if cb.message:
        try:
            await cb.message.edit_caption(
                caption=f"✅ <b>APPROVED #{draft_id}</b>",
                parse_mode="HTML",
                reply_markup=None,
            )
        except Exception:
            try:
                await cb.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
    logger.info("approved draft #{}", draft_id)


@router.callback_query(F.data.startswith("d:reject:"))
async def cb_reject(cb: CallbackQuery) -> None:
    if not cb.from_user or not _is_admin(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return
    draft_id = int(cb.data.split(":")[2])
    async with get_session() as s:
        d = await s.get(Draft, draft_id)
        if d:
            d.status = DraftStatus.rejected
    await cb.answer("❌ Отклонено")
    if cb.message:
        try:
            await cb.message.edit_caption(caption=f"❌ REJECTED #{draft_id}", parse_mode="HTML", reply_markup=None)
        except Exception:
            try:
                await cb.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
    logger.info("rejected draft #{}", draft_id)


@router.callback_query(F.data.startswith("d:edit:"))
async def cb_edit(cb: CallbackQuery, state: FSMContext) -> None:
    if not cb.from_user or not _is_admin(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return
    draft_id = int(cb.data.split(":")[2])
    await state.set_state(EditState.waiting_caption)
    await state.update_data(draft_id=draft_id)
    await cb.answer()
    if cb.message:
        await cb.message.answer(f"Пришли новый текст подписи для draft #{draft_id}:")


@router.message(EditState.waiting_caption)
async def edit_caption(msg: Message, state: FSMContext) -> None:
    if not msg.from_user or not _is_admin(msg.from_user.id):
        return
    data = await state.get_data()
    draft_id = data.get("draft_id")
    if not draft_id or not msg.text:
        return
    async with get_session() as s:
        d = await s.get(Draft, draft_id)
        if not d:
            await msg.answer("Draft не найден")
            await state.clear()
            return
        d.caption = msg.text
        d.status = DraftStatus.edited
    await state.clear()
    await msg.answer(f"✏️ Caption для #{draft_id} обновлён. Жми Accept, чтобы опубликовать.")


@router.callback_query(F.data.startswith("d:rewrite:"))
async def cb_rewrite(cb: CallbackQuery) -> None:
    if not cb.from_user or not _is_admin(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return
    draft_id = int(cb.data.split(":")[2])
    async with get_session() as s:
        d = await s.get(Draft, draft_id)
        if not d:
            await cb.answer("Draft не найден", show_alert=True)
            return
        old_caption = d.caption or d.title or ""

    await cb.answer("Claude переписывает...")
    try:
        new_caption = await claude.complete(
            system=(
                "Ты — редактор Telegram-канала про вирусные ролики. "
                "Перепиши подпись короче, ярче, с разговорным тоном. 1-2 строки. "
                "Без воды, без 'смотрите видео'. Можно лёгкий эмодзи."
            ),
            user=f"Текущая подпись:\n{old_caption}\n\nЗаголовок видео: {d.title}",
            max_tokens=200,
        )
    except Exception as e:
        logger.error("Rewrite failed: {}", e)
        if cb.message:
            await cb.message.answer("⚠️ Не удалось переписать. Попробуй ещё раз.")
        return

    async with get_session() as s:
        d = await s.get(Draft, draft_id)
        if d:
            d.caption = new_caption.strip()
            d.status = DraftStatus.edited
    if cb.message:
        await cb.message.answer(f"🔁 Новая подпись для #{draft_id}:\n\n{new_caption}\n\nНажми Accept в исходном сообщении.")
