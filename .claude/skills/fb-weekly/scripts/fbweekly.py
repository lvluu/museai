#!/usr/bin/env python3
"""Plan and track what each Facebook Page must publish to finish Meta's creator weekly tasks.

The weekly tasks (Creator Dashboard → Status: "Create 16 new public posts, 14 reels, 7 stories,
reply to 5 comments, comment on 5 public posts") change per Page and week. The agent reads them,
`record`s them here, and `plan` says what to publish today so the week ends at 100 %. Content comes
from what the channel already makes: frames of its published reels become photo posts and stories,
backlog reels (booked beyond Business Suite's 28-day window) are published now as live reels.

State: ~/.config/museai/fb-weekly/ (status.jsonl, actions.jsonl, assets/). Stdlib only.
"""

from __future__ import annotations

import argparse
import functools
import json
import math
import os
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PAGES_FILE = HERE / "pages.json"
STATE = Path(os.environ.get("FBWEEKLY_STATE", Path.home() / ".config" / "museai" / "fb-weekly"))
QUEUE = Path(os.environ.get("FBWEEKLY_QUEUE", Path.home() / ".local" / "state" / "postq" / "queue"))
MUSEAI_BASE = os.environ.get("MUSEAI_BASE", "http://127.0.0.1:18610")
TZ = timezone(timedelta(hours=7))  # the Pages' own clock (Asia/Ho_Chi_Minh, no DST)
KINDS = ("posts", "reels", "stories", "replies", "comments")
DEFAULT_TARGETS = {"posts": 16, "reels": 14, "stories": 7, "replies": 5, "comments": 5}
META_AHEAD = timedelta(days=28)  # postq leaves Meta slots further out than this off Business Suite
# What one logged action adds to each weekly task. A reel published from the Page also counts as a
# public post, and its "Share to story" toggle (on by default for Pages) makes a story.
ACTION_COUNTS = {
    "reel": {"reels": 1, "posts": 1, "stories": 1},
    "photo": {"posts": 1},
    "story": {"stories": 1},
    "reply": {"replies": 1},
    "comment": {"comments": 1},
}


def now() -> datetime:
    if fake := os.environ.get("FBWEEKLY_NOW"):
        return datetime.fromisoformat(fake).astimezone(TZ)
    return datetime.now(TZ)


def load_pages() -> dict:
    return json.loads(PAGES_FILE.read_text(encoding="utf-8"))


