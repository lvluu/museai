"""Pick a travel-reel template at random and print the plan for it.

Usage:
  python3 scripts/pick.py --place "Amalfi Coast" --scope region --setting coast [--country italy] [--id ID] [--n 6]

scope   = what the user named: country | region | city | place
setting = main landscape: coast island mountain lake city oldtown nature desert snow
Chooses uniformly among templates whose scope and setting fit, skipping the last 5 used
(history in ~/.config/scenic-drop-reel/history.json), and prints JSON: the template plus, per
shot, the camera move and light to put in each brief, the transition after it, and the music
tags/lyrics with the place filled in. --id forces a template; --list prints all ids.
"""
import argparse
import json
import random
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
HISTORY = Path.home() / ".config/scenic-drop-reel/history.json"


def cycle(seq, i):
    return seq[i % len(seq)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--place", default="")
    ap.add_argument("--scope", choices=["country", "region", "city", "place"], default="place")
    ap.add_argument("--setting", default="any")
    ap.add_argument("--country", default="", help="country/region key for local-flavour music")
    ap.add_argument("--id", help="use this template")
    ap.add_argument("--n", type=int, help="override shot count")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    data = json.loads((SKILL / "templates.json").read_text())
    temps = data["templates"]
    if a.list:
        for t in temps:
            print(f"{t['id']:20} {t['name']:26} {','.join(t['scope']):28} {','.join(t['setting'])}")
        return

    history = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    if a.id:
        t = next((t for t in temps if t["id"] == a.id), None) or sys.exit(f"no template {a.id}")
    else:
        fit = [t for t in temps if a.scope in t["scope"]
               and ("any" in t["setting"] or a.setting in t["setting"] or a.setting == "any")]
        fresh = [t for t in fit if t["id"] not in history[-5:]] or fit
        t = random.choice(fresh)
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps((history + [t["id"]])[-50:]))

    n = a.n or t["shots"]
    place = a.place
    local = data["local_sounds"].get(a.country.lower() or place.lower(), data["local_sounds"]["default"])
    music = dict(t["music"])
    music["tags"] = music["tags"].replace("{local}", local)
    music["lyrics"] = music["lyrics"].replace("{place}", place)
    shots = []
    for i in range(n):
        light = cycle(t["lights"], i) if "lights" in t else t["light"]
        shots.append({
            "shot": i + 1,
            "beats": cycle(t["pattern"], i),
            "move": data["moves"][cycle(t["moves"], i)],
            "light": data["lights"].get(light, light),
            "transition_after": cycle(t["transitions"], i) if i < n - 1 else None,
            "time_label": cycle(t["times"], i) if "times" in t else None,
        })
    intro = dict(t["intro"])
    if "text" in intro:
        intro["text"] = intro["text"].replace("{place}", place).replace("{PLACE}", place.upper()).replace("{n}", str(n))
    print(json.dumps({"template": t["id"], "name": t["name"], "vibe": t["vibe"], "place": place,
                      "intro": intro, "text": t["text"], "grade": t["grade"], "target": t["target"],
                      "ramp": t["ramp"], "fast": "fpv" in t["moves"], "music": music, "shots": shots}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
