import asyncio
import re
import uuid
from pathlib import Path

import yt_dlp

from shared.config import settings
from shared.logger import logger


async def download_video(url: str, max_height: int = 1080) -> Path | None:
    """Download video via yt-dlp, return local path or None on failure."""
    out_dir = settings.storage_path / "media"
    file_id = uuid.uuid4().hex
    out_template = str(out_dir / f"{file_id}.%(ext)s")

    ydl_opts = {
        # Prefer H.264 to avoid HDR/AV1/VP9 pixel format issues that cause dark output
        "format": (
            f"bestvideo[height<={max_height}][vcodec^=avc]+bestaudio[ext=m4a]"
            f"/bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]"
            f"/best[height<={max_height}][ext=mp4]/best"
        ),
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
    }

    def _dl() -> str | None:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    return None
                fn = ydl.prepare_filename(info)
                # yt-dlp may change extension
                p = Path(re.sub(r"\.\w+$", ".mp4", fn))
                if p.exists():
                    return str(p)
                # Try .webm fallback
                p2 = Path(re.sub(r"\.\w+$", ".webm", fn))
                return str(p2) if p2.exists() else fn
        except Exception as e:
            logger.error("yt-dlp failed [{}]: {}", url, e)
            return None

    result = await asyncio.to_thread(_dl)
    return Path(result) if result else None
