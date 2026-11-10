"""Muse Hands dashboard text: what is left to post, per channel and platform, built for a phone.

Look and content are editable in ``data/hands.json`` under ``"dashboard"`` (all keys optional)::

    {"dashboard": {"title": "Posting",
                   "platforms": ["youtube", "tiktok", "facebook", "instagram"],   # columns, in order
                   "channels": ["chinese", "travel"],                              # only these, in order
                   "icons": {"youtube": "▶️", "tiktok": "🎵", "facebook": "📘", "instagram": "📸"},
                   "hide_empty": false}}                                           # hide channels with 0 left
"""

from __future__ import annotations

import json
from datetime import datetime

from ...services.container import Services
from ...services.publishers import AUTO_PLATFORMS
from . import posting

ICONS = {"youtube": "▶️", "tiktok": "🎵", "facebook": "📘", "instagram": "📸"}
BAD = ("error", "missed", "needs_account")
Keyboard = dict


def config(svc: Services) -> dict:
    try:
        own = json.loads((svc.settings.data_dir / "hands.json").read_text()).get("dashboard") or {}
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        own = {}
    platforms = [p for p in own.get("platforms") or AUTO_PLATFORMS if p in AUTO_PLATFORMS]
    return {"title": own.get("title") or "Posting", "platforms": platforms or list(AUTO_PLATFORMS),
            "channels": own.get("channels"), "icons": {**ICONS, **(own.get("icons") or {})},
            "hide_empty": bool(own.get("hide_empty"))}


def pending(video: dict, platforms: list[str]) -> list[dict]:
    """The platforms of ``video`` that still have to be posted (shown columns only)."""
    return [p for p in video["platforms"] if p["id"] in platforms and p["can_post"] and p["state"] != "manual"]


def channels(data: dict, cfg: dict) -> list[tuple[str, str, list[dict]]]:
    """(id, name, videos) per channel in dashboard order."""
    names: dict[str, str] = {}
    groups: dict[str, list[dict]] = {}
    for v in data["videos"]:
        names[v["channel_id"]] = v["channel"]
        groups.setdefault(v["channel_id"], []).append(v)
    order = cfg["channels"] or list(posting.CHANNELS)
    rows = []
    for cid in order:
        if cid not in posting.CHANNELS:
            continue
        videos = [v for v in groups.get(cid, []) if pending(v, cfg["platforms"])]
        if videos or not cfg["hide_empty"]:
            rows.append((cid, posting.CHANNELS[cid][0], videos))
    return rows


def _when(iso: str | None) -> str:
    return datetime.fromisoformat(iso).astimezone(posting.TZ).strftime("%a %H:%M") if iso else ""


def status(data: dict, cfg: dict) -> tuple[str, Keyboard]:
    rows = channels(data, cfg)
    left = sum(len(v) for _, _, v in rows)
    lines = [f"📊 {cfg['title']} · {left} video{'s' * (left != 1)} left"]
    if data["paused"]:
        lines.append("⏸ Auto-posting paused")
    nxt = min((p["time"] for _, _, vs in rows for v in vs for p in pending(v, cfg["platforms"]) if p["time"]), default=None)
    if nxt:
        lines.append(f"Next: {_when(nxt)}")
    keyboard = []
    for cid, name, videos in rows:
        if not videos:
            lines.append(f"\n{name} · all posted ✅")
            continue
        lines.append(f"\n{name} · {len(videos)} left")
        cells = []
        for pid in cfg["platforms"]:
            todo = [p for v in videos for p in pending(v, [pid])]
            if todo:
                bad = sum(p["state"] in BAD for p in todo)
                cells.append(f"{cfg['icons'][pid]} {len(todo)}" + (f"⚠️{bad}" if bad else ""))
        lines.append("  " + "   ".join(cells))
        keyboard.append([{"text": f"{name} · {len(videos)} ›", "callback_data": f"ch:{cid}"}])
    if not left:
        lines.append("\n📭 Nothing left to post." + (f"\nWatching: {data['folder']}" if data.get("folder") else ""))
    else:
        keyboard.append([{"text": "✅ Approve all", "callback_data": "apprq:all:all"}])
    keyboard.append([{"text": "🔄 Refresh", "callback_data": "status"}])
    return "\n".join(lines), {"inline_keyboard": keyboard}


def channel(data: dict, cid: str, cfg: dict) -> tuple[str, Keyboard]:
    name, videos = next(((n, v) for c, n, v in channels(data, cfg) if c == cid), (cid, []))
    lines = [f"{name} · {len(videos)} left"]
    keyboard = []
    for i, v in enumerate(videos, 1):
        lines.append(f"\n{i}. {v['title'] or v['name']}")
        for p in pending(v, cfg["platforms"]):
            icon = {"retry": "🔁", "error": "❌", "missed": "⚠️", "needs_account": "🔌", "posting": "⏳",
                    "paused": "⏸", "waiting": "✍️"}.get(p["state"], "🕒")
            lines.append(f"  {icon} {p['name']} {_when(p['time'])}".rstrip() + (f" — {p['error'][:70]}" if p["error"] else ""))
        row = [{"text": f"{i} ▸ {cfg['icons'][p['id']]} {p['name'].split()[0]}", "callback_data": f"post:{v['id']}:{p['id']}"}
               for p in pending(v, cfg["platforms"]) if v["planned"] and p["state"] != "posting"]
        if row:
            keyboard.append(row)
        if not v["planned"]:
            lines.append("  ✋ not auto-planned: plan it on the dashboard")
    if videos:
        keyboard.append([{"text": f"✅ Approve {name}", "callback_data": f"apprq:{cid}:all"}])
    keyboard.append([{"text": "‹ Back", "callback_data": "status"}])
    return "\n".join(lines), {"inline_keyboard": keyboard}


def targets(data: dict, cid: str, platform: str, cfg: dict) -> list[tuple[str, str]]:
    """(video name, platform) pairs an approve of ``cid`` (or "all") x ``platform`` ("all") would post."""
    out = []
    for c, _, videos in channels(data, cfg):
        if cid in ("all", c):
            for v in videos:
                if v["planned"]:
                    out += [(v["name"], p["id"]) for p in pending(v, cfg["platforms"])
                            if platform in ("all", p["id"]) and p["state"] != "posting"]
    return out


def confirm(count: int, cid: str, platform: str) -> tuple[str, Keyboard]:
    what = "everything" if cid == "all" else cid
    where = "" if platform == "all" else f" on {platform}"
    return (f"Post {count} job{'s' * (count != 1)} now ({what}{where})?",
            {"inline_keyboard": [[{"text": f"✅ Yes, post {count}", "callback_data": f"appr:{cid}:{platform}"},
                                  {"text": "✖ No", "callback_data": "status"}]]})


def queue(data: dict) -> str:
    """/postq: the auto-poster at a glance."""
    counts: dict[str, int] = {}
    for v in data["videos"]:
        for p in v["platforms"]:
            if p["state"] != "manual":
                counts[p["state"]] = counts.get(p["state"], 0) + 1
    icons = {"scheduled": "🕒", "posting": "⏳", "retry": "🔁", "waiting": "✍️", "needs_account": "🔌",
             "missed": "⚠️", "error": "❌", "posted": "✅", "paused": "⏸"}
    lines = ["⏸ Auto-posting paused" if data["paused"] else "▶️ Auto-posting running"]
    lines += [f"{icons.get(k, '•')} {k.replace('_', ' ')}: {n}" for k, n in sorted(counts.items())]
    return "\n".join(lines + ([] if counts else ["Queue empty."]))
