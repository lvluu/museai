"""Posting queue: finished videos in ``post_dir`` (the Desktop) waiting to go to social media.

muse-video delivers each final video to the Desktop. The dashboard lists them with a caption
per platform (``captions``, written by the social-captions skill; ``caption`` is the fallback for a
platform without one) and one button per platform that opens its upload page; the user marks each platform as
posted, and once every platform is done the video moves to the Trash.

Each video also gets a posting slot (day + slot 1 or 2), two a day, handed out in delivery order, and
each platform has its own peak time for that slot (``TIMES``) to set in its scheduler.
"""

from __future__ import annotations

import ipaddress
import json
import re
import shutil
import subprocess
import time
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

TZ = ZoneInfo("Asia/Ho_Chi_Minh")  # the user's own clock: days in the calendar start here
# Where a video's viewers live: its posting times are their local time. Chinese lessons are for
# Vietnamese learners (Vietnamese captions -> vn); travel reels are for everyone (-> global, user rule
# 2026-10-29). Global has no single clock: slot 1 goes out at Europe's evening peak (US lunch), slot 2
# at the US East evening peak (Asia's next morning), both from the table's evening column.
AUDIENCES = {
    "vn": ("Vietnam", "Asia/Ho_Chi_Minh"),
    "global": ("Everyone (Europe, Americas, Asia)", None),
}
VIETNAMESE = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]", re.IGNORECASE)
# Two videos a day (user rule 2026-10-29). Each platform peaks at its own hours, so each gets its own
# time per slot, Monday first, "slot 1 slot 2" in the audience's local time. Sources and reasoning:
# .claude/skills/social-captions/references/posting-times.md (Buffer 2026 studies of 1.8-14M posts,
# all in the audience's local time; Vietnamese audience data agrees).
#   YouTube Shorts: evenings 19-20h win, Friday 16-18h; slot 1 in the lunch break.
#   TikTok: evenings 19-22h, Sunday 9h is the week's peak, Thursday 13h, Saturday 17h.
#   Facebook Reels: weekday mornings 8-9h and evenings 20-22h; afternoons are worst.
#   Instagram Reels: evenings 18-22h; Wednesday noon, Thursday 9h.
#   X: weekday mornings 9-11h and early afternoon; evenings and Saturday are weakest.
#   Threads: mornings 9-11h and noon; evenings are weakest.
TIMES = {
    "youtube":   ["12:00 20:00", "12:00 20:00", "12:00 19:00", "12:00 19:00", "12:00 17:00", "11:00 19:00", "11:00 19:00"],
    "tiktok":    ["11:00 20:00", "12:00 21:30", "12:00 21:30", "13:00 21:30", "12:00 19:00", "11:30 17:00", "09:00 19:00"],
    "facebook":  ["12:00 21:00", "08:00 20:00", "08:00 20:30", "09:00 20:30", "08:00 20:30", "11:30 22:00", "10:00 20:30"],
    "instagram": ["12:00 19:00", "15:00 19:00", "12:00 18:00", "09:00 20:00", "12:00 21:00", "12:00 21:00", "12:00 21:00"],
    "x":         ["09:00 14:00", "09:00 13:00", "10:00 14:00", "09:00 13:00", "09:00 13:00", "10:00 13:00", "10:00 13:00"],
    "threads":   ["09:00 12:00", "09:00 12:00", "09:00 12:00", "09:00 12:00", "09:00 12:00", "10:00 13:00", "11:00 14:00"],
}  # fmt: skip
SLOT_FOCUS = {1: "Bite-sized (stroke order, word of the day, a quick view)",
              2: "Conversations, common mistakes, quizzes that invite comments"}
GLOBAL_FOCUS = {1: "Europe's evening peak (US lunch)", 2: "US evening peak (Asia's next morning)"}
SLOT_KEY = re.compile(r"^(\d{4}-\d{2}-\d{2})/([12])$")


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


def _audience(entry: dict) -> str:
    """The video's audience: the one the user picked, else guessed from the caption's language."""
    if entry.get("audience") in AUDIENCES:
        return entry["audience"]
    text = " ".join([entry.get("caption", ""), *entry.get("captions", {}).values()])
    return "vn" if VIETNAMESE.search(text) else "global"


def _clock(audience: str, n: int) -> tuple[ZoneInfo, int]:
    """The time zone a slot follows and which column of ``TIMES`` (0 = slot 1, 1 = slot 2) it uses."""
    if audience == "global":
        return ZoneInfo("Europe/London" if n == 1 else "America/New_York"), 1
    return ZoneInfo(AUDIENCES[audience][1]), n - 1


def _slot_times(key: str, audience: str = "vn") -> dict[str, datetime]:
    """Posting time per platform for a slot key "YYYY-MM-DD/1|2", on that day in the audience's time."""
    day, n = SLOT_KEY.match(key).groups()
    d = date.fromisoformat(day)
    tz, col = _clock(audience, int(n))
    out = {}
    for p, week in TIMES.items():
        hh, mm = map(int, week[d.weekday()].split()[col].split(":"))
        out[p] = datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)
    return out


