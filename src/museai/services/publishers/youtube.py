"""YouTube Shorts through the YouTube Data API v3 (``videos.insert``, resumable upload).

A vertical video up to 3 min uploads as a Short. The upload session URL is saved before the bytes
go up; a resumed post asks that session how far it got (``Content-Range: bytes */size``), and a
finished session answers with the video, so a restart never uploads the video twice.

Scopes: ``youtube.upload`` (post) and ``youtube.readonly`` (show which channel is connected).
Videos posted through an unaudited Google Cloud project stay private: the project needs the
YouTube API audit (docs/auto-post.md).
"""

from __future__ import annotations

import json

import httpx

from .base import Checkpoint, Job, Publisher, PublishError, Result, Save, title_and_description
from .http import check, read, using

UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
THUMBNAIL = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
CATEGORY_PEOPLE = "22"


class YouTubePublisher(Publisher):
    platform = "youtube"

    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self.http = http

    async def publish(self, job: Job, checkpoint: Checkpoint, save: Save) -> Result:
        auth = {"Authorization": f"Bearer {job.token['access_token']}"}
        async with using(self.http) as http:
            video_id = checkpoint.get("video_id")
            if not video_id:
                data = await read(job.video)
                # YouTube creates the video only once a session receives every byte, so an
                # unfinished session is dropped and the upload starts over in a new one.
                if session := checkpoint.get("session"):
                    video_id = await _finished(http, session, len(data), auth)
                if not video_id:
                    session = await _start(http, job, len(data), auth)
                    await save({"session": session})
                    res = await http.put(session, content=data, headers={**auth, "Content-Type": "video/*"})
                    video_id = check(res, "YouTube upload").json()["id"]
                await save({"video_id": video_id})
            if job.thumbnail and not checkpoint.get("thumbnail"):
                # Needs a verified channel; a failed thumbnail must not fail the post.
                res = await http.post(THUMBNAIL, params={"videoId": video_id, "uploadType": "media"},
                                      content=await read(job.thumbnail),
                                      headers={**auth, "Content-Type": "image/jpeg"})
                await save({"video_id": video_id, "thumbnail": res.status_code})
        return Result(id=video_id, url=f"https://youtube.com/shorts/{video_id}")


async def _start(http: httpx.AsyncClient, job: Job, size: int, auth: dict) -> str:
    title, description = title_and_description(job.caption)
    meta = {"snippet": {"title": title, "description": description, "categoryId": CATEGORY_PEOPLE},
            "status": {"privacyStatus": job.privacy, "selfDeclaredMadeForKids": False,
                       # muse renders are synthetic media: YouTube asks for this disclosure.
                       "containsSyntheticMedia": True}}
    res = await http.post(UPLOAD, params={"uploadType": "resumable", "part": "snippet,status"},
                          content=json.dumps(meta),
                          headers={**auth, "Content-Type": "application/json; charset=UTF-8",
                                   "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/*"})
    session = check(res, "YouTube upload session").headers.get("location")
    if not session:
        raise PublishError("YouTube gave no upload session URL")
    return session


async def _finished(http: httpx.AsyncClient, session: str, size: int, auth: dict) -> str | None:
    """The video id when the session finished, None when it is gone or still open."""
    res = await http.put(session, headers={**auth, "Content-Range": f"bytes */{size}"})
    if res.status_code in (200, 201):
        return res.json()["id"]
    return None

