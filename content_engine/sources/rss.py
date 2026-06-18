import asyncio

import feedparser

from content_engine.sources.base import RawItem, Source
from shared.logger import logger


VIRAL_RSS_FEEDS = [
    "https://www.youtube.com/feeds/videos.xml?user=PewDiePie",
    # Add channels/feeds as needed; these are public examples.
]


class RSSSource(Source):
    name = "rss"

    async def fetch(self, limit: int = 25) -> list[RawItem]:
        items: list[RawItem] = []
        for url in VIRAL_RSS_FEEDS:
            try:
                parsed = await asyncio.to_thread(feedparser.parse, url)
            except Exception as e:
                logger.error("RSS fetch failed [{}]: {}", url, e)
                continue
            for entry in parsed.entries[: max(1, limit // max(1, len(VIRAL_RSS_FEEDS)))]:
                link = getattr(entry, "link", None)
                if not link:
                    continue
                items.append(RawItem(
                    source=self.name,
                    source_id=f"rss:{entry.get('id', link)}",
                    url=link,
                    title=getattr(entry, "title", ""),
                    description=getattr(entry, "summary", "")[:1500],
                    thumbnail_url=(entry.get("media_thumbnail", [{}])[0] or {}).get("url"),
                    extra={"feed": url},
                ))
        logger.info("RSS source produced {} items", len(items))
        return items
