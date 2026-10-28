from __future__ import annotations

import hashlib
import json
import time

from fastapi import APIRouter, Depends, Request

from ...core.media import load_image_ref
from ...core.models import resolve_model
from ...drivers.base import InputImage, VideoRequest
from ...errors import NotFound
from ...services.container import Services
from ...services.tasks import Task
from ..deps import get_services, public_base, require_api_key
from ..schemas import VideoCreateRequest

# An identical request within this window gets the finished clip back instead of a new render.
REUSE_WINDOW = 3600.0

router = APIRouter(tags=["videos"], dependencies=[Depends(require_api_key)])


def _task_view(task: Task) -> dict:
    return {
        "id": task.id,
        "object": "video",
        "status": task.status.value,
        "progress": task.progress,
        "created_at": int(task.created_at),
        "model": task.request.get("model"),
        "result": task.result,
        "error": task.error,
        "account_id": task.account_id,
    }


def submit_video(svc: Services, base: str, meta: dict, first_frame: InputImage | None,
                 session: str | None, reuse=None) -> Task:
    """Queue a video render; an identical request still in flight is joined, not rendered twice."""

    async def runner(task: Task, progress) -> dict:
        req = VideoRequest(prompt=meta["prompt"], model=meta["model"], size=meta["size"],
                           duration=meta["duration"], first_frame=first_frame,
                           timeout=svc.settings.video_timeout, on_progress=progress)
        result = await svc.gateway.generate_video(
            req, on_account=lambda acc: task.assign(acc.id, acc.label), owner=task.session)
        name = svc.media.save(result.data, result.mime, prefix="vid")
        return {"url": f"{base}/v1/media/{name}", "mime": result.mime,
                "width": result.width, "height": result.height}

    key = hashlib.sha256(json.dumps(meta, sort_keys=True).encode())
    if first_frame:
        key.update(first_frame.data)
    return svc.tasks.submit("video", meta, runner, dedupe_key=key.hexdigest(),
                            session=session, reuse=reuse)


@router.post("/v1/videos")
async def create_video(body: VideoCreateRequest, request: Request,
                       svc: Services = Depends(get_services)) -> dict:
    spec = resolve_model(body.model, "video")
    frame_ref = body.image or body.input_reference
    first_frame = InputImage(*(await load_image_ref(frame_ref))) if frame_ref else None
    request_meta = {"model": spec.id, "prompt": body.prompt, "size": body.size,
                    "duration": body.duration or body.seconds, "has_first_frame": bool(first_frame)}

    def reuse(done: Task) -> bool:
        # X-Muse-Retake asks for a new take of the same clip on purpose.
        if request.headers.get("x-muse-retake") or time.time() - done.updated_at > REUSE_WINDOW:
            return False
        try:  # the file may have been deleted since
            svc.media.path_of(str((done.result or {}).get("url", "")).rsplit("/", 1)[-1])
        except NotFound:
            return False
        return True

    task = submit_video(svc, public_base(request), request_meta, first_frame,
                        request.headers.get("x-muse-session") or None, reuse)
    return _task_view(task)


@router.get("/v1/videos/{task_id}")
async def get_video(task_id: str, svc: Services = Depends(get_services)) -> dict:
    task = svc.tasks.get(task_id)
    if task is None or task.kind != "video":
        raise NotFound(f"video task '{task_id}' not found")
    return _task_view(task)
