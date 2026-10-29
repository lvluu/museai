#!/usr/bin/env python3
"""Registry of every place shot rendered through museai, so a repeat request gets new views.

  shots.py check  --place "Ilulissat" [--country Greenland]
  shots.py record --place "Ilulissat Icefjord" --country Greenland --skill scenic-drop-reel \
                  --template winter-wonder --video ~/Desktop/reel.mp4 --shots shots.json
  shots.py list

shots.json: [{"subject": "...", "move": "...", "light": "..."}, ...] in reel order.
Store: ~/.config/museai/shots.json (one entry per delivered video). check prints every earlier
video of the same place (fuzzy name match, or same country with --country-wide) with its subjects,
moves, light and template, and exits 1 when there are any, 0 when the place is new.
"""
import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

STORE = Path.home() / ".config/museai/shots.json"
# words that name a kind of place, not the place itself: "Lake Bled" and "Lake Como" must not match
GENERIC = {
    "lake", "national", "park", "city", "old", "town", "island", "islands", "beach", "bay", "fjord",
    "icefjord", "mount", "mountain", "mountains", "valley", "river", "falls", "waterfall", "coast",
    "cape", "glacier", "the", "of", "de", "la", "le", "di", "del", "and", "region", "village", "peninsula",
}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def keys(place):
    return {w for w in norm(place).split() if len(w) >= 3 and w not in GENERIC}


def load():
    return json.loads(STORE.read_text()) if STORE.exists() else []


def same_place(entry, place, country, country_wide):
    a, b = norm(entry["place"]), norm(place)
    if a == b or keys(entry["place"]) & keys(place):
        return True
    return country_wide and country and norm(entry.get("country", "")) == norm(country)


def show(e):
    print(f"- {e['date']}  {e['place']} ({e.get('country', '?')})  skill={e['skill']}"
          f"  template={e.get('template') or '-'}  video={e.get('video') or '-'}")
    for i, s in enumerate(e["shots"], 1):
        print(f"    {i}. {s['subject']}")
        print(f"       move: {s.get('move', '-')} | light: {s.get('light', '-')}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--place", required=True)
    c.add_argument("--country")
    c.add_argument("--country-wide", action="store_true", help="also list other places in the country")
    r = sub.add_parser("record")
    r.add_argument("--place", required=True)
    r.add_argument("--country", default="")
    r.add_argument("--skill", required=True)
    r.add_argument("--template", default="")
    r.add_argument("--video", default="")
    r.add_argument("--shots", required=True, help="JSON file: list of {subject, move, light}")
    sub.add_parser("list")
    a = ap.parse_args()

    entries = load()
    if a.cmd == "list":
        for e in entries:
            show(e)
        return 0
    if a.cmd == "record":
        shots = json.loads(Path(a.shots).expanduser().read_text())
        if not shots or not all(s.get("subject") for s in shots):
            sys.exit("every shot needs a subject")
        entries.append({"date": date.today().isoformat(), "place": a.place, "country": a.country,
                        "skill": a.skill, "template": a.template, "video": a.video, "shots": shots})
        STORE.parent.mkdir(parents=True, exist_ok=True)
        STORE.write_text(json.dumps(entries, indent=1, ensure_ascii=False))
        print(f"recorded {len(shots)} shots of {a.place} ({len(entries)} videos in {STORE})")
        return 0
    hits = [e for e in entries if same_place(e, a.place, a.country, a.country_wide)]
    if not hits:
        print(f"NEW PLACE: no earlier shots of {a.place}")
        return 0
    where = f"{a.place} or elsewhere in {a.country}" if a.country_wide else a.place
    print(f"ALREADY SHOT: {len(hits)} earlier video(s) of {where}. Plan different subjects, "
          "angles, moves, light/season and template; tell the user before rendering.")
    for e in hits:
        show(e)
    return 1


if __name__ == "__main__":
    sys.exit(main())
