import asyncio
import ssl
from pathlib import Path

from shared.logger import logger


def _fix_ssl() -> None:
    """macOS ships broken SSL certs for Python — patch with certifi."""
    try:
        import certifi
        ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass


async def transcribe(
    video_path: Path,
    language: str | None = "ru",
    model_size: str = "base",
) -> list[dict]:
    """
    Returns list of segments: [{"start": float, "end": float, "text": str}, ...]
    language=None lets Whisper auto-detect. model_size: tiny/base/small.
    """
    try:
        import whisper
    except ImportError:
        logger.warning("whisper not installed, skipping transcription")
        return []

    def _run() -> list[dict]:
        _fix_ssl()
        model = whisper.load_model(model_size)
        kwargs: dict = {"task": "transcribe", "verbose": False, "fp16": False}
        if language:
            kwargs["language"] = language
        result = model.transcribe(str(video_path), **kwargs)
        return result.get("segments", [])

    try:
        segments = await asyncio.to_thread(_run)
        logger.info("transcribed {} segments for {}", len(segments), video_path.name)
        return segments
    except Exception as e:
        logger.error("Whisper failed for {}: {}", video_path, e)
        return []
