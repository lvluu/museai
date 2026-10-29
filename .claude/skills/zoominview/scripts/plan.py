"""Plan a zoominview reel: pick a hook (reaction), a reveal transition, a music style and a caption hook that fit the place, fill the prompts.

Usage:
  python3 scripts/plan.py --place "Ponta de São Lourenço, Madeira" --setting coast --light sunset \
      --view "jagged red volcanic cliffs dropping into a deep blue Atlantic, white surf, green headlands ..." > plan.json
  python3 scripts/plan.py --list
Options: --focus (what the end zooms into), --country (local music), --hook ID / --reveal ID / --music ID (force), --person "..." (default: the recurring character in styles.json, "random" for a random traveller),
--seed N. Picks skip the last 3 hooks, reveals and music styles used (~/.config/zoominview/history.json).
"""
import argparse
import json
import random
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
HISTORY = Path.home() / ".config/zoominview/history.json"
PEOPLE = [
    "a young woman in her twenties with long dark hair and a white T-shirt",
    "a young man in his twenties with messy wavy brown hair and a white T-shirt",
    "a woman in her thirties with a short blonde bob and a light rain jacket",
    "a man in his thirties with a short beard and a grey hoodie",
    "a young East Asian woman with a ponytail and a denim jacket",
    "a young Black man with short curly hair and an olive overshirt",
    "a South Asian woman in her twenties with wavy black hair and a linen shirt",
    "a freckled young woman with red curly hair and a knitted sweater",
]


# the attached photo only shows who she is; without this muse may open the clip on the photo itself
FACE_REF = ("FACE REFERENCE: The attached photo shows the woman's real face, hair and glasses. It is NOT the first "
            "frame and NOT the location: do not show this room or this pose. Render her with exactly this face, "
            "hairstyle, bangs and glasses, at the place below. She WEARS HER THIN ROUND SILVER WIRE-RIM GLASSES IN "
            "EVERY FRAME: never takes them off, never without glasses.\n\n")


# muse put a second traveller in clip B for the whole reveal although the brief said "Nobody in frame"
# (Madeira, 2026-10-29): the rule must open the prompt and name every body part
NOBODY = ("POINT OF VIEW ONLY: the traveller from the previous clip is now BEHIND the phone, filming. No person "
          "appears in any frame of this clip: no face, no hair, no hands, no arms, no body, no other tourists. "
          "Only the landscape.\n\n")


