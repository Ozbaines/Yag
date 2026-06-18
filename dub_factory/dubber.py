"""
History dub pipeline:
  download full video → transcribe (English) → LLM picks 4-6 moments →
  per clip: translate → Silero TTS → cut + replace audio →
  ffmpeg concat → send to admin
"""
import asyncio
import tempfile
import uuid
from pathlib import Path

import ffmpeg

from shared.config import settings
from shared.logger import logger
from video_factory.downloader import download_video
from video_factory.transcriber import transcribe

MIN_CLIP_SEC = 35
MAX_CLIP_SEC = 65
MIN_TOTAL_SEC = 540
MAX_TOTAL_SEC = 660


def _get_duration(path: Path) -> float:
    try:
        probe = ffmpeg.probe(str(path))
        return float(probe["format"]["duration"])
    except Exception:
        return 0.0


def _run_clip_with_tts(
    source: Path,
    tts_path: Path,
    start: float,
    end: float,
    out_path: Path,
) -> None:
    duration = end - start
    inp = ffmpeg.input(str(source), ss=start, t=duration)
    vid = (
        inp.video
        .filter("scale", w=1080, h=1920, force_original_aspect_ratio="decrease")
        .filter("pad", w=1080, h=1920, x="(ow-iw)/2", y="(oh-ih)/2", color="black")
        .filter("setsar", r="1")
        .filter("format", "yuv420p")
    )
    tts_audio = ffmpeg.input(str(tts_path)).audio
    (
        ffmpeg.output(
            vid, tts_audio, str(out_path),
            vcodec="libx264", acodec="aac",
            audio_bitrate="128k", crf=22, preset="fast",
            movflags="faststart", t=duration,
        )
        .overwrite_output()
        .run(quiet=True)
    )


TG_MAX_BYTES = 45 * 1024 * 1024  # 45 MB — leave headroom under Telegram's 50 MB bot limit


def _compress_for_telegram(src: Path, out: Path, duration: float) -> None:
    """Re-encode to fit within TG_MAX_BYTES using 2-pass bitrate targeting."""
    target_kbps = int((TG_MAX_BYTES * 8) / duration / 1000)
    audio_kbps = 96
    video_kbps = max(100, target_kbps - audio_kbps)
    logger.info("Compressing for Telegram: {}kbps video + {}kbps audio (target {:.0f}s)", video_kbps, audio_kbps, duration)
    (
        ffmpeg.input(str(src))
        .output(
            str(out),
            vcodec="libx264",
            video_bitrate=f"{video_kbps}k",
            acodec="aac",
            audio_bitrate=f"{audio_kbps}k",
            preset="fast",
            movflags="faststart",
        )
        .overwrite_output()
        .run(quiet=True)
    )


def _concat_clips(clip_paths: list[Path], out_path: Path) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")
        list_file = f.name
    try:
        (
            ffmpeg.input(list_file, format="concat", safe=0)
            .output(
                str(out_path),
                vcodec="libx264", acodec="aac",
                audio_bitrate="128k", crf=22, preset="fast",
                movflags="faststart",
            )
            .overwrite_output()
            .run(quiet=True)
        )
    finally:
        Path(list_file).unlink(missing_ok=True)


def _clamp_clip(start: float, end: float, total: float) -> tuple[float, float]:
    start = max(0.0, min(start, total - MIN_CLIP_SEC))
    end = min(end, total)
    if end - start < MIN_CLIP_SEC:
        end = min(start + MIN_CLIP_SEC, total)
    if end - start > MAX_CLIP_SEC:
        end = start + MAX_CLIP_SEC
    return start, end


