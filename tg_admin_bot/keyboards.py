from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def draft_review_kb(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Accept", callback_data=f"d:approve:{draft_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"d:reject:{draft_id}"),
        ],
        [
            InlineKeyboardButton(text="✏️ Edit caption", callback_data=f"d:edit:{draft_id}"),
            InlineKeyboardButton(text="🔁 Rewrite (Claude)", callback_data=f"d:rewrite:{draft_id}"),
        ],
        [
            InlineKeyboardButton(text="🔗 Source", url="https://example.com"),
        ],
    ])


def draft_review_kb_with_source(draft_id: int, source_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Accept", callback_data=f"d:approve:{draft_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"d:reject:{draft_id}"),
        ],
        [
            InlineKeyboardButton(text="✏️ Edit caption", callback_data=f"d:edit:{draft_id}"),
            InlineKeyboardButton(text="🔁 Rewrite", callback_data=f"d:rewrite:{draft_id}"),
        ],
        [InlineKeyboardButton(text="🔗 Источник", url=source_url)],
    ])
