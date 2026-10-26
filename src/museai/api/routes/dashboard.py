"""Admin dashboard: which account rendered which video.

Requests from the machine running museai need no key; anyone else needs the admin
key, passed to the page as ``/dashboard#key=<admin key>``.
"""

from __future__ import annotations

import ipaddress
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from ...services.container import Services
from ..deps import get_services, require_admin_key

router = APIRouter(tags=["dashboard"])

_PAGE = Path(__file__).resolve().parent.parent / "static" / "dashboard.html"


def _local_or_admin(request: Request) -> None:
    host = request.client.host if request.client else ""
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    require_admin_key(request)


@router.get("/dashboard", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(_PAGE, media_type="text/html", headers={"Cache-Control": "no-cache"})


@router.get("/dashboard/data", include_in_schema=False, dependencies=[Depends(_local_or_admin)])
async def dashboard_data(limit: int = 1000, svc: Services = Depends(get_services)) -> dict:
    return {
        "accounts": [a.public() for a in svc.pool.all()],
        "videos": [t.model_dump(mode="json") for t in svc.tasks.list(limit) if t.kind == "video"],
    }
