from content_engine.sources.base import RawItem, Source
from content_engine.sources.youtube import YouTubeTrendingSource
from content_engine.sources.reddit import RedditVideosSource
from content_engine.sources.rss import RSSSource

ALL_SOURCES: list[Source] = [
    YouTubeTrendingSource(),
    RedditVideosSource(),
    RSSSource(),
]

__all__ = ["RawItem", "Source", "ALL_SOURCES"]
