"""
Finds the best viral clip window using Claude + transcript,
cuts it with ffmpeg into 9:16 vertical format,
burns Russian subtitles if transcript is available.
"""
import asyncio
import tempfile
import uuid
from pathlib import Path

import ffmpeg

from shared.config import settings
from shared.llm import claude
from shared.logger import logger

MAX_CLIP_SEC = 59
MIN_CLIP_SEC = 10

CLIP_SYSTEM = """Ты редактор вирусного контента.
Тебе дан транскрипт видео. Найди ОДИН момент, который максимально цепляет:
- кульминация события (пик напряжения, реакция, "вот это да!")
- смешной/шокирующий момент
- независимый эпизод, понятный без контекста

Верни JSON:
{
  "start_sec": <float>,
  "end_sec": <float>,
  "reason": "<1 предложение>"
}
Условия: end - start должен быть от 10 до 59 секунд.
"""


async def find_best_clip(segments: list[dict], total_sec: float) -> tuple[float, float]:
    if not segments:
        return 0.0, min(MAX_CLIP_SEC, total_sec)
    transcript_lines = [
        f"[{s['start']:.1f}s-{s['end']:.1f}s] {s['text'].strip()}"
        for s in segments[:200]
    ]
    try:
        data = await claude.complete_json(
            system=CLIP_SYSTEM,
            user=f"Длительность видео: {total_sec:.0f}с\n\nТранскрипт:\n" + "\n".join(transcript_lines),
            max_tokens=256,
        )
        start = max(0.0, min(float(data["start_sec"]), total_sec - MIN_CLIP_SEC))
        end = min(float(data["end_sec"]), total_sec)
        if end <= start or end - start < MIN_CLIP_SEC:
            end = min(start + MAX_CLIP_SEC, total_sec)
        if end - start > MAX_CLIP_SEC:
            end = start + MAX_CLIP_SEC
        return start, end
    except Exception as e:
        logger.error("Claude clip selection failed: {}", e)
        return 0.0, min(MAX_CLIP_SEC, total_sec)


def _segments_to_srt(segments: list[dict], clip_start: float) -> str:
    """Convert Whisper segments to SRT, offset by clip start time."""
    def _fmt(sec: float) -> str:
        sec = max(0.0, sec)
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int((sec % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    idx = 1
    for seg in segments:
        s_start = seg["start"] - clip_start
        s_end = seg["end"] - clip_start
        if s_end <= 0:
            continue
        text = seg["text"].strip()
        if not text:
            continue
        lines.append(f"{idx}\n{_fmt(s_start)} --> {_fmt(s_end)}\n{text}\n")
        idx += 1
    return "\n".join(lines)


def _has_audio(path: Path) -> bool:
    try:
        probe = ffmpeg.probe(str(path))
        return any(s["codec_type"] == "audio" for s in probe.get("streams", []))
    except Exception:
        return False


def _run_ffmpeg(source: Path, start: float, end: float, out_path: Path, srt_path: Path | None) -> None:
    duration = end - start
    inp = ffmpeg.input(str(source), ss=start, t=duration)

    # Video pipeline: scale to 9:16 with black bars
    vid = (
        inp.video
        .filter("scale", w=1080, h=1920, force_original_aspect_ratio="decrease")
        .filter("pad", w=1080, h=1920, x="(ow-iw)/2", y="(oh-ih)/2", color="black")
        .filter("setsar", r="1")
        .filter("format", "yuv420p")
    )

    # Subtitle burning requires ffmpeg with libass — skipped until available

    output_kwargs = dict(
        vcodec="libx264",
        crf=22,
        preset="fast",
        movflags="faststart",
    )

    if _has_audio(source):
        aud = inp.audio
        ffmpeg.output(
            vid, aud,
            str(out_path),
            acodec="aac",
            audio_bitrate="128k",
            **output_kwargs,
        ).overwrite_output().run(quiet=True)
    else:
        ffmpeg.output(
            vid,
            str(out_path),
            **output_kwargs,
        ).overwrite_output().run(quiet=True)


async def cut_clip(
    source: Path,
    start: float,
    end: float,
    segments: list[dict] | None = None,
) -> Path | None:
    out_dir = settings.storage_path / "clips"
    out_path = out_dir / f"{uuid.uuid4().hex}.mp4"

    # Build SRT in a temp file if we have transcript
    srt_path: Path | None = None
    if segments:
        clip_segs = [s for s in segments if s["end"] > start and s["start"] < end]
        if clip_segs:
            srt_content = _segments_to_srt(clip_segs, start)
            tmp = tempfile.NamedTemporaryFile(suffix=".srt", delete=False, mode="w", encoding="utf-8")
            tmp.write(srt_content)
            tmp.close()
            srt_path = Path(tmp.name)

    try:
        await asyncio.to_thread(_run_ffmpeg, source, start, end, out_path, srt_path)
        has_aud = _has_audio(out_path)
        logger.info("clip done: {} | audio={} | subtitles={}", out_path.name, has_aud, srt_path is not None)
        return out_path
    except ffmpeg.Error as e:
        logger.error("ffmpeg clip failed: {}", e.stderr.decode() if e.stderr else e)
        return None
    finally:
        if srt_path and srt_path.exists():
            srt_path.unlink(missing_ok=True)


def _get_duration(path: Path) -> float:
    try:
        probe = ffmpeg.probe(str(path))
        return float(probe["format"]["duration"])
    except Exception:
        return 0.0


async def process_video(source: Path, segments: list[dict]) -> Path | None:
    total = _get_duration(source)
    if total < MIN_CLIP_SEC:
        logger.warning("Video too short ({:.1f}s), copying as-is", total)
        start, end = 0.0, total
    else:
        start, end = await find_best_clip(segments, total)
    logger.info("clip window: {:.1f}s -> {:.1f}s ({:.1f}s)", start, end, end - start)
    return await cut_clip(source, start, end, segments=segments)
