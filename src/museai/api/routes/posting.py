"""Posting queue: finished videos in ``post_dir`` (the Desktop) waiting to go to social media.

muse-video delivers each final video to the Desktop. The dashboard lists them with a caption
per platform (``captions``, written by the social-captions skill; ``caption`` is the fallback for a
platform without one) and one button per platform that opens its upload page; the user marks each platform as
posted, and once every platform is done the video moves to the Trash.

A video missing a platform's caption gets one written in the background (services/captions.py).

Each video also gets a posting slot: two a day at the audience's peak hours (``SLOTS``), handed out in
delivery order, with a time per platform (``OFFSETS``) to set in each platform's scheduler.
"""

from __future__ import annotations

import ipaddress
import json
import re
import shutil
import subprocess
import threading
import time
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from ...errors import InvalidRequest, NotFound
from ...services.container import Services
from ..deps import get_services
from .dashboard import _local_or_admin

router = APIRouter(tags=["dashboard"], dependencies=[Depends(_local_or_admin)])

# Upload pages. None of them takes a file in the link, so the dashboard also shows the file
# in Finder to drag in. Facebook's reel composer can cross-post to a linked Instagram account.
# The caption limit is the description's (YouTube's caption is "title\n\ndescription", title <= 100);
# X counts weighted characters (emoji, CJK and Vietnamese letters count 2). The social-captions
# skill's check_captions.py enforces the same limits before delivery.
PLATFORMS = {
    "youtube": ("YouTube Shorts", "https://www.youtube.com/upload", 5000),
    "tiktok": ("TikTok", "https://www.tiktok.com/tiktokstudio/upload", 4000),
    "facebook": ("Facebook Reels", "https://www.facebook.com/reels/create", 2200),
    "instagram": ("Instagram Reels", "https://www.instagram.com/", 2200),
    "x": ("X", "https://x.com/compose/post", 280),
    "threads": ("Threads", "https://www.threads.com/", 500),
}
VIDEO_EXT = {".mp4", ".mov", ".m4v"}

TZ = ZoneInfo("Asia/Ho_Chi_Minh")  # GMT+7: the viewers are in Vietnam
# Two Shorts a day (user rule 2026-10-29), Monday first: (slot 1 midday, slot 2 evening) YouTube times.
# 5-6 h apart so the two don't compete in subscribers' feeds; evening posts go up ~2 h before the
# 20-22 h peak, weekends start earlier.
SLOTS = [("11:30", "18:00"), ("11:30", "18:00"), ("11:30", "17:30"), ("11:30", "18:00"),
         ("11:30", "18:00"), ("10:30", "17:30"), ("10:30", "17:00")]
SLOT_FOCUS = {1: "Midday: bite-sized (stroke order, word of the day, a quick view)",
              2: "Evening: conversations, common mistakes, quizzes that invite comments"}
# Minutes after the YouTube time per platform (midday, evening). TikTok, Reels, X and Threads hand a
# post out within the hour, so they go closer to the peak than Shorts, which needs a head start.
OFFSETS = {"youtube": (0, 0), "tiktok": (30, 60), "facebook": (30, 90), "instagram": (0, 60),
           "x": (30, 120), "threads": (0, 90)}
SLOT_KEY = re.compile(r"^(\d{4}-\d{2}-\d{2})/([12])$")
# Requests (in threads) and the caption writer all read-modify-write posts.json.
_state_lock = threading.Lock()


def _key(name: str) -> str:
    """State key of a file name. macOS lists some names decomposed (NFD) while deliver.sh posts them
    composed, so "Tiếng" could land under two keys and the video lose its caption."""
    return unicodedata.normalize("NFC", name)


