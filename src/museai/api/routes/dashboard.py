"""Admin dashboard: which account rendered which video.

Requests from the machine running museai need no key; anyone else needs the admin
key, passed to the page as ``/dashboard#key=<admin key>``.
"""

from __future__ import annotations

import ipaddress
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from ...accounts.model import Account
from ...services.container import Services
from ...services.tasks import Task, TaskStatus
from ..deps import get_services, require_admin_key

router = APIRouter(tags=["dashboard"])

_PAGE = Path(__file__).resolve().parent.parent / "static" / "dashboard.html"


def usage_estimate(acc: Account, videos: list[Task]) -> dict[str, Any]:
    """Estimate videos left before muse.ai says "Out of usage" again.

    muse.ai exposes no balance, so the cap is learned: the most videos the account
    finished between two "Out of usage" hits (the first window starts when tracking
    started). ``used`` counts videos finished since the last hit.
    """
    mine = [t for t in videos if t.account_id == acc.id]
    done = sorted(t.updated_at for t in mine if t.status == TaskStatus.SUCCEEDED)
    start = min((t.created_at for t in mine), default=None)
    caps = []
    for hit in sorted(acc.quota_hits):
        if start is not None and start < hit:
            caps.append(sum(start < t <= hit for t in done))
        start = hit
    since = start if acc.quota_hits else None
    used = sum(since is None or t > since for t in done)
    cap = max(caps) if caps else None
    return {
        "cap": cap,
        "used": used,
        "left": None if cap is None else max(cap - used, 0),
        "windows": len(caps),
    }


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
    videos = [t for t in svc.tasks.list(limit) if t.kind == "video"]
    accounts = svc.pool.all()
    return {
        "accounts": [a.public() for a in accounts],
        "usage": {a.id: usage_estimate(a, videos) for a in accounts},
        "videos": [t.model_dump(mode="json") for t in videos],
    }
