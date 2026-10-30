"""TikTok through the Content Posting API, Direct Post (``/v2/post/publish/video/init/``, file upload).

TikTok publishes on its own once the last chunk is in, so ``init`` starts the irreversible part.
Its ``publish_id`` is saved right after; a resumed post asks ``/status/fetch/`` where it stands and
uploads again only when TikTok says the upload failed or expired.

Scopes: ``user.info.basic``, ``video.publish``. Until the app passes TikTok's audit, every post is
private (``SELF_ONLY``) and at most 5 users may post in 24 h; ``creator_info`` lists the privacy
levels the account may use and this driver picks the most public one the job allows.
"""

from __future__ import annotations

import httpx

from .base import Checkpoint, Job, Publisher, PublishError, Result, Save
from .http import check, read, using

API = "https://open.tiktokapis.com/v2"
CHUNK = 10 * 1024 * 1024  # TikTok: chunks of 5-64 MB, the last one up to 128 MB; one chunk below 64 MB
SINGLE = 64 * 1024 * 1024
PREFERENCE = ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY"]


def chunks(size: int) -> list[tuple[int, int]]:
    """(first byte, last byte) per chunk; the remainder joins the last chunk, as TikTok requires."""
    if size <= SINGLE:
        return [(0, size - 1)]
    n = size // CHUNK
    return [(i * CHUNK, (i + 1) * CHUNK - 1 if i < n - 1 else size - 1) for i in range(n)]


class TikTokPublisher(Publisher):
    platform = "tiktok"

    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self.http = http

    async def publish(self, job: Job, checkpoint: Checkpoint, save: Save) -> Result:
        auth = {"Authorization": f"Bearer {job.token['access_token']}",
                "Content-Type": "application/json; charset=UTF-8"}
        async with using(self.http) as http:
            if publish_id := checkpoint.get("publish_id"):
                status, post_ids = await self._status(http, publish_id, auth)
                if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
                    return self._result(job, publish_id, post_ids)
                if status not in ("FAILED", ""):
                    raise PublishError(f"TikTok is still processing the post ({status})")
                await save({})  # failed or expired: post it again
            data = await read(job.video)
            parts = chunks(len(data))
            res = await http.post(f"{API}/post/publish/creator_info/query/", headers=auth)
            creator = check(res, "TikTok creator info").json().get("data", {})
            allowed = creator.get("privacy_level_options") or ["SELF_ONLY"]
            wanted = PREFERENCE if job.privacy == "public" else ["SELF_ONLY"]
            privacy = next((p for p in wanted if p in allowed), allowed[0])
            body = {"post_info": {"title": job.caption[:2200], "privacy_level": privacy,
                                  "disable_comment": False, "disable_duet": False, "disable_stitch": False,
                                  "is_aigc": True},  # muse renders are AI-generated content
                    "source_info": {"source": "FILE_UPLOAD", "video_size": len(data),
                                    "chunk_size": parts[0][1] + 1, "total_chunk_count": len(parts)}}
            res = await http.post(f"{API}/post/publish/video/init/", headers=auth, json=body)
            got = _data(check(res, "TikTok init"))
            publish_id, upload_url = got["publish_id"], got["upload_url"]
            await save({"publish_id": publish_id})
            for first, last in parts:
                res = await http.put(upload_url, content=data[first:last + 1], headers={
                    "Content-Type": "video/mp4", "Content-Length": str(last - first + 1),
                    "Content-Range": f"bytes {first}-{last}/{len(data)}"})
                check(res, "TikTok upload")
            status, post_ids = await self._status(http, publish_id, auth)
            if status == "FAILED":
                await save({})
                raise PublishError("TikTok rejected the video")
        return self._result(job, publish_id, post_ids)

    @staticmethod
    def _result(job: Job, publish_id: str, post_ids: list) -> Result:
        user = job.token.get("username", "")
        if post_ids and user:
            return Result(id=str(post_ids[0]), url=f"https://www.tiktok.com/@{user}/video/{post_ids[0]}")
        # A private post has no public id; it still shows on the profile.
        return Result(id=publish_id, url=f"https://www.tiktok.com/@{user}" if user else "")

    @staticmethod
    async def _status(http: httpx.AsyncClient, publish_id: str, auth: dict) -> tuple[str, list]:
        res = await http.post(f"{API}/post/publish/status/fetch/", headers=auth, json={"publish_id": publish_id})
        if res.status_code == 404:
            return "", []
        data = _data(check(res, "TikTok status"))
        return data.get("status", ""), data.get("publicaly_available_post_id") or []


def _data(res: httpx.Response) -> dict:
    body = res.json()
    err = body.get("error") or {}
    if err.get("code") not in (None, "ok"):
        retry = err.get("code") in ("rate_limit_exceeded", "internal_error")
        raise PublishError(f"TikTok: {err.get('code')}: {err.get('message', '')}", retry=retry)
    return body.get("data") or {}
