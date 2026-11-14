#!/usr/bin/env python3
"""Story seeds for long-form healing days, with a history so no story, place or dish comes back too soon.

  stories.py next [--season autumn] [--n 3]   fresh seeds (skips used ids, a place or dish of the last 5 videos)
  stories.py show lf-001
  stories.py list                             what was delivered
  stories.py record lf-001 --video ~/Desktop/healing-<slug>.mp4 [--title "..."]

Seeds live in ../stories/seeds.json; a told story is kept as ../stories/<slug>.json (the full story.json).
History: ~/.config/museai/healing-longform-history.json (one entry per DELIVERED video).
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

SEEDS = Path(__file__).resolve().parent.parent / "stories" / "seeds.json"
HISTORY = Path.home() / ".config" / "museai" / "healing-longform-history.json"
SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring", 6: "summer", 7: "summer",
           8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}


def history():
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def seeds():
    return json.loads(SEEDS.read_text())


def fresh(season=None):
    h = history()
    used = {e["id"] for e in h}
    recent = h[-5:]
    places = {e.get("place") for e in recent}
    dishes = {d for e in recent for d in e.get("dishes", [])}
    out = []
    for s in seeds():
        if s["id"] in used or s["place"] in places or dishes & set(s["dishes"]):
            continue
        if season and season not in s["seasons"]:
            continue
        out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["next", "show", "list", "record"])
    ap.add_argument("id", nargs="?")
    ap.add_argument("--season")
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--video")
    ap.add_argument("--title")
    a = ap.parse_args()
    if a.cmd == "next":
        season = SEASONS[datetime.date.today().month] if a.season == "now" else a.season
        got = fresh(season)
        if not got:
            sys.exit("no fresh seed: add seeds at the end of stories/seeds.json")
        print(json.dumps(got[: a.n] if a.n > 1 else got[0], indent=1, ensure_ascii=False))
    elif a.cmd == "show":
        print(json.dumps(next(s for s in seeds() if s["id"] == a.id), indent=1, ensure_ascii=False))
    elif a.cmd == "list":
        for e in history():
            print(f"{e['date']}  {e['id']}  {e.get('title', '')}  ({e.get('place')})")
    else:
        s = next(s for s in seeds() if s["id"] == a.id)
        h = history()
        h.append({"id": s["id"], "title": a.title or s["title"], "place": s["place"], "dishes": s["dishes"],
                  "video": a.video, "date": datetime.date.today().isoformat()})
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text(json.dumps(h, indent=1, ensure_ascii=False) + "\n")
        print(f"recorded {s['id']}")


if __name__ == "__main__":
    main()