def page_of(name: str) -> dict:
    for p in load_pages()["pages"]:
        if name.lower() in (p["name"].lower(), p["channel"], p["series"].lower(), p["id"]):
            return p
    sys.exit(f"unknown page '{name}': see pages.json")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def week_start(day: date) -> date:
    """Meta's weekly tasks run Sunday to Saturday (seen: 'Week of 22 Nov - 28 Nov', 22 Nov 2026 a Sunday)."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_frac(s: str) -> tuple[int, int]:
    m = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", s)
    if not m:
        raise argparse.ArgumentTypeError(f"expected done/target like 3/16, got '{s}'")
    return int(m.group(1)), int(m.group(2))


def latest_status(page: str, ws: date) -> dict | None:
    rows = [
        r
        for r in read_jsonl(STATE / "status.jsonl")
        if r["page"] == page and r["week"] == ws.isoformat()
    ]
    return rows[-1] if rows else None


def actions_since(page: str, since: str) -> list[dict]:
    return [a for a in read_jsonl(STATE / "actions.jsonl") if a["page"] == page and a["at"] > since]


def queue_items(account: str) -> list[dict]:
    """postq Meta items (pending and done) of one Page."""
    return [d for d in _meta_items() if d.get("account") == account]


@functools.lru_cache(maxsize=1)
def _meta_items() -> list[dict]:
    out = []
    for f in list(QUEUE.glob("*.json")) + list((QUEUE / "done").glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (
            d.get("platform") == "meta"
            and d.get("status") != "superseded"
            and "facebook" in (d.get("targets") or ["facebook"])
            and d.get("schedule_at")
        ):
            d["_dir"] = str(f.parent)
            out.append(d)
    return out


def scheduled_between(account: str, start: datetime, end: datetime) -> int:
    n = 0
    for d in queue_items(account):
        at = datetime.fromisoformat(d["schedule_at"].replace("Z", "+00:00"))
        if start < at <= end:
            n += 1
    return n


def plan_page(page: dict, cfg: dict, t: datetime) -> dict:
    today = t.date()
    ws = week_start(today)
    we = ws + timedelta(days=6)
    days_left = (we - today).days + 1
    snap = latest_status(page["name"], ws)
    tasks = (
        {k: tuple(snap["tasks"][k]) for k in KINDS}
        if snap
        else {k: (0, DEFAULT_TARGETS[k]) for k in KINDS}
    )
    since = snap["at"] if snap else datetime.combine(ws, datetime.min.time(), TZ).isoformat()
    done = {k: tasks[k][0] for k in KINDS}
    logged_today = {k: 0 for k in KINDS}
    for a in actions_since(page["name"], since):
        for k, n in ACTION_COUNTS.get(a["kind"], {}).items():
            done[k] += n
            if a["at"][:10] == today.isoformat():
                logged_today[k] += n
    sched = 0
    if cfg.get("scheduled_counts"):
        end = datetime.combine(we + timedelta(days=1), datetime.min.time(), TZ)
        sched = scheduled_between(page["name"], t, end)
        for k in ("reels", "posts", "stories"):
            done[k] += sched
    remaining = {k: max(0, tasks[k][1] - done[k]) for k in KINDS}
    # Spread over the days left; what was already logged today counts toward today's share.
    share = {
        k: max(0, math.ceil((remaining[k] + logged_today[k]) / days_left) - logged_today[k])
        for k in KINDS
    }
    reel_n = min(share["reels"], remaining["reels"])
    todo = {
        "reel": reel_n,
        "photo": max(0, min(share["posts"], remaining["posts"]) - reel_n),
        "story": max(0, min(share["stories"], remaining["stories"]) - reel_n),
        "reply": min(share["replies"], remaining["replies"]),
        "comment": min(share["comments"], remaining["comments"]),
    }
    return {
        "page": page["name"],
        "week": f"{ws.isoformat()}..{we.isoformat()}",
        "days_left": days_left,
        "status_read": bool(snap and snap["at"][:10] == today.isoformat()),
        "status_at": snap["at"] if snap else None,
        "tasks": {k: list(tasks[k]) for k in KINDS},
        "counted": done,
        "remaining": remaining,
        "scheduled_reels_counted": sched,
        "today": todo,
    }


def cmd_plan(a) -> None:
    cfg = load_pages()
    pages = [page_of(a.page)] if a.page else [p for p in cfg["pages"] if p.get("id")]
    plans = [plan_page(p, cfg, now()) for p in pages]
    if a.json:
        print(json.dumps(plans, ensure_ascii=False, indent=2))
        return
    for p in plans:
        flag = "" if p["status_read"] else "  (status not read today: read it first, then `record`)"
        print(f"{p['page']}  week {p['week']}  {p['days_left']} days left{flag}")
        print("  tasks   " + "  ".join(f"{k} {p['counted'][k]}/{p['tasks'][k][1]}" for k in KINDS))
        print("  today   " + "  ".join(f"{k} {n}" for k, n in p["today"].items()))


def cmd_record(a) -> None:
    page = page_of(a.page)
    t = now()
    ws = date.fromisoformat(a.week_start) if a.week_start else week_start(t.date())
    tasks = {k: list(getattr(a, k)) for k in KINDS}
    append_jsonl(
        STATE / "status.jsonl",
        {
            "at": t.isoformat(),
            "page": page["name"],
            "week": ws.isoformat(),
            "focus": a.focus or "",
            "tasks": tasks,
        },
    )
    print(
        f"recorded {page['name']} week {ws}: "
        + "  ".join(f"{k} {v[0]}/{v[1]}" for k, v in tasks.items())
    )


def cmd_log(a) -> None:
    page = page_of(a.page)
    append_jsonl(
        STATE / "actions.jsonl",
        {
            "at": now().isoformat(),
            "page": page["name"],
            "kind": a.kind,
            "ref": a.ref or "",
            "text": a.text or "",
        },
    )
    print(f"logged {a.kind} for {page['name']}")


def used(kind: str) -> set[str]:
    return {
        a["ref"] for a in read_jsonl(STATE / "actions.jsonl") if a["kind"] == kind and a.get("ref")
    }


def duration(video: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return float(out.strip() or 0)


def cmd_assets(a) -> None:
    """Clean frames of the Page's already-published reels, for photo posts or stories, never reused."""
    page = page_of(a.page)
    t = now()
    taken = used("photo") | used("story")
    items = sorted(
        (
            d
            for d in queue_items(page["name"])
            if datetime.fromisoformat(d["schedule_at"].replace("Z", "+00:00")) <= t
            and (Path(d["_dir"]) / (d.get("video") or {}).get("file", "")).is_file()
        ),
        key=lambda d: d["schedule_at"],
        reverse=True,
    )
    out_dir = STATE / "assets" / slug(page["name"])
    out_dir.mkdir(parents=True, exist_ok=True)
    picked = []
    for d in items:
        if len(picked) >= a.n:
            break
        for frac in (0.45, 0.7, 0.25):  # three distinct frames per reel before it counts as used
            ref = f"{d['id']}@{frac}"
            if ref in taken or len(picked) >= a.n:
                continue
            video = Path(d["_dir"]) / d["video"]["file"]
            jpg = out_dir / f"{d['id']}-{int(frac * 100)}.jpg"
            if not jpg.is_file():
                subprocess.run(
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-y",
                        "-ss",
                        f"{duration(video) * frac:.2f}",
                        "-i",
                        str(video),
                        "-frames:v",
                        "1",
                        "-q:v",
                        "2",
                        str(jpg),
                    ],
                    check=True,
                )
            picked.append(
                {
                    "ref": ref,
                    "image": str(jpg),
                    "title": d.get("title", ""),
                    "reel_caption": (d.get("caption") or "")[:600],
                    "published": d["schedule_at"],
                }
            )
            taken.add(ref)
    print(json.dumps(picked, ensure_ascii=False, indent=2))
    if len(picked) < a.n:
        print(
            f"only {len(picked)} of {a.n}: render stills with muse (/v1/images/generations) in the channel's look",
            file=sys.stderr,
        )