def _load(svc: Services) -> dict:
    try:
        raw = json.loads(svc.settings.posts_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    state: dict = {}
    for name, entry in raw.items():  # merge entries saved under a decomposed name
        merged = state.setdefault(_key(name), {})
        merged.update({k: v for k, v in entry.items() if v or k not in merged})
    return state


def _save(svc: Services, state: dict) -> None:
    path = svc.settings.posts_file
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    tmp.replace(path)


def _exists(svc: Services, key: str) -> bool:
    folder = svc.settings.post_dir
    return any(_key(p.name) == key for p in folder.iterdir()) if folder.is_dir() else False


def _video(svc: Services, name: str) -> Path:
    path = svc.settings.post_dir / name
    if Path(name).name != name or path.suffix.lower() not in VIDEO_EXT or not path.is_file():
        raise NotFound(f"video '{name}' not found")
    return path


def _slot_times(key: str) -> dict[str, datetime]:
    """Posting time per platform for a slot key "YYYY-MM-DD/1|2"."""
    day, n = SLOT_KEY.match(key).groups()
    d, n = date.fromisoformat(day), int(n)
    hh, mm = map(int, SLOTS[d.weekday()][n - 1].split(":"))
    base = datetime(d.year, d.month, d.day, hh, mm, tzinfo=TZ)
    return {p: base + timedelta(minutes=off[n - 1]) for p, off in OFFSETS.items()}


def _slots_from(now: datetime):
    """Slot keys from today on whose YouTube time is still ahead of ``now``."""
    d = now.astimezone(TZ).date()
    while True:
        for n in (1, 2):
            key = f"{d.isoformat()}/{n}"
            if _slot_times(key)["youtube"] > now:
                yield key
        d += timedelta(days=1)


def _assign_slots(state: dict, videos: list[Path], now: datetime) -> bool:
    """Give every queued video a slot, oldest delivery first. A slot that passed with nothing posted
    moves to the next free one unless the user picked it. Returns True when the state changed."""
    entries = [(p.name, state.setdefault(_key(p.name), {})) for p in sorted(videos, key=lambda p: p.stat().st_mtime)]
    for _, e in entries:
        if (key := e.get("slot")) and not e.get("posted") and not e.get("slot_pinned") \
                and _slot_times(key)["youtube"] <= now:
            del e["slot"]
    taken = {e["slot"] for _, e in entries if e.get("slot")}
    free = (k for k in _slots_from(now) if k not in taken)
    changed = False
    for _, e in entries:
        if not e.get("slot"):
            e["slot"] = next(free)
            changed = True
    return changed


def _view(path: Path, entry: dict, svc: Services) -> dict:
    st = path.stat()
    key = entry.get("slot")
    return {"name": path.name, "size": st.st_size, "mtime": st.st_mtime,
            "caption": entry.get("caption", ""), "captions": entry.get("captions", {}),
            "auto_captions": svc.captions.status(_key(path.name)),
            "posted": entry.get("posted", {}), "slot": key,
            "schedule": {p: t.isoformat() for p, t in _slot_times(key).items()} if key else {}}


def _calendar(state: dict, names: dict[str, str], now: datetime, days: int = 7) -> list[dict]:
    """The next ``days`` days of slots with the video (file name, by state key in ``names``) booked
    in each (or None)."""
    booked = {e["slot"]: names[n] for n, e in state.items() if n in names and e.get("slot")}
    start = now.astimezone(TZ).date()
    out = []
    for i in range(days):
        d = start + timedelta(days=i)
        slots = []
        for n in (1, 2):
            key = f"{d.isoformat()}/{n}"
            slots.append({"key": key, "n": n, "time": _slot_times(key)["youtube"].isoformat(),
                          "focus": SLOT_FOCUS[n], "video": booked.get(key)})
        out.append({"date": d.isoformat(), "slots": slots})
    return out


def _trash(path: Path) -> None:
    if shutil.which("trash"):
        subprocess.run(["trash", str(path)], check=True)
    else:
        bin_ = Path.home() / ".Trash"
        bin_.mkdir(exist_ok=True)
        shutil.move(str(path), bin_ / f"{path.stem}-{int(time.time())}{path.suffix}")


def _save_captions(svc: Services, key: str, captions: dict[str, str]) -> None:
    """Store auto-written captions in the platforms still empty (the user may have typed one since)."""
    with _state_lock:
        state = _load(svc)
        entry = state.setdefault(key, {})
        own = entry.setdefault("captions", {})
        for platform, text in captions.items():
            own.setdefault(platform, text)
        if not entry.get("caption") and own.get("tiktok"):
            entry["caption"] = own["tiktok"]  # push notifications and the "All" tab show it
        _save(svc, state)


@router.get("/dashboard/posts", include_in_schema=False)
async def list_posts(svc: Services = Depends(get_services)) -> dict:
    folder = svc.settings.post_dir
    videos = sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXT
                     and not p.name.startswith(".")), key=lambda p: p.stat().st_mtime, reverse=True) \
        if folder.is_dir() else []
    now = datetime.now(TZ)
    with _state_lock:
        state = _load(svc)
        if _assign_slots(state, videos, now):
            _save(svc, state)
    for p in videos:
        svc.captions.schedule(_key(p.name), p, state.get(_key(p.name), {}),
                              lambda key, caps: _save_captions(svc, key, caps))
    return {
        "folder": str(folder),
        "timezone": "GMT+7",
        "platforms": [{"id": k, "name": n, "url": u, "limit": lim}
                      for k, (n, u, lim) in PLATFORMS.items()],
        "videos": [_view(p, state.get(_key(p.name), {}), svc) for p in videos],
        "calendar": _calendar(state, {_key(p.name): p.name for p in videos}, now),
    }


