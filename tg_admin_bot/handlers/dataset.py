"""Dataset rating callbacks and export commands for the admin bot."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from dub_factory.dataset import RATING_LABELS, export_jsonl, get_stats, rate_entry
from shared.config import settings
from shared.logger import logger

router = Router()


def _is_admin(uid: int) -> bool:
    return uid == settings.TG_ADMIN_USER_ID


@router.callback_query(F.data.startswith("ds:rate:"))
async def cb_rate_dub(cb: CallbackQuery) -> None:
    """Handle 👎 / 👍 / ⭐ rating buttons on dubbed draft reviews."""
    if not cb.from_user or not _is_admin(cb.from_user.id):
        await cb.answer("Нет доступа", show_alert=True)
        return

    parts = cb.data.split(":")  # ds:rate:{draft_id}:{rating}
    draft_id, rating = int(parts[2]), int(parts[3])

    ok = await rate_entry(draft_id, rating)
    if ok:
        label = RATING_LABELS.get(rating, "?")
        await cb.answer(f"Оценка сохранена: {label}")
        logger.info("admin rated draft #{}: {}", draft_id, label)
    else:
        await cb.answer("Запись в датасете не найдена", show_alert=True)


@router.message(Command("export_dataset"))
async def cmd_export_dataset(msg: Message) -> None:
    """Export all 👍 + ⭐ entries as JSONL ready for fine-tuning."""
    if not _is_admin(msg.from_user.id if msg.from_user else 0):
        return

    await msg.answer("⏳ Собираю датасет...")
    jsonl = await export_jsonl(min_rating=2)
    if not jsonl:
        await msg.answer(
            "Нет оценённых записей с рейтингом 👍 или ⭐.\n"
            "Оцени хотя бы одно видео через кнопки при ревью."
        )
        return

    count = jsonl.count("\n") + 1
    buf = jsonl.encode("utf-8")
    await msg.answer_document(
        document=BufferedInputFile(buf, filename="dub_dataset.jsonl"),
        caption=(
            f"📦 <b>Датасет для файн-тюна</b>\n"
            f"Записей: {count} (👍 Хорошо + ⭐ Отлично)\n\n"
            f"Формат: OpenAI chat JSONL — system + user (транскрипт) + assistant (клипы JSON)\n"
            f"Можно использовать с llama-factory, Axolotl, OpenAI fine-tune API."
        ),
        parse_mode="HTML",
    )


@router.message(Command("dataset_stats"))
async def cmd_dataset_stats(msg: Message) -> None:
    """Show rating distribution across the dataset."""
    if not _is_admin(msg.from_user.id if msg.from_user else 0):
        return

    stats = await get_stats()
    total = stats["total"]
    by_rating = stats["by_rating"]

    lines = [f"📊 <b>Датасет дублированных видео</b>\nВсего записей: {total}\n"]
    for rating, label in [(None, "⏳ Не оценено"), (1, "👎 Плохо"), (2, "👍 Хорошо"), (3, "⭐ Отлично")]:
        cnt = by_rating.get(rating, 0)
        lines.append(f"  {label}: {cnt}")

    rated = sum(by_rating.get(r, 0) for r in (1, 2, 3))
    good = sum(by_rating.get(r, 0) for r in (2, 3))
    if rated:
        lines.append(f"\nГодных для обучения (👍+⭐): {good} из {rated} оценённых")

    await msg.answer("\n".join(lines), parse_mode="HTML")
