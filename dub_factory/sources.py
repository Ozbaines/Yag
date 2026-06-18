"""Fetch next unprocessed video from a YouTube channel via yt-dlp."""
import asyncio
from shared.logger import logger

CHANNEL_URL = "https://www.youtube.com/c/TimelineChannel/videos"


async def fetch_video_info(url: str) -> dict | None:
    """Fetch metadata for a specific YouTube video URL."""
    def _get():
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            vid_id = info.get("id", "")
            return {
                "source_id": f"timeline:yt:{vid_id}",
                "url": url,
                "title": info.get("title", ""),
                "duration_sec": int(info.get("duration") or 0),
                "view_count": int(info.get("view_count") or 0),
                "upload_date": info.get("upload_date") or "",
                "thumbnail_url": info.get("thumbnail"),
            }
    try:
        return await asyncio.to_thread(_get)
    except Exception as e:
        logger.error("fetch_video_info failed for {}: {}", url, e)
        return None


async def fetch_next_channel_video(already_seen_fn) -> dict | None:
    """
    Returns the oldest unseen video from the channel, or None.
    already_seen_fn(source_id: str) -> Awaitable[bool]
    """
    def _list() -> list[dict]:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlist_items": "1-50",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(CHANNEL_URL, download=False)
            entries = info.get("entries") or []
            videos = []
            for e in entries:
                vid_id = e.get("id") or ""
                if not vid_id:
                    continue
                videos.append({
                    "source_id": f"timeline:yt:{vid_id}",
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "title": e.get("title", ""),
                    "duration_sec": int(e.get("duration") or 0),
                    "view_count": int(e.get("view_count") or 0),
                    "upload_date": e.get("upload_date") or "",
                    "thumbnail_url": e.get("thumbnail"),
                })
            # Sort oldest first so we process chronologically
            videos.sort(key=lambda v: v["upload_date"])
            return videos

    try:
        videos = await asyncio.to_thread(_list)
    except Exception as e:
        logger.error("Channel fetch failed: {}", e)
        return None

    logger.info("Channel listed {} videos", len(videos))
    for v in videos:
        if v["duration_sec"] < 30 or v["duration_sec"] > 7200:
            continue
        if not await already_seen_fn(v["source_id"]):
            logger.info("Next unseen: {} | {}", v["source_id"], v["title"][:60])
            return v

    logger.info("All channel videos already processed")
    return None
