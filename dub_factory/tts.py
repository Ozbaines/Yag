"""Russian TTS using Silero (on-prem PyTorch model)."""
import asyncio
import ssl
from pathlib import Path

from shared.logger import logger


def _fix_ssl() -> None:
    try:
        import certifi
        ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass

SPEAKER = "xenia"   # female, good intonation; options: aidar, baya, kseniya, xenia, eugene
SAMPLE_RATE = 48000

_model = None


def _load_model():
    global _model
    if _model is None:
        import torch
        _fix_ssl()
        logger.info("Loading Silero TTS model...")
        model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language="ru",
            speaker="v3_1_ru",
            trust_repo=True,
        )
        model.to(torch.device("cpu"))
        _model = model
        logger.info("Silero TTS ready")
    return _model


def _generate(text: str, out_path: Path) -> bool:
    import torch
    import tempfile
    model = _load_model()
    MAX_CHARS = 800
    chunks = _split_text(text, MAX_CHARS)
    audio_parts = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        audio = model.apply_tts(text=chunk.strip(), speaker=SPEAKER, sample_rate=SAMPLE_RATE)
        audio_parts.append(audio)
    if not audio_parts:
        return False
    combined = torch.cat(audio_parts)
    # Save via soundfile (avoids torchaudio/torchcodec dependency)
    try:
        import soundfile as sf
        sf.write(str(out_path), combined.numpy(), SAMPLE_RATE)
    except ImportError:
        # Fallback: save via scipy
        import scipy.io.wavfile as wav
        import numpy as np
        wav.write(str(out_path), SAMPLE_RATE, combined.numpy().astype(np.float32))
    return out_path.exists() and out_path.stat().st_size > 0


def _split_text(text: str, max_chars: int) -> list[str]:
    """Split on sentence boundaries to stay within model char limit."""
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 > max_chars and current:
            chunks.append(current)
            current = s
        else:
            current = (current + " " + s).strip()
    if current:
        chunks.append(current)
    return chunks


async def text_to_speech(text: str, out_path: Path) -> bool:
    """Generate Russian TTS from plain text using Silero."""
    if not text.strip():
        return False
    try:
        return await asyncio.to_thread(_generate, text, out_path)
    except Exception as e:
        logger.error("Silero TTS failed: {}", e)
        return False


async def segments_to_speech(segments: list[dict], out_path: Path) -> bool:
    """Generate Russian TTS from translated segments."""
    text = " ".join(s["text"].strip() for s in segments if s.get("text", "").strip())
    return await text_to_speech(text, out_path)
