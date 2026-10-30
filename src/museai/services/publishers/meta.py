"""Facebook Page Reels and Instagram Reels through the Meta Graph API (resumable upload).

Facebook: ``/{page}/video_reels`` start → upload the bytes to rupload.facebook.com → finish with
``video_state=PUBLISHED``. Instagram: create a REELS container → upload the bytes → wait until the
container is FINISHED → ``/{ig-user}/media_publish``. Both run on the Page access token the channel's
Meta login gave (services/oauth.py); permissions: ``pages_show_list``, ``pages_read_engagement``,
``pages_manage_posts``, ``instagram_basic``, ``instagram_content_publish`` (Meta app review for
anyone but the app's own admins and testers).

The publish call is the step that must not run twice: the checkpoint records it before it is sent,
and a resumed post asks the platform whether the reel is already up.
"""

from __future__ import annotations

import asyncio
import time

import httpx

from .base import Checkpoint, Job, Publisher, PublishError, Result, Save
from .http import check, read, using

VERSION = "v23.0"
GRAPH = f"https://graph.facebook.com/{VERSION}"
RUPLOAD = "https://rupload.facebook.com"


async def _upload(http: httpx.AsyncClient, url: str, data: bytes, token: str) -> None:
    res = await http.post(url, content=data, headers={"Authorization": f"OAuth {token}", "offset": "0",
                                                       "file_size": str(len(data))})
    check(res, "Meta upload")


class FacebookPublisher(Publisher):
    platform = "facebook"

    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self.http = http

    async def publish(self, job: Job, checkpoint: Checkpoint, save: Save) -> Result:
        page, token = job.token["page_id"], job.token["access_token"]
        cp = dict(checkpoint)
        async with using(self.http) as http:
            if cp.get("finishing") and await self._published(http, cp["video_id"], token):
                return self._result(cp["video_id"])
            if not cp.get("video_id"):
                res = await http.post(f"{GRAPH}/{page}/video_reels",
                                      data={"upload_phase": "start", "access_token": token})
                body = check(res, "Facebook reel start").json()
                cp = {"video_id": body["video_id"],
                      "upload_url": body.get("upload_url") or f"{RUPLOAD}/video-upload/{VERSION}/{body['video_id']}"}
                await save(cp)
            if not cp.get("uploaded"):
                await _upload(http, cp["upload_url"], await read(job.video), token)
                cp["uploaded"] = True
                await save(cp)
            cp["finishing"] = True
            await save(cp)
            res = await http.post(f"{GRAPH}/{page}/video_reels", data={
                "upload_phase": "finish", "video_id": cp["video_id"], "video_state": "PUBLISHED",
                "description": job.caption, "access_token": token})
            check(res, "Facebook reel publish")
        return self._result(cp["video_id"])

    @staticmethod
    def _result(video_id: str) -> Result:
        return Result(id=video_id, url=f"https://www.facebook.com/reel/{video_id}")

    @staticmethod
    async def _published(http: httpx.AsyncClient, video_id: str, token: str) -> bool:
        res = await http.get(f"{GRAPH}/{video_id}", params={"fields": "status", "access_token": token})
        if not res.is_success:
            return False
        phase = (res.json().get("status") or {}).get("publishing_phase") or {}
        return phase.get("status") in ("complete", "in_progress")


class InstagramPublisher(Publisher):
    platform = "instagram"
    poll_every = 10.0
    poll_for = 600.0  # Instagram processes a reel in 0.5-3 min

    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self.http = http

    async def publish(self, job: Job, checkpoint: Checkpoint, save: Save) -> Result:
        user, token = job.token["ig_user_id"], job.token["access_token"]
        cp = dict(checkpoint)
        async with using(self.http) as http:
            if cp.get("publishing"):
                status = await self._status(http, cp["container"], token)
                if status == "PUBLISHED":  # it went up before the restart; the media id was lost
                    return Result(id=cp["container"], url=job.token.get("profile_url", ""))
            if not cp.get("container"):
                res = await http.post(f"{GRAPH}/{user}/media", data={
                    "media_type": "REELS", "upload_type": "resumable", "caption": job.caption,
                    "share_to_feed": "true", "access_token": token})
                body = check(res, "Instagram container").json()
                cp = {"container": body["id"],
                      "upload_url": body.get("uri") or f"{RUPLOAD}/ig-api-upload/{VERSION}/{body['id']}"}
                await save(cp)
            if not cp.get("uploaded"):
                await _upload(http, cp["upload_url"], await read(job.video), token)
                cp["uploaded"] = True
                await save(cp)
            deadline = time.monotonic() + self.poll_for
            while (status := await self._status(http, cp["container"], token)) != "FINISHED":
                if status in ("ERROR", "EXPIRED"):
                    await save({})  # a fresh container on the retry
                    raise PublishError(f"Instagram could not process the video ({status})")
                if status == "PUBLISHED":
                    return Result(id=cp["container"], url=job.token.get("profile_url", ""))
                if time.monotonic() > deadline:
                    raise PublishError("Instagram is still processing the video")
                await asyncio.sleep(self.poll_every)
            cp["publishing"] = True
            await save(cp)
            res = await http.post(f"{GRAPH}/{user}/media_publish",
                                  data={"creation_id": cp["container"], "access_token": token})
            media = check(res, "Instagram publish").json()["id"]
            res = await http.get(f"{GRAPH}/{media}", params={"fields": "permalink", "access_token": token})
            url = res.json().get("permalink", "") if res.is_success else ""
        return Result(id=media, url=url)

    @staticmethod
    async def _status(http: httpx.AsyncClient, container: str, token: str) -> str:
        res = await http.get(f"{GRAPH}/{container}", params={"fields": "status_code", "access_token": token})
        return check(res, "Instagram container status").json().get("status_code", "")
