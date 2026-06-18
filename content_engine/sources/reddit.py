import asyncpraw

from content_engine.sources.base import RawItem, Source
from shared.config import settings
from shared.logger import logger


class RedditVideosSource(Source):
    name = "reddit"
    SUBREDDITS = (
        "PublicFreakout",
        "interestingasfuck",
        "Damnthatsinteresting",
        "nextfuckinglevel",
        "BeAmazed",
        "ContagiousLaughter",
    )

    async def fetch(self, limit: int = 25) -> list[RawItem]:
        if not (settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET):
            logger.warning("Reddit creds missing, skipping Reddit source")
            return []

        items: list[RawItem] = []
        reddit = asyncpraw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
        )
        try:
            per_sub = max(3, limit // len(self.SUBREDDITS))
            for sub_name in self.SUBREDDITS:
                try:
                    sub = await reddit.subreddit(sub_name)
                    async for post in sub.hot(limit=per_sub):
                        if post.stickied or post.over_18:
                            continue
                        # Prefer video posts; allow image+link too
                        video_url = None
                        duration = None
                        if getattr(post, "is_video", False):
                            video = (post.media or {}).get("reddit_video") or {}
                            video_url = video.get("fallback_url")
                            duration = video.get("duration")
                        items.append(RawItem(
                            source=self.name,
                            source_id=f"reddit:{post.id}",
                            url=video_url or f"https://reddit.com{post.permalink}",
                            title=post.title,
                            description=(post.selftext or "")[:1500],
                            thumbnail_url=post.thumbnail if post.thumbnail and post.thumbnail.startswith("http") else None,
                            duration_sec=duration,
                            view_count=getattr(post, "view_count", None),
                            like_count=post.score,
                            extra={
                                "subreddit": sub_name,
                                "permalink": f"https://reddit.com{post.permalink}",
                                "is_video": bool(getattr(post, "is_video", False)),
                            },
                        ))
                except Exception as e:
                    logger.error("Reddit fetch failed for r/{}: {}", sub_name, e)
        finally:
            await reddit.close()
        logger.info("Reddit source produced {} items", len(items))
        return items