async def dub_history_video(item: dict) -> dict | None:
    """
    Full pipeline for one historical video.
    Returns dict with local_path, caption, hashtags, duration or None on failure.
    """
    from dub_factory.translator import narrate_clip, select_history_clips
    from dub_factory.tts import text_to_speech

    url = item["url"]
    logger.info("History dub: {}", item["title"][:70])

    # 1. Download
    source = await download_video(url, max_height=1080)
    if not source or not source.exists():
        logger.error("Download failed: {}", url)
        return None

    total = _get_duration(source)
    if total < 60:
        logger.warning("Too short ({:.0f}s): {}", total, url)
        source.unlink(missing_ok=True)
        return None

    # 2. Transcribe in English (tiny model for speed on long videos)
    logger.info("Transcribing {:.0f}s video...", total)
    segments = await transcribe(source, language="en", model_size="tiny")
    if not segments:
        logger.warning("No transcript for {}", url)
        source.unlink(missing_ok=True)
        return None

    # 3. LLM selects 4-6 historical moments
    plan = await select_history_clips(segments, total)
    if not plan or not plan.get("clips"):
        logger.error("LLM clip selection failed for {}", url)
        source.unlink(missing_ok=True)
        return None

    clips_plan = plan["clips"]
    caption = plan.get("caption", item["title"])
    hashtags = plan.get("hashtags", "история documentary")
    logger.info("Plan: {} clips | {}", len(clips_plan), plan.get("title", ""))

    # 4. Per-clip: translate → TTS → cut video
    out_dir = settings.storage_path / "dubbed"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_clips: list[Path] = []

    for i, clip_def in enumerate(clips_plan):
        try:
            start, end = _clamp_clip(
                float(clip_def["start_sec"]), float(clip_def["end_sec"]), total
            )
            # Collect transcript for this window
            win_segs = [s for s in segments if s["end"] > start and s["start"] < end]
            if not win_segs:
                logger.warning("No segments in clip {}: {:.0f}-{:.0f}s", i, start, end)
                continue

            # Translate to Russian narration
            ru_text = await narrate_clip(win_segs)
            if not ru_text:
                logger.warning("Empty narration for clip {}", i)
                continue

            # TTS
            tts_path = out_dir / f"{uuid.uuid4().hex}.wav"
            tts_ok = await text_to_speech(ru_text, tts_path)
            if not tts_ok:
                logger.warning("TTS failed for clip {}", i)
                tts_path.unlink(missing_ok=True)
                continue

            # Cut + replace audio
            clip_out = out_dir / f"{uuid.uuid4().hex}.mp4"
            await asyncio.to_thread(_run_clip_with_tts, source, tts_path, start, end, clip_out)
            tts_path.unlink(missing_ok=True)

            if clip_out.exists() and _get_duration(clip_out) > 1:
                tmp_clips.append(clip_out)
                logger.info("  clip {}: {:.0f}-{:.0f}s ({:.0f}s) OK", i, start, end, end - start)
            else:
                clip_out.unlink(missing_ok=True)
        except Exception as e:
            logger.error("Clip {} failed: {}", i, e)

    source.unlink(missing_ok=True)

    if not tmp_clips:
        logger.error("No clips produced for {}", url)
        return None

    # 5. Concatenate all clips
    final_path = out_dir / f"{uuid.uuid4().hex}.mp4"
    try:
        if len(tmp_clips) == 1:
            tmp_clips[0].rename(final_path)
        else:
            await asyncio.to_thread(_concat_clips, tmp_clips, final_path)
    except ffmpeg.Error as e:
        logger.error("Concat failed: {}", e.stderr.decode() if e.stderr else e)
        return None
    finally:
        for p in tmp_clips:
            p.unlink(missing_ok=True)

    if not final_path.exists():
        return None

    duration = _get_duration(final_path)

    # Re-encode if file exceeds Telegram bot limit
    file_size = final_path.stat().st_size
    if file_size > TG_MAX_BYTES and duration > 0:
        compressed_path = out_dir / f"{uuid.uuid4().hex}.mp4"
        try:
            await asyncio.to_thread(_compress_for_telegram, final_path, compressed_path, duration)
            final_path.unlink(missing_ok=True)
            final_path = compressed_path
        except ffmpeg.Error as e:
            logger.error("Compression failed: {}", e.stderr.decode() if e.stderr else e)
            compressed_path.unlink(missing_ok=True)

    logger.info("History dub done: {} | {:.0f}s | {} clips | {:.1f}MB",
                final_path.name, duration, len(clips_plan), final_path.stat().st_size / 1024 / 1024)

    return {
        "local_path": str(final_path),
        "caption": caption,
        "hashtags": hashtags,
        "title": plan.get("title", item["title"]),
        "duration": int(duration),
        "tts_ok": True,
    }
