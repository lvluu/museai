"""Idea bank + history for healing videos, so no video repeats an earlier one.

Bank: ../ideas.json (1000 ideas, scripts/gen_ideas.py). History: ~/.config/museai/healing-history.json,
one entry per DELIVERED video (idea id or custom idea, title, home, season, task, animal, shots, video, date).

  python3 scripts/ideas.py next [--season autumn|now] [--home Kyoto] [--animal cat] [--no-animal] [--n 3]
  python3 scripts/ideas.py show hv-0042
  python3 scripts/ideas.py check --title "..." --home "..." --season autumn --task "..." [--animal cat]
  python3 scripts/ideas.py record hv-0042 --video ~/Desktop/healing-x.mp4 [--shots shots.json]
  python3 scripts/ideas.py record custom --title "..." --home "..." --season ... --task ... --video ...
  python3 scripts/ideas.py list [--last 20]
  python3 scripts/ideas.py stats

next: the first unused ideas (bank order) that also differ from the last 10 videos in home and task and
from the last 3 in animal and caption, so a run of posts never looks samey. "--season now" = the month's
season (northern hemisphere). check exits 1 (DUPLICATE) when an earlier video has the same home +
season + task, or the same task + animal in the same home; 2 (SIMILAR) on the same home or task in
the last 10.
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
BANK = SKILL / "ideas.json"
HIST = Path.home() / ".config/museai/healing-history.json"
MONTH_SEASON = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
                6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def norm(x):
    return (x or "").strip().lower()


def verdict(idea, hist):
    """(code, reason): 0 fresh, 1 duplicate, 2 too similar to recent videos."""
    for h in hist:
        if h.get("id") and h["id"] == idea.get("id"):
            return 1, f"idea {h['id']} already used ({h['date']}, {h['video']})"
        same_home = norm(h["home"]) == norm(idea["home"])
        if same_home and norm(h["season"]) == norm(idea["season"]) and norm(h["task"]) == norm(idea["task"]):
            return 1, f"same home + season + task as {h['date']} {h['title']}"
        if same_home and norm(h["task"]) == norm(idea["task"]) and norm(h.get("animal")) == norm(idea.get("animal")):
            return 1, f"same home + task + animal as {h['date']} {h['title']}"
    for h in hist[-10:]:
        if norm(h["home"]) == norm(idea["home"]):
            return 2, f"home used in the last 10 videos ({h['date']} {h['title']})"
        if norm(h["task"]) == norm(idea["task"]):
            return 2, f"task used in the last 10 videos ({h['date']} {h['title']})"
    for h in hist[-3:]:
        if idea.get("animal") and norm(h.get("animal")) == norm(idea["animal"]):
            return 2, f"animal used in the last 3 videos ({h['date']} {h['title']})"
        if idea.get("caption") and norm(h.get("caption")) == norm(idea["caption"]):
            return 2, f"caption used in the last 3 videos ({h['date']} {h['title']})"
    return 0, "fresh"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("next")
    n.add_argument("--season")
    n.add_argument("--home")
    n.add_argument("--animal")
    n.add_argument("--no-animal", action="store_true")
    n.add_argument("--n", type=int, default=1)
    sub.add_parser("show").add_argument("id")
    for name in ("check", "record"):
        p = sub.add_parser(name)
        if name == "record":
            p.add_argument("id", help="hv-NNNN or 'custom'")
            p.add_argument("--video", required=True)
            p.add_argument("--shots", help="JSON list of the shot briefs actually used")
        for f in ("title", "home", "season", "task", "animal", "caption"):
            p.add_argument(f"--{f}")
    sub.add_parser("list").add_argument("--last", type=int, default=20)
    sub.add_parser("stats")
    a = ap.parse_args()

    bank = load(BANK, [])
    by_id = {i["id"]: i for i in bank}
    hist = load(HIST, [])

    if a.cmd == "next":
        season = MONTH_SEASON[datetime.date.today().month] if a.season == "now" else a.season
        out = []
        for idea in bank:
            if season and norm(idea["season"]) != norm(season):
                continue
            if a.home and norm(a.home) not in norm(idea["home"]):
                continue
            if a.animal and norm(a.animal) not in norm(idea.get("animal")):
                continue
            if a.no_animal and idea.get("animal"):
                continue
            if verdict(idea, hist)[0] == 0:
                out.append(idea)
            if len(out) == a.n:
                break
        if not out:
            sys.exit("no fresh idea matches; loosen the filters or add homes/tasks to gen_ideas.py")
        print(json.dumps(out if a.n > 1 else out[0], ensure_ascii=False, indent=1))
    elif a.cmd == "show":
        print(json.dumps(by_id.get(a.id) or sys.exit(f"no idea {a.id}"), ensure_ascii=False, indent=1))
    elif a.cmd == "check":
        code, why = verdict({k: getattr(a, k) for k in ("title", "home", "season", "task", "animal", "caption")}, hist)
        print(["FRESH", "DUPLICATE", "SIMILAR"][code] + f": {why}")
        sys.exit(code)
    elif a.cmd == "record":
        if a.id == "custom":
            idea = {k: getattr(a, k) for k in ("title", "home", "season", "task", "animal", "caption")}
            missing = [k for k in ("title", "home", "season", "task") if not idea[k]]
            if missing:
                sys.exit(f"custom record needs --{' --'.join(missing)}")
            idea["id"] = None
        else:
            idea = dict(by_id.get(a.id) or sys.exit(f"no idea {a.id}"))
        code, why = verdict(idea, hist)
        if code == 1:
            print(f"warning: recording a duplicate ({why})", file=sys.stderr)
        entry = {k: idea.get(k) for k in ("id", "title", "home", "season", "task", "animal", "caption")}
        entry["shots"] = json.loads(Path(a.shots).read_text()) if a.shots else idea.get("shots", [])
        entry["video"] = str(Path(a.video).expanduser().resolve())
        entry["date"] = datetime.date.today().isoformat()
        hist.append(entry)
        HIST.parent.mkdir(parents=True, exist_ok=True)
        HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=1) + "\n")
        print(f"recorded {entry['id'] or 'custom'}: {entry['title']} ({len(hist)} videos in history)")
    elif a.cmd == "list":
        for h in hist[-a.last:]:
            print(f"{h['date']}  {h['id'] or 'custom':9}  {h['title']}  → {h['video']}")
        if not hist:
            print("no videos yet")
    elif a.cmd == "stats":
        used = {h["id"] for h in hist if h.get("id")}
        print(f"{len(hist)} videos delivered, {len(used)}/{len(bank)} bank ideas used, "
              f"{sum(verdict(i, hist)[0] == 0 for i in bank)} fresh now")


if __name__ == "__main__":
    main()