@router.get("/dashboard/posts/{name}/file", include_in_schema=False)
async def post_file(name: str, svc: Services = Depends(get_services)) -> FileResponse:
    return FileResponse(_video(svc, name))


# Plain def (not async): trashing and Finder run subprocesses, so FastAPI runs these in a thread.
@router.post("/dashboard/posts/{name}", include_in_schema=False)
def update_post(name: str, body: dict, svc: Services = Depends(get_services)) -> dict:
    """Set the caption, per-platform ``captions`` (merged in; an empty text drops that platform's
    own caption), the posting ``slot`` ("YYYY-MM-DD/1|2"; a video already there swaps into this
    one's old slot), mark a platform posted (or not), or ``{"done": true}`` to trash it now.

    Marking the last platform posted moves the video to the Trash.
    """
    path = _video(svc, name)
    with _state_lock:
        return _update(svc, path, body)


def _update(svc: Services, path: Path, body: dict) -> dict:
    name = _key(path.name)
    state = _load(svc)
    entry = state.setdefault(name, {})
    if "caption" in body:
        entry["caption"] = str(body["caption"] or "")[:5000]
    if captions := body.get("captions"):
        if not isinstance(captions, dict) or set(captions) - set(PLATFORMS):
            raise InvalidRequest(f"captions must map platforms ({', '.join(PLATFORMS)}) to text")
        own = entry.setdefault("captions", {})
        for platform, text in captions.items():
            if text := str(text or "")[:5200]:  # YouTube: title + blank line + description
                own[platform] = text
            else:
                own.pop(platform, None)
    if slot := body.get("slot"):
        try:
            _slot_times(slot)
        except (TypeError, AttributeError, ValueError):
            raise InvalidRequest("slot must be 'YYYY-MM-DD/1' or 'YYYY-MM-DD/2'") from None
        for other, e in state.items():
            if other != name and e.get("slot") == slot and _exists(svc, other):
                if old := entry.get("slot"):
                    e["slot"], e["slot_pinned"] = old, True
                else:
                    e.pop("slot", None)
        entry["slot"], entry["slot_pinned"] = slot, True
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
    return {"trashed": bool(done), "video": None if done else _view(path, entry, svc)}


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
