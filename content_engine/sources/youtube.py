import re

import httpx

from content_engine.sources.base import RawItem, Source
from shared.config import settings
from shared.logger import logger


def _parse_iso_duration(s: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    h, mn, sec = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mn * 60 + sec


class YouTubeTrendingSource(Source):
    name = "youtube"
    REGIONS = ("RU",)
    CATEGORIES = ("24", "23", "17", "22", "28")  # Entertainment, Comedy, Sports, People, Science

    async def fetch(self, limit: int = 25) -> list[RawItem]:
        if not settings.YOUTUBE_API_KEY:
            logger.warning("YOUTUBE_API_KEY not set, skipping YouTube source")
            return []

        seen_ids: set[str] = set()
        items: list[RawItem] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for region in self.REGIONS:
                for category in self.CATEGORIES:
                    try:
                        r = await client.get(
                            "https://www.googleapis.com/youtube/v3/videos",
                            params={
                                "part": "snippet,contentDetails,statistics",
                                "chart": "mostPopular",
                                "regionCode": region,
                                "videoCategoryId": category,
                                "maxResults": min(limit, 50),
                                "key": settings.YOUTUBE_API_KEY,
                            },
                        )
                        r.raise_for_status()
                        data = r.json()
                    except httpx.HTTPError as e:
                        logger.error("YouTube fetch failed [{}/{}]: {}", region, category, e)
                        continue

                    for v in data.get("items", []):
                        if v["id"] in seen_ids:
                            continue
                        seen_ids.add(v["id"])
                        duration = _parse_iso_duration(v.get("contentDetails", {}).get("duration", ""))
                        if duration > 600:  # skip long videos, we want clippable
                            continue
                        snip = v.get("snippet", {})
                        stats = v.get("statistics", {})
                        items.append(RawItem(
                            source=self.name,
                            source_id=f"yt:{v['id']}",
                            url=f"https://www.youtube.com/watch?v={v['id']}",
                            title=snip.get("title", ""),
                            description=snip.get("description", "")[:1500],
                            thumbnail_url=(snip.get("thumbnails", {}).get("high") or {}).get("url"),
                            duration_sec=duration,
                            view_count=int(stats.get("viewCount", 0) or 0),
                            like_count=int(stats.get("likeCount", 0) or 0),
                            extra={"region": region, "category": category, "channel": snip.get("channelTitle")},
                        ))
        logger.info("YouTube source produced {} items", len(items))
        return items
