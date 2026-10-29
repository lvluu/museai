"""Posting queue: finished videos in ``post_dir`` (the Desktop) waiting to go to social media.

muse-video delivers each final video to the Desktop. The dashboard lists them with a caption
and one button per platform that opens its upload page; the user marks each platform as
posted, and once every platform is done the video moves to the Trash.
"""

from __future__ import annotations

import ipaddress
import json
import shutil
import subprocess
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from ...errors import InvalidRequest, NotFound
from ...services.container import Services
from ..deps import get_services
from .dashboard import _local_or_admin

router = APIRouter(tags=["dashboard"], dependencies=[Depends(_local_or_admin)])

# Upload pages. None of them takes a file in the link, so the dashboard also shows the file
# in Finder to drag in. Facebook's reel composer can cross-post to a linked Instagram account.
PLATFORMS = {
    "youtube": ("YouTube Shorts", "https://www.youtube.com/upload"),
    "tiktok": ("TikTok", "https://www.tiktok.com/tiktokstudio/upload"),
    "facebook": ("Facebook Reels", "https://www.facebook.com/reels/create"),
    "instagram": ("Instagram Reels", "https://www.instagram.com/"),
    "x": ("X", "https://x.com/compose/post"),
    "threads": ("Threads", "https://www.threads.com/"),
}
VIDEO_EXT = {".mp4", ".mov", ".m4v"}


def _load(svc: Services) -> dict:
    try:
        return json.loads(svc.settings.posts_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(svc: Services, state: dict) -> None:
    path = svc.settings.posts_file
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    tmp.replace(path)


def _video(svc: Services, name: str) -> Path:
    path = svc.settings.post_dir / name
    if Path(name).name != name or path.suffix.lower() not in VIDEO_EXT or not path.is_file():
        raise NotFound(f"video '{name}' not found")
    return path


def _view(path: Path, entry: dict) -> dict:
    st = path.stat()
    return {"name": path.name, "size": st.st_size, "mtime": st.st_mtime,
            "caption": entry.get("caption", ""), "posted": entry.get("posted", {})}


def _trash(path: Path) -> None:
    if shutil.which("trash"):
        subprocess.run(["trash", str(path)], check=True)
    else:
        bin_ = Path.home() / ".Trash"
        bin_.mkdir(exist_ok=True)
        shutil.move(str(path), bin_ / f"{path.stem}-{int(time.time())}{path.suffix}")


@router.get("/dashboard/posts", include_in_schema=False)
async def list_posts(svc: Services = Depends(get_services)) -> dict:
    state = _load(svc)
    folder = svc.settings.post_dir
    videos = sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT
                     and not p.name.startswith(".")), key=lambda p: p.stat().st_mtime, reverse=True) \
        if folder.is_dir() else []
    return {
        "folder": str(folder),
        "platforms": [{"id": k, "name": n, "url": u} for k, (n, u) in PLATFORMS.items()],
        "videos": [_view(p, state.get(p.name, {})) for p in videos],
    }


@router.get("/dashboard/posts/{name}/file", include_in_schema=False)
async def post_file(name: str, svc: Services = Depends(get_services)) -> FileResponse:
    return FileResponse(_video(svc, name))


# Plain def (not async): trashing and Finder run subprocesses, so FastAPI runs these in a thread.
@router.post("/dashboard/posts/{name}", include_in_schema=False)
def update_post(name: str, body: dict, svc: Services = Depends(get_services)) -> dict:
    """Set the caption, mark a platform posted (or not), or ``{"done": true}`` to trash it now.

    Marking the last platform posted moves the video to the Trash.
    """
    path = _video(svc, name)
    state = _load(svc)
    entry = state.setdefault(name, {})
    if "caption" in body:
        entry["caption"] = str(body["caption"] or "")[:5000]
    if platform := body.get("platform"):
        if platform not in PLATFORMS:
            raise InvalidRequest(f"unknown platform '{platform}'")
        posted = entry.setdefault("posted", {})
        if body.get("posted", True):
            posted[platform] = time.time()
        else:
            posted.pop(platform, None)
    done = body.get("done") or set(entry.get("posted", {})) >= set(PLATFORMS)
    if done:
        _trash(path)
        state.pop(name, None)
    _save(svc, state)
    return {"trashed": bool(done), "video": None if done else _view(path, entry)}


@router.post("/dashboard/posts/{name}/reveal", include_in_schema=False)
def reveal_post(name: str, request: Request, svc: Services = Depends(get_services)) -> dict:
    """Show the video in Finder, to drag into an upload page. Only on the machine itself."""
    path = _video(svc, name)
    host = request.client.host if request.client else ""
    try:
        local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        local = False
    if local and shutil.which("open"):
        subprocess.run(["open", "-R", str(path)], check=False)
    return {"revealed": local}
