from pathlib import Path

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, URLInputFile

from publisher.channels.base import Channel, PublishResult
from shared.config import settings
from shared.db import Draft
from shared.logger import logger


def _format_caption(draft: Draft) -> str:
    caption = draft.caption or draft.title or ""
    hashtags = draft.hashtags or ""
    if hashtags:
        tags = " ".join(f"#{h.lstrip('#')}" for h in hashtags.split() if h.strip())
        return f"{caption}\n\n{tags}"
    return caption


class TelegramChannel(Channel):
    target = "tg_channel"

    def __init__(self) -> None:
        if not settings.TG_ADMIN_BOT_TOKEN:
            raise RuntimeError("TG_ADMIN_BOT_TOKEN required for channel publishing")
        self.bot = Bot(
            token=settings.TG_ADMIN_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.channel = settings.TG_CHANNEL_ID

    async def publish(self, draft: Draft) -> PublishResult:
        if not self.channel:
            return PublishResult(success=False, error="TG_CHANNEL_ID not set")

        caption = _format_caption(draft)
        try:
            if draft.media_local_path and Path(draft.media_local_path).exists():
                msg = await self.bot.send_video(
                    chat_id=self.channel,
                    video=FSInputFile(draft.media_local_path),
                    caption=caption[:1024],
                    supports_streaming=True,
                )
            elif draft.media_remote_url:
                msg = await self.bot.send_video(
                    chat_id=self.channel,
                    video=URLInputFile(draft.media_remote_url),
                    caption=caption[:1024],
                    supports_streaming=True,
                )
            elif draft.thumbnail_url:
                msg = await self.bot.send_photo(
                    chat_id=self.channel,
                    photo=URLInputFile(draft.thumbnail_url),
                    caption=f"{caption[:1020]}\n\n<a href=\"{draft.source_url}\">Источник</a>"[:1024],
                )
            else:
                msg = await self.bot.send_message(
                    chat_id=self.channel,
                    text=f"{caption}\n\n{draft.source_url}",
                    disable_web_page_preview=False,
                )
        except Exception as e:
            logger.exception("TG channel publish failed: {}", e)
            return PublishResult(success=False, error=str(e))
        finally:
            await self.bot.session.close()

        url = None
        if isinstance(self.channel, str) and self.channel.startswith("@"):
            url = f"https://t.me/{self.channel[1:]}/{msg.message_id}"
        return PublishResult(success=True, remote_id=str(msg.message_id), remote_url=url)