def fits(item, key, value):
    allowed = item.get(key, ["any"])
    return "any" in allowed or value in allowed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--place")
    ap.add_argument("--view", help="what the revealed view shows: real landmarks, terrain, water, light")
    ap.add_argument("--setting", default="nature",
                    help="coast island mountain canyon lake city oldtown nature desert snow")
    ap.add_argument("--light", default="golden", help="sunset sunrise golden day blue-hour night")
    ap.add_argument("--country", default="")
    ap.add_argument("--focus", default="the most beautiful landmark of the view",
                    help="the beautiful angle the end zooms into, e.g. \"the dark basalt sea stacks in the white surf\"")
    ap.add_argument("--reveal")
    ap.add_argument("--music")
    ap.add_argument("--hook", help="the reaction (styles.json hooks), e.g. gasp, still-awe")
    ap.add_argument("--person")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    styles = json.loads((SKILL / "styles.json").read_text())
    if a.list:
        for r in styles["reveals"]:
            print(f"reveal {r['id']:14} {','.join(r['setting']):55} {r['name']}")
        for h in styles["hooks"]:
            print(f"hook   {h['id']:18} {','.join(h['setting']):51} {h['name']}")
        for m in styles["music"]:
            print(f"music  {m['id']:14} {','.join(m['setting']):55} {m['name']}")
        return
    if not (a.place and a.view):
        ap.error("--place and --view are required")
    if a.light not in styles["lights"]:
        ap.error(f"--light must be one of {', '.join(styles['lights'])}")
    rng = random.Random(a.seed)
    hist = {"reveals": [], "music": [], "hooks": [], **(json.loads(HISTORY.read_text()) if HISTORY.exists() else {})}

    def choose(kind, pool, forced):
        if forced:  # a named one is used even when it doesn't fit the setting, light or country
            return next((x for x in styles[kind] if x["id"] == forced), None) or sys.exit(f"no {kind} {forced!r}")
        fresh = [x for x in pool if x["id"] not in hist[kind][-3:]] or pool
        return rng.choice(fresh)

    reveals = [r for r in styles["reveals"] if fits(r, "setting", a.setting)]
    reveal = choose("reveals", reveals, a.reveal)
    character = None if a.person else styles.get("character")
    if a.person == "random":
        a.person = None
    hooks = [h for h in styles["hooks"] if fits(h, "setting", a.setting) and fits(h, "light", a.light)
             and h["id"] not in (character or {}).get("skip_hooks", [])]
    hook = choose("hooks", hooks, a.hook)
    country = a.country.lower()
    local = [m for m in styles["music"] if country and country in m.get("country", [])
             and fits(m, "setting", a.setting)]
    music_pool = local or [m for m in styles["music"] if "country" not in m and fits(m, "setting", a.setting)
                           and fits(m, "light", a.light)] or [m for m in styles["music"] if "country" not in m]
    music = choose("music", music_pool, a.music)

    light = styles["lights"][a.light]
    fill = {"{place}": a.place, "{view}": a.view, "{person}": character["text"] if character else a.person or rng.choice(PEOPLE),
            "{light}": light, "{focus}": a.focus, "{hook}": hook["text"], "{reveal_at}": f"{reveal['reveal_at']:g}"}
    rules = (SKILL / "prompt/reveal.txt").read_text().replace("{LIGHT}", light[0].upper() + light[1:])

    def prompt(text):
        text = text.replace("{zoom}", styles["zoom"])
        for k, v in fill.items():
            text = text.replace(k, v)
        return f"{text}\n\n{rules}"

    name = a.place.split(",")[0].strip()
    caption = rng.choice(styles["captions"].get(a.setting, []) + styles["captions"]["any"]).replace("{name}", name)

    reveal_time = reveal["a_seconds"] + reveal["reveal_at"]
    length = reveal["a_seconds"] + reveal["b_seconds"] + reveal.get("c_seconds", 0)
    m = {"id": music["id"], "name": music["name"]}
    if "file" in music:
        m["file"] = str(SKILL / music["file"])
    else:
        beat = 60 / music["bpm"]
        m.update(style=music["style"], bpm=music["bpm"], lyrics=music.get("lyrics", ""),
                 intro_beats=round(reveal_time / beat), body_beats=round((length - reveal_time) / beat) + 1)
    plan = {"place": a.place, "setting": a.setting, "light": a.light, "person": fill["{person}"],
            "reveal": {"id": reveal["id"], "name": reveal["name"], "a_seconds": reveal["a_seconds"],
                       "b_seconds": reveal["b_seconds"], "c_seconds": reveal.get("c_seconds", 0),
                       "reveal_at": reveal["reveal_at"]},
            "hook": {"id": hook["id"], "name": hook["name"]},
            "reveal_time": reveal_time, "length": length, "music": m, "caption_hook": caption,
            "prompt_a": prompt((FACE_REF if character else "") + reveal["a"]), "prompt_b": prompt(NOBODY + reveal["b"])}
    if character:
        plan["person_image"] = str(Path(character["image"]).expanduser())
    if "c" in reveal:
        plan["prompt_c"] = prompt(NOBODY + reveal["c"])
    hist["reveals"] = (hist["reveals"] + [reveal["id"]])[-10:]
    hist["music"] = (hist["music"] + [music["id"]])[-10:]
    hist["hooks"] = (hist["hooks"] + [hook["id"]])[-10:]
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(hist))
    print(json.dumps(plan, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
