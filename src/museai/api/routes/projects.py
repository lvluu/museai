"""``POST /v1/projects``: ask muse for code, get the files and a zip back."""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import Field

from ...core.models import resolve_model
from ...core.projects import PROJECT_INSTRUCTIONS, build_zip, extract_files
from ...drivers.base import ChatRequest
from ...errors import UpstreamError
from ...services.container import Services
from ..deps import get_services, public_base, require_api_key
from ..schemas import _Lenient

router = APIRouter(tags=["projects"], dependencies=[Depends(require_api_key)])


class ProjectRequest(_Lenient):
    prompt: str = Field(min_length=1)
    model: str | None = None
    include_content: bool = False
    user: str | None = None


@router.post("/v1/projects")
async def create_project(body: ProjectRequest, request: Request,
                         svc: Services = Depends(get_services)) -> dict:
    spec = resolve_model(body.model, "chat")
    prompt = PROJECT_INSTRUCTIONS + body.prompt
    req = ChatRequest(prompt=prompt, model=spec.id, timeout=svc.settings.chat_timeout,
                      first_token_timeout=svc.settings.first_token_timeout,
                      conversation_hint=body.user, turns=[("user", prompt)])
    text = await svc.gateway.chat_complete(req)
    files = extract_files(text)
    if not files:
        raise UpstreamError("muse replied without any file block")
    name = svc.media.save(build_zip(files), "application/zip", prefix="proj")
    return {"id": "proj_" + uuid.uuid4().hex[:16], "object": "project", "created": int(time.time()),
            "model": spec.id, "zip_url": f"{public_base(request)}/v1/media/{name}",
            "files": [{"path": p, "bytes": len(c.encode()),
                       **({"content": c} if body.include_content else {})} for p, c in files.items()],
            "text": text}
