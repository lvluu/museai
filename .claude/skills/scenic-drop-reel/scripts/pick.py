"""Pick a travel-reel template at random and print the plan for it.

Usage:
  python3 scripts/pick.py --place "Amalfi Coast" --scope region --setting coast [--country italy] [--id ID] [--n 6]

scope   = what the user named: country | region | city | place
setting = main landscape: coast island mountain lake city oldtown nature desert snow
Chooses uniformly among templates whose scope and setting fit, skipping the last 5 used
(history in ~/.config/scenic-drop-reel/history.json), and prints JSON: the template plus, per
shot, the camera move and light to put in each brief, the transition after it, and the music
tags/lyrics with the place filled in. --id forces a template; --list prints all ids.

Length is random per reel, in a range that suits the template's pace (a template may set
"length": [min, max] seconds): slow dreamy templates run longer and may hold each shot 1.5-2x
the pattern, fast cut templates stay short. The shot count follows from the length. --length
forces seconds, --n the shot count. Without ACE-Step (MusicGen tops out at 30 s) the reel stays
under 26 s. Each shot gets a render "duration" (6-10 s) long enough for its window.
"""
import argparse
import json
import math
import os
import random
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
HISTORY = Path.home() / ".config/scenic-drop-reel/history.json"
ACE_PY = Path(os.environ.get("ACE_STEP_HOME", Path.home() / ".local/share/ace-step")) / "venv/bin/python"
CARD_INTROS = ("countdown", "black-title", "coords")
MAX_SHOTS = 12  # every shot is one muse render
MAX_SHOT_S = 5.5  # longest window a 6-10 s muse clip gives at a calm, even pace


def length_range(t, shot_s):
    if "length" in t:
        return t["length"]
    if shot_s >= 2.4:  # slow holds: room to breathe
        return 12, 30
    if shot_s >= 1.4:
        return 10, 24
    return 8, 18  # one-beat bursts tire fast


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
    ap.add_argument("--length", type=float, help="reel seconds (default: random for the template)")
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

    beat = 60 / t["music"]["bpm"]
    pattern = list(t["pattern"])
    if min(pattern) >= 4 and t["music"]["bpm"] <= 104 and not a.n:  # slow template: sometimes hold each shot longer
        hold = random.choice([b for b in (4, 6, 8) if b * beat <= MAX_SHOT_S])
        pattern = [hold] * len(pattern)
    shot_s = sum(pattern) / len(pattern) * beat
    intro_s = t["intro"].get("beats", 0) * beat if t["intro"]["type"] in CARD_INTROS else 0
    lo, hi = length_range(t, shot_s)
    hi = min(hi, intro_s + MAX_SHOTS * shot_s, 30 if ACE_PY.exists() else 26)
    lo = min(lo, 0.6 * hi)
    length = a.length or random.uniform(lo, max(lo, hi))
    n = a.n or max(3, min(MAX_SHOTS, round((length - intro_s) / shot_s)))
    if "times" in t:
        n = min(n, len(t["times"]))
    place = a.place
    local = data["local_sounds"].get(a.country.lower() or place.lower(), data["local_sounds"]["default"])
    music = dict(t["music"])
    music["tags"] = music["tags"].replace("{local}", local)
    music["lyrics"] = music["lyrics"].replace("{place}", place)
    shots = []
    for i in range(n):
        light = cycle(t["lights"], i) if "lights" in t else t["light"]
        beats = cycle(pattern, i)
        shots.append({
            "shot": i + 1,
            "beats": beats,
            "duration": max(6, min(10, math.ceil(beats * beat + 3))),
            "move": data["moves"][cycle(t["moves"], i)],
            "light": data["lights"].get(light, light),
            "transition_after": cycle(t["transitions"], i) if i < n - 1 else None,
            "time_label": cycle(t["times"], i) if "times" in t else None,
        })
    intro = dict(t["intro"])
    if "text" in intro:
        intro["text"] = intro["text"].replace("{place}", place).replace("{PLACE}", place.upper()).replace("{n}", str(n))
    print(json.dumps({"template": t["id"], "name": t["name"], "vibe": t["vibe"], "place": place,
                      "seconds": round(intro_s + sum(x["beats"] for x in shots) * beat, 1),
                      "intro": intro, "text": t["text"], "grade": t["grade"], "target": t["target"],
                      "ramp": t["ramp"], "fast": "fpv" in t["moves"], "music": music, "shots": shots}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
