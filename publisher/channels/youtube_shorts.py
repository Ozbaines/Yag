import asyncio
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from publisher.channels.base import Channel, PublishResult
from shared.config import settings
from shared.db import Draft
from shared.logger import logger

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_youtube_service():
    creds = Credentials(
        token=None,
        refresh_token=settings.YT_REFRESH_TOKEN,
        client_id=settings.YT_CLIENT_ID,
        client_secret=settings.YT_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds)


class YouTubeShorts(Channel):
    target = "youtube_shorts"

    async def publish(self, draft: Draft) -> PublishResult:
        if not all([settings.YT_CLIENT_ID, settings.YT_CLIENT_SECRET, settings.YT_REFRESH_TOKEN]):
            return PublishResult(success=False, error="YouTube OAuth creds not set")
        if not draft.media_local_path or not Path(draft.media_local_path).exists():
            return PublishResult(success=False, error="No local video file for Shorts")

        title = (draft.title or draft.caption or "")[:100]
        description = (draft.caption or "")[:5000]
        if draft.hashtags:
            tags = [h.lstrip("#") for h in draft.hashtags.split() if h.strip()]
        else:
            tags = ["вирусное", "шортс", "shorts"]

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "24",
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }
        try:
            video_id = await asyncio.to_thread(_upload_sync, draft.media_local_path, body)
        except Exception as e:
            logger.exception("YouTube upload failed: {}", e)
            return PublishResult(success=False, error=str(e))
        url = f"https://www.youtube.com/shorts/{video_id}"
        return PublishResult(success=True, remote_id=video_id, remote_url=url)


def _upload_sync(path: str, body: dict) -> str:
    youtube = _get_youtube_service()
    media = MediaFileUpload(path, chunksize=-1, resumable=True, mimetype="video/*")
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = req.next_chunk()
    return response["id"]
