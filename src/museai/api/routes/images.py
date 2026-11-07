from __future__ import annotations

import base64
import time

from fastapi import APIRouter, Depends, Request

from ...core.media import load_image_ref
from ...core.models import resolve_model
from ...drivers.base import ImageRequest, InputImage, MediaResult
from ...errors import InvalidRequest
from ...services.container import Services
from ..deps import get_services, public_base, require_api_key
from ..schemas import ImageGenerationRequest

router = APIRouter(tags=["images"], dependencies=[Depends(require_api_key)])


def _image_item(r: MediaResult, fmt: str, svc: Services, base: str) -> dict:
    item: dict = {"revised_prompt": r.revised_prompt}
    if fmt == "b64_json":
        item["b64_json"] = base64.b64encode(r.data).decode()
    else:
        name = svc.media.save(r.data, r.mime, prefix="img")
        item["url"] = f"{base}/v1/media/{name}"
    return item


@router.post("/v1/images/generations")
async def generate_images(body: ImageGenerationRequest, request: Request,
                          svc: Services = Depends(get_services)) -> dict:
    spec = resolve_model(body.model, "image")
    refs = [body.image] if isinstance(body.image, str) else body.image or []
    req = ImageRequest(prompt=body.prompt, model=spec.id, size=body.size, n=body.n,
                       reference_images=[InputImage(*(await load_image_ref(r))) for r in refs],
                       timeout=svc.settings.image_timeout)
    results = await svc.gateway.generate_image(req)
    base = public_base(request)
    return {"created": int(time.time()),
            "data": [_image_item(r, body.response_format, svc, base) for r in results]}


@router.post("/v1/images/edits")
async def edit_images(request: Request, svc: Services = Depends(get_services)) -> dict:
    """Multipart ``image`` / ``image[]`` files + ``prompt`` (OpenAI shape); same output as generations."""
    form = await request.form()
    prompt = str(form.get("prompt") or "").strip()
    uploads = [f for k in ("image", "image[]") for f in form.getlist(k) if hasattr(f, "read")]
    if not prompt or not uploads:
        raise InvalidRequest("prompt and at least one image file are required")
    refs = [InputImage(await f.read(), f.content_type or "image/png") for f in uploads]
    spec = resolve_model(str(form.get("model") or "") or None, "image")
    req = ImageRequest(prompt=prompt, model=spec.id, size=str(form.get("size") or "") or None,
                       n=int(form.get("n") or 1), reference_images=refs,
                       timeout=svc.settings.image_timeout)
    results = await svc.gateway.generate_image(req)
    fmt = str(form.get("response_format") or "url")
    base = public_base(request)
    return {"created": int(time.time()), "data": [_image_item(r, fmt, svc, base) for r in results]}
