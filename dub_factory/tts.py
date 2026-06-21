"""Russian TTS using XTTS-v2 (Coqui) — GPU-accelerated on CUDA, CPU fallback."""
import asyncio
from pathlib import Path

from shared.logger import logger

# Built-in XTTS-v2 speaker for Russian narration (documentary style).
# Full list: tts.speakers  — swap anytime without redownloading the model.
DEFAULT_SPEAKER = "Gitta Nikolina"  # clear female voice, works well in Russian
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

_tts = None


def _load_model():
    global _tts
    if _tts is None:
        import torch
        from TTS.api import TTS

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading XTTS-v2 on {}...", device)
        _tts = TTS(MODEL_NAME).to(device)
        logger.info("XTTS-v2 ready | speakers: {}", len(_tts.speakers))
    return _tts


def _generate(text: str, out_path: Path, speaker: str, speaker_wav: str | None) -> bool:
    tts = _load_model()
    kwargs = dict(
        text=text,
        language="ru",
        file_path=str(out_path),
    )
    if speaker_wav:
        # Voice cloning mode
        kwargs["speaker_wav"] = speaker_wav
    else:
        # Built-in speaker mode
        kwargs["speaker"] = speaker

    tts.tts_to_file(**kwargs)
    return out_path.exists() and out_path.stat().st_size > 0


def _split_text(text: str, max_chars: int = 200) -> list[str]:
    """Split on sentence boundaries — XTTS works best with short chunks."""
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = s
        else:
            current = (current + " " + s).strip()
    if current:
        chunks.append(current.strip())
    return chunks or [text]


def _generate_long(text: str, out_path: Path, speaker: str, speaker_wav: str | None) -> bool:
    """Split long text into chunks, generate each, concatenate with ffmpeg."""
    import tempfile
    import ffmpeg

    chunks = _split_text(text, max_chars=200)
    if len(chunks) == 1:
        return _generate(text, out_path, speaker, speaker_wav)

    tmp_dir = out_path.parent
    part_paths: list[Path] = []
    try:
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            part = tmp_dir / f"{out_path.stem}_part{i}.wav"
            if _generate(chunk, part, speaker, speaker_wav):
                part_paths.append(part)

        if not part_paths:
            return False
        if len(part_paths) == 1:
            part_paths[0].rename(out_path)
            return True

        # Concatenate parts
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for p in part_paths:
                f.write(f"file '{p}'\n")
            list_file = f.name
        try:
            ffmpeg.input(list_file, format="concat", safe=0).output(
                str(out_path), acodec="pcm_s16le"
            ).overwrite_output().run(quiet=True)
        finally:
            Path(list_file).unlink(missing_ok=True)

        return out_path.exists() and out_path.stat().st_size > 0
    finally:
        for p in part_paths:
            p.unlink(missing_ok=True)


async def text_to_speech(
    text: str,
    out_path: Path,
    speaker: str = DEFAULT_SPEAKER,
    speaker_wav: str | None = None,
) -> bool:
    """Generate Russian TTS via XTTS-v2. Pass speaker_wav for voice cloning."""
    if not text.strip():
        return False
    try:
        return await asyncio.to_thread(_generate_long, text, out_path, speaker, speaker_wav)
    except Exception as e:
        logger.error("XTTS-v2 TTS failed: {}", e)
        return False


async def segments_to_speech(
    segments: list[dict],
    out_path: Path,
    speaker: str = DEFAULT_SPEAKER,
    speaker_wav: str | None = None,
) -> bool:
    """Generate Russian TTS from translated segments."""
    text = " ".join(s["text"].strip() for s in segments if s.get("text", "").strip())
    return await text_to_speech(text, out_path, speaker, speaker_wav)