def _slots_from(now: datetime, audience: str):
    """Slot keys from today on whose YouTube time (the slot's anchor) is still ahead of ``now``."""
    d = now.astimezone(TZ).date() - timedelta(days=1)  # an audience west of the user is a day behind
    while True:
        for n in (1, 2):
            key = f"{d.isoformat()}/{n}"
            if _slot_times(key, audience)["youtube"] > now:
                yield key
        d += timedelta(days=1)


def _assign_slots(state: dict, videos: list[Path], now: datetime) -> bool:
    """Give every queued video a slot, oldest delivery first. A slot that passed with nothing posted
    moves to the next free one unless the user picked it. Returns True when the state changed."""
    entries = [(p.name, state.setdefault(p.name, {})) for p in sorted(videos, key=lambda p: p.stat().st_mtime)]
    for _, e in entries:
        if (key := e.get("slot")) and not e.get("posted") and not e.get("slot_pinned") \
                and _slot_times(key, _audience(e))["youtube"] <= now:
            del e["slot"]
    taken = {e["slot"] for _, e in entries if e.get("slot")}
    changed = False
    for _, e in entries:
        if not e.get("slot"):
            e["slot"] = next(k for k in _slots_from(now, _audience(e)) if k not in taken)
            taken.add(e["slot"])
            changed = True
    return changed


def _view(path: Path, entry: dict) -> dict:
    st = path.stat()
    key, audience = entry.get("slot"), _audience(entry)
    return {"name": path.name, "size": st.st_size, "mtime": st.st_mtime,
            "caption": entry.get("caption", ""), "captions": entry.get("captions", {}),
            "posted": entry.get("posted", {}), "slot": key, "focus": (GLOBAL_FOCUS if audience == "global" else SLOT_FOCUS)[int(key[-1])] if key else "",
            "audience": audience,
            "clock": str(_clock(audience, int(key[-1]))[0]).split("/")[-1].replace("_", " ") if key else "",
            "schedule": {p: t.isoformat() for p, t in _slot_times(key, audience).items()} if key else {}}


def _calendar(state: dict, names: set[str], now: datetime, days: int = 7) -> list[dict]:
    """The next ``days`` days of slots with the video booked in each (or None)."""
    booked = {e["slot"]: (n, _audience(e)) for n, e in state.items() if n in names and e.get("slot")}
    start = now.astimezone(TZ).date()
    out = []
    for i in range(days):
        d = start + timedelta(days=i)
        slots = []
        for n in (1, 2):
            key = f"{d.isoformat()}/{n}"
            video, audience = booked.get(key, (None, "vn"))
            slots.append({"key": key, "n": n, "time": _slot_times(key, audience)["youtube"].isoformat(),
                          "focus": SLOT_FOCUS[n], "video": video})
        out.append({"date": d.isoformat(), "slots": slots})
    return out


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
    now = datetime.now(TZ)
    if _assign_slots(state, videos, now):
        _save(svc, state)
    return {
        "folder": str(folder),
        "audiences": [{"id": k, "name": n, "tz": tz} for k, (n, tz) in AUDIENCES.items()],
        "platforms": [{"id": k, "name": n, "url": u, "limit": lim}
                      for k, (n, u, lim) in PLATFORMS.items()],
        "videos": [_view(p, state.get(p.name, {})) for p in videos],
        "calendar": _calendar(state, {p.name for p in videos}, now),
    }


@router.get("/dashboard/posts/{name}/file", include_in_schema=False)
async def post_file(name: str, svc: Services = Depends(get_services)) -> FileResponse:
    return FileResponse(_video(svc, name))


# Plain def (not async): trashing and Finder run subprocesses, so FastAPI runs these in a thread.
@router.post("/dashboard/posts/{name}", include_in_schema=False)
def update_post(name: str, body: dict, svc: Services = Depends(get_services)) -> dict:
    """Set the caption, per-platform ``captions`` (merged in; an empty text drops that platform's
    own caption), the posting ``slot`` ("YYYY-MM-DD/1|2"; a video already there swaps into this
    one's old slot), the ``audience`` (an ``AUDIENCES`` id: times follow its clock), mark a platform posted (or not), or ``{"done": true}`` to trash it now.

    Marking the last platform posted moves the video to the Trash.
    """
    path = _video(svc, name)
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
    if audience := body.get("audience"):
        if audience not in AUDIENCES:
            raise InvalidRequest(f"audience must be one of {', '.join(AUDIENCES)}")
        entry["audience"] = audience
    if slot := body.get("slot"):
        try:
            _slot_times(slot)
        except (TypeError, AttributeError, ValueError):
            raise InvalidRequest("slot must be 'YYYY-MM-DD/1' or 'YYYY-MM-DD/2'") from None
        for other, e in state.items():
            if other != name and e.get("slot") == slot and (svc.settings.post_dir / other).is_file():
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