def fetch_dashboard() -> dict:
    return json.load(urllib.request.urlopen(f"{MUSEAI_BASE}/dashboard/posts", timeout=60))


def backlog(page: dict, feed: dict, t: datetime, n: int) -> list[dict]:
    """Reels booked beyond Business Suite's window, Facebook not yet posted: safe to publish now
    without a duplicate (postq has not scheduled them). Furthest slots first, so the near-term
    calendar stays as booked."""
    out = []
    taken = used("reel")
    for v in feed.get("videos", []):
        at = (v.get("schedule") or {}).get("facebook")
        if (
            v.get("channel") != page["channel"]
            or "facebook" not in (v.get("open") or [])
            or not at
            or not v.get("folder")
            or v["name"] in taken
        ):
            continue
        if datetime.fromisoformat(at) - t <= META_AHEAD:
            continue
        caps = v.get("captions") or {}
        out.append(
            {
                "name": v["name"],
                "video": str(Path(v["folder"]) / v["name"]),
                "slot": v["slot"],
                "caption": caps.get("facebook") or v.get("caption") or "",
            }
        )
    out.sort(key=lambda x: x["slot"], reverse=True)
    return out[:n]


def cmd_backlog(a) -> None:
    print(
        json.dumps(
            backlog(page_of(a.page), fetch_dashboard(), now(), a.n), ensure_ascii=False, indent=2
        )
    )


def cmd_mark_posted(a) -> None:
    """Tick Facebook on the dashboard so postq never schedules this reel again."""
    req = urllib.request.Request(
        f"{MUSEAI_BASE}/dashboard/posts/{urllib.request.quote(a.name)}",
        method="POST",
        data=json.dumps({"posted": {"facebook": True}}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"marked facebook posted: {a.name} ({r.status})")


def cmd_learn(_a) -> None:
    """Compare each week's last reading with what was published, to settle `scheduled_counts`."""
    cfg = load_pages()
    for p in cfg["pages"]:
        weeks = {}
        for r in read_jsonl(STATE / "status.jsonl"):
            if r["page"] == p["name"]:
                weeks[r["week"]] = r
        for wk, r in sorted(weeks.items()):
            ws = datetime.combine(date.fromisoformat(wk), datetime.min.time(), TZ)
            at = datetime.fromisoformat(r["at"])
            live = sum(
                1
                for x in read_jsonl(STATE / "actions.jsonl")
                if x["page"] == p["name"]
                and x["kind"] == "reel"
                and ws.isoformat() <= x["at"] <= r["at"]
            )
            sched = scheduled_between(p["name"], ws, at - timedelta(hours=1))
            print(
                f"{p['name']} week {wk} read {r['at'][:16]}: reels counted {r['tasks']['reels'][0]}, "
                f"published live {live}, scheduled published {sched}"
            )
    print(
        f"scheduled_counts now {cfg.get('scheduled_counts')}: true only if counted ≈ live + scheduled"
    )


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="what each Page publishes today")
    p.add_argument("--page")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("record", help="save the weekly tasks read from the Creator Dashboard")
    p.add_argument("page")
    for k in KINDS:
        p.add_argument(f"--{k}", type=parse_frac, required=True, metavar="DONE/TARGET")
    p.add_argument("--focus")
    p.add_argument("--week-start")
    p.set_defaults(fn=cmd_record)
    p = sub.add_parser("log", help="log one published item or comment")
    p.add_argument("page")
    p.add_argument("kind", choices=sorted(ACTION_COUNTS))
    p.add_argument("--ref", help="asset ref / video name / comment id, so nothing is reused")
    p.add_argument("--text")
    p.set_defaults(fn=cmd_log)
    p = sub.add_parser("assets", help="fresh frames of published reels for photo posts and stories")
    p.add_argument("page")
    p.add_argument("--n", type=int, default=2)
    p.set_defaults(fn=cmd_assets)
    p = sub.add_parser("backlog", help="booked reels safe to publish live now")
    p.add_argument("page")
    p.add_argument("--n", type=int, default=2)
    p.set_defaults(fn=cmd_backlog)
    p = sub.add_parser("mark-posted", help="tick Facebook on the dashboard after a live reel")
    p.add_argument("name")
    p.set_defaults(fn=cmd_mark_posted)
    p = sub.add_parser(
        "learn", help="do scheduled posts count? compare readings with what was published"
    )
    p.set_defaults(fn=cmd_learn)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
