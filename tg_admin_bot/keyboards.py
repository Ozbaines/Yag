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


def dubbed_review_kb(draft_id: int, source_url: str) -> InlineKeyboardMarkup:
    """Review keyboard for dubbed videos — includes dataset rating row."""
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
        [
            InlineKeyboardButton(text="👎 Плохо", callback_data=f"ds:rate:{draft_id}:1"),
            InlineKeyboardButton(text="👍 Хорошо", callback_data=f"ds:rate:{draft_id}:2"),
            InlineKeyboardButton(text="⭐ Отлично", callback_data=f"ds:rate:{draft_id}:3"),
        ],
    ])
