#!/usr/bin/env python3
"""Direct one cinematic scenery episode: pick the camera technique, storytelling structure, hook,
lighting, music and shot count (skipping what the last episodes used), then write

  <out>/plan.json      machine plan: segments, moves, render prompts (render / compose read it)
  <out>/episode.md     the six-part director's brief (title, concept, reference image, camera and
                       storytelling plan, ready-to-paste generation prompt, production tip)
  <out>/segN.txt       the muse prompt per segment (STYLE block included, render runs QUALITY=0)

Usage:
  python3 scripts/plan.py --place "Geirangerfjord" --country Norway --setting mountain \
      --view "deep fjord between steep cliffs, the Seven Sisters waterfalls, snow on the peaks" \
      --focus "the Seven Sisters waterfalls" --water falls [--photo fjord.jpg] \
      --out ~/Movies/museai/scenic-geirangerfjord
  python3 scripts/plan.py --list                # the whole library
  python3 scripts/plan.py --history             # earlier episodes
  python3 scripts/plan.py --record plan.json    # after delivery: add the episode to the history

Overrides (only when the user names one): --technique --structure --shots 1|2|3 --hook --light --music.
--vocals on|off: only sung (ACE-Step) or only instrumental styles; default auto picks from both where
the setting/country fits a vocal style.
History: ~/.config/scenery-director/history.json; each dimension skips its last values (series variety).
"""

import argparse
import datetime
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
LIB = json.loads((HERE / "library.json").read_text())
TRAVEL = (HERE.parent / "muse-video/prompt/travel.txt").read_text()
HISTORY = Path.home() / ".config/scenery-director/history.json"
ORIENT = {"9:16": "vertical", "16:9": "horizontal"}
STILL = ("static-panorama", "long-lens-compressed")
SKIP = {"technique": 4, "structure": 3, "hook": 3, "light": 2, "music": 2, "shots": 1}
TREELESS = "NO trees, NO forest, NO bushes, NO green meadows anywhere; only bare rock, scree, snow, ice and brownish tundra."
SETTING_AMBIENCE = {
    "coast": "sea",
    "island": "sea",
    "lake": "lake",
    "mountain": "mountain",
    "snow": "snow",
    "desert": "desert",
    "canyon": "desert",
    "nature": "forest",
    "oldtown": "town",
    "city": "town",
}
WATER_AMBIENCE = {"falls": "waterfall", "sea": "sea", "lake": "lake", "river": "river"}
TIPS = {
    "photo": "Use the original, uncropped photo (no filters, horizon level); muse keeps its light "
    "and colours, so a hazy or over-edited photo gives a hazy, over-edited episode.",
    "falls": "Check the contact sheet for falling water: a waterfall that shimmers in place instead "
    "of falling reads as fake; re-render with the fall-speed line quoted more strongly.",
    "sea": "Judge the open water over time: one constant sliding direction for the whole shot is the "
    "fake 'sheet' look; real sea rises, falls and breaks at irregular spots.",
    "timelapse": "Only the sky may be accelerated: if water, boats or animals speed up too, re-render "
    "with the ground named as real-time again.",
    "multi": "Keep light and weather identical across the shots; a sun that jumps sides at the cut "
    "breaks the spell faster than any other flaw.",
    "move": "Frame-grab 0, 1, 2 s and the last second: muse likes to drift or push in on its own; "
    "a late drift is fixed with muse-video lock_camera.py instead of a re-render.",
}


def slug(text):
    text = unicodedata.normalize("NFKD", text.split(",")[0]).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "scenery"


def history():
    try:
        return json.loads(HISTORY.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def fresh(options, dim, hist):
    """Options not used in the last SKIP[dim] episodes; all of them when that leaves none."""
    recent = [h.get(dim) for h in hist[-SKIP[dim] :]]
    left = [o for o in options if o not in recent]
    return left or list(options)


def fits(entry, setting, country=""):
    regions = entry.get("regions")
    if regions and country.lower() not in regions:
        return False
    return "*" in entry["fits"] or setting in entry["fits"]


def choose(rng, options, dim, hist, forced=None):
    if forced:
        return forced
    return rng.choice(fresh(options, dim, hist))


def strip_sound(text):
    """travel.txt asks muse for music; the episode's music comes from music.py, so clips carry ambience only."""
    return re.sub(r"SOUND\n\n.*?\n\n", "", text, flags=re.S)


def fill(text, a):
    return text.format(
        place=a.place,
        focus=a.focus,
        side=a.side,
        over=a.over or "the water and valley",
        cover=a.cover or "the nearest ridge",
        foreground=a.foreground or "rocks and wild grass",
        sun=a.sun,
        event="{event}",
    )


def direct(a, rng, hist):
    T, S = LIB["techniques"], LIB["structures"]
    # Intimate Detail opens on a close foreground a wide reference photo does not have
    structures = [k for k in sorted(S) if not (k == "D" and a.photo and not a.foreground)]
    structure = choose(rng, structures, "structure", hist, a.structure)
    st = S[structure]

    shots = a.shots or (st.get("shots") or [None])[0]
    if not shots:
        shots = int(choose(rng, ["1", "2", "3"], "shots", hist))
    shots = int(shots)

    def usable(t, photo_seg):
        ok = fits(T[t], a.setting) and t != "multi-shot-sequence"
        return ok and (not photo_seg or T[t]["photo"] in ("best", "ok"))

    one_photo = a.photo and shots == 1
    pool = [t for t in st["techniques"] if t in T and usable(t, one_photo)]
    if shots > 1:
        # the held shots frame the episode; the primary technique is the one that moves
        pool = [t for t in pool if t not in STILL] or [
            t for t in T if usable(t, False) and t not in STILL
        ]
    pool = pool or [t for t in T if usable(t, one_photo)]
    primary = a.technique or choose(rng, pool, "technique", hist)
    if shots == 1:
        moves = [primary]
    else:
        close = (
            "long-lens-compressed"
            if fits(T["long-lens-compressed"], a.setting)
            else "static-panorama"
        )
        moves = ["static-panorama", primary] if shots == 2 else ["static-panorama", primary, close]

    hooks = list(LIB["hooks"])
    if a.water == "none":
        hooks.remove("motion-event")
    if a.water not in ("lake",):
        hooks.remove("reflection")
    hook = choose(rng, hooks, "hook", hist, a.hook)

    lights = [k for k, v in LIB["lighting"].items() if fits(v, a.setting)]
    if not a.north:
        lights = [k for k in lights if not LIB["lighting"][k].get("north")]
    if structure == "E":
        lights = [
            k
            for k in lights
            if k in ("misty-morning", "golden-sunrise", "dramatic-storm", "aurora-night")
        ] or lights
    # a reference photo fixes the light: every segment must match it, so no light is picked
    light = a.light or ("from-photo" if a.photo else choose(rng, lights, "light", hist))

    musics = [k for k, v in LIB["music"].items() if fits(v, a.setting, a.country)]
    if a.vocals != "auto":
        musics = [k for k in musics if LIB["music"][k].get("vocal", False) == (a.vocals == "on")]
    music = choose(rng, musics, "music", hist, a.music)
    return structure, shots, moves, hook, light, music


def segment_roles(arc, n):
    if n == 1:
        return ["; then ".join(arc)]
    if n == 2:
        return [f"{arc[0]}; {arc[1]}", arc[2]]
    return arc


def music_cues(style_name, n, vocal=False):
    if vocal:
        cues = [
            "the song is already playing from the first frame, the voice entering softly (no silent intro)",
            "the chorus rises with the voice as the view opens",
            "the voice holds its last note and the song resolves, flowing back into the opening",
        ]
        if n == 1:
            return [
                "the song is already playing from the first frame, the voice entering softly, rises "
                "into the chorus toward the middle, then holds its last note and flows back into the opening"
            ]
        return [cues[0], cues[2]] if n == 2 else cues
    if n == 1:
        return [
            "the music is already playing from the first frame (no silent intro), builds slowly "
            "toward the middle, then resolves on a held chord that flows back into the opening"
        ]
    cues = [
        "the music is already playing from the first frame, soft and inviting (no silent intro)",
        "the music builds and swells as the view opens",
        "the music settles and resolves on a held chord that flows back into the opening",
    ]
    return [cues[0], cues[2]] if n == 2 else cues


def build(a):
    rng = random.Random(a.seed)
    hist = history()
    structure, shots, moves, hook, light, music = direct(a, rng, hist)
    L, T = LIB, LIB["techniques"]
    st, mu = L["structures"][structure], L["music"][music]
    segs = [list(s) for s in L["edits"][str(shots)]["segments"]]
    if a.seconds != 15:
        k = a.seconds / 15
        segs = [[round(s * k, 2), round(e * k, 2)] for s, e in segs]
    roles = [fill(r, a) for r in segment_roles(st["arc"], shots)]
    cues = music_cues(mu["name"], shots, mu.get("vocal", False))
    amb_keys = [WATER_AMBIENCE.get(a.water), SETTING_AMBIENCE.get(a.setting, "mountain")]
    ambience = "; ".join(L["ambience"][k] for k in dict.fromkeys(filter(None, amb_keys)))
    light_line = fill(L["lighting"][light]["line"], a)
    # segments without the photo attached cannot see its light: describe it in words
    words_light = a.photo_light if light == "from-photo" else light_line
    motion = L["water"][a.water]
    timelapse = None
    if st.get("timelapse"):
        allowed = L["timelapse"]["allowed"]
        event = a.timelapse or rng.choice(allowed)
        timelapse = L["timelapse"]["line"].format(event=event)
    land = f"{a.place}, {a.country}: {a.view}." + (f" {TREELESS}" if a.treeless else "")
    hook_line = fill(L["hooks"][hook]["line"], a)
    style_block = strip_sound(TRAVEL)

    seg_out = []
    for i, ((s, e), move, role, cue) in enumerate(zip(segs, moves, roles, cues, strict=True)):
        dur = e - s
        # muse settles in for ~0.5 s and may self-join renders over 10 s: render a little longer, cap at 10
        render = 15 if shots == 1 and a.seconds > 10 else min(10, max(5, round(dur + 2)))
        photo = bool(a.photo) and i == 0
        tl = timelapse if timelapse and (shots == 1 or i == 1) else None
        parts = []
        if photo:
            parts.append(
                "REFERENCE FIDELITY: The attached photograph is the first frame of real moving footage: "
                "keep its exact composition, landmarks, terrain, colours, light and weather; do not "
                "redraw, restyle or replace anything in it."
            )
        parts += [
            f"PLACE: {land}",
            f"TIME + WEATHER: {light_line if photo else words_light}; the same light, sun direction and weather for the whole shot.",
            f"SHOT ({a.aspect} {ORIENT[a.aspect]}, {render} s): {role}."
            + (f" {hook_line}" if i == 0 else ""),
            f"CAMERA: {fill(T[move]['prompt'], a)} Slow, smooth, level; never dizzy.",
            f"NATURE MOTION: REAL-TIME FOOTAGE. {motion}"
            + (f" {tl}" if tl else " NOT A TIME-LAPSE."),
            f"SOUND: only real natural ambience: {ambience}. No music, no narration, no singing.",
            L["avoid"],
            style_block,
        ]
        seg_out.append(
            {
                "n": i + 1,
                "start": s,
                "end": e,
                "render": render,
                "move": move,
                "role": role,
                "music": cue,
                "photo": a.photo if photo else None,
                "timelapse": bool(tl),
                "prompt": "\n\n".join(parts),
            }
        )

    name = f"scenic-{slug(a.place)}"
    plan = {
        "name": name,
        "place": a.place,
        "country": a.country,
        "setting": a.setting,
        "seconds": a.seconds,
        "aspect": a.aspect,
        "fps": 24,
        "photo": a.photo,
        "structure": structure,
        "technique": moves[0]
        if shots == 1
        else ("multi-shot-sequence" if structure == "F" else moves[1]),
        "moves": moves,
        "shots": str(shots),
        "hook": hook,
        "light": light,
        "music": music,
        "music_style": mu["style"],
        "vocal": mu.get("vocal", False),
        "lyrics": mu.get("lyrics", "").format(place=a.place),
        "bpm": mu["bpm"],
        "ambience": ambience,
        "water": a.water,
        "pace": "calm" if mu["bpm"] < 80 else "flowing",
        "timelapse": bool(timelapse),
        "title": st["title"].format(place=a.place),
        "segments": seg_out,
    }
    return plan


def episode_md(p, a):
    L = LIB
    st, mu = L["structures"][p["structure"]], L["music"][p["music"]]
    tech = L["techniques"][p["technique"]]
    segs = p["segments"]
    edit = L["edits"][p["shots"]]["name"]
    first = segs[0]
    ref = (
        f"Use `{p['photo']}` as the first frame of segment 1 (reference-image-to-video). Keep it "
        "uncropped and unfiltered; the move from it stays small because muse can only animate what "
        "the photo shows."
        if p["photo"]
        else f"Best: a sharp, unfiltered photo of {a.focus} in {L['lighting'][p['light']]['name'].lower()} "
        "light, from the same viewpoint as the opening frame, horizon in the upper third, croppable to "
        f"{p['aspect']}, no people in the foreground, no text or watermark. Without one, render text-to-video."
    )
    if p["photo"]:
        tip = TIPS["photo"]
    elif p["timelapse"]:
        tip = TIPS["timelapse"]
    elif p["water"] in ("falls", "sea"):
        tip = TIPS[p["water"]]
    elif int(p["shots"]) > 1:
        tip = TIPS["multi"]
    else:
        tip = TIPS["move"]

    timeline = []
    for s in segs:
        mv = L["techniques"][s["move"]]["name"]
        timeline.append(
            f"- **{s['start']:g}-{s['end']:g} s** ({mv}): {s['role']}. Music: {s['music']}. Ambience: {p['ambience']}."
        )
    camera_rows = "\n".join(
        f"| {s['n']} | {s['start']:g}-{s['end']:g} s | {L['techniques'][s['move']]['name']} | {s['role']} |"
        for s in segs
    )
    paste = [
        f"Ultra-photorealistic cinematic travel documentary, {p['seconds']:g} seconds, {p['aspect']} "
        + (
            "vertical for YouTube Shorts / TikTok / Reels"
            if p["aspect"] == "9:16"
            else "horizontal"
        )
        + ", 4K, 24 fps, natural colour grade, physically "
        "accurate light. No narration, no text, no subtitles, no watermarks, no logos.",
    ]
    if p["photo"]:
        paste.append(
            "REFERENCE FIDELITY: the attached photograph is the first frame: keep its exact "
            "composition, landmarks, terrain, colours, light and weather."
        )
    paste += [
        f"LANDSCAPE: {p['place']}, {p['country']}: {a.view}."
        + (f" {TREELESS}" if a.treeless else ""),
        f"LIGHT: {fill(L['lighting'][p['light']]['line'], a)}"
        + (f" ({a.photo_light})" if p["light"] == "from-photo" else "")
        + "; identical in every segment.",
        f"CAMERA: {tech['name']}. "
        + " ".join(
            f"Segment {s['n']}: {fill(L['techniques'][s['move']]['prompt'], a)}" for s in segs
        ),
        f"NATURAL MOTION: real-time footage. {L['water'][p['water']]}"
        + (
            " Only the sky may be a smooth time-lapse; water and animals stay real-time."
            if p["timelapse"]
            else ""
        ),
        f"MUSIC: original {'song' if p['vocal'] else 'instrumental'}, {mu['style']}, synced to the segments below; with {p['ambience']} underneath.",
        *([f"LYRICS (one natural lead singer):\n{p['lyrics']}"] if p["vocal"] else []),
        "TIMELINE:\n"
        + "\n".join(
            f"{s['start']:g}-{s['end']:g} s: {s['role']}. {s['music'][0].upper()}{s['music'][1:]}; "
            f"ambience of {p['ambience'].split(';')[0]}."
            for s in segs
        ),
        L["avoid"],
    ]
    return f"""# {p["title"]}

## 1. Episode title
**{p["title"]}**

## 2. Cinematic concept
{st["name"]} (structure {p["structure"]}) at {p["place"]}, {p["country"]}, in {L["lighting"][p["light"]]["name"].lower()} light.
Hook: {L["hooks"][p["hook"]]["name"].lower()}. Primary technique: {tech["name"].lower()} ({tech["use"]}).
Music: {mu["name"].lower()} with real ambience. Pace: {p["pace"]}. {edit}.

## 3. Reference image recommendation
{ref}

## 4. Camera and storytelling plan
| shot | time | move | what the viewer sees |
|---|---|---|---|
{camera_rows}

{chr(10).join(timeline)}

Opening frame: {fill(L["hooks"][p["hook"]]["line"], a)}
Ending: the last frame settles so the replay loops into the first.

## 5. Complete ready-to-paste video generation prompt
```
{chr(10).join(chr(10) + x if i else x for i, x in enumerate(paste))}
```
museai renders each segment from `seg{first["n"]}.txt` … (same content, muse-safe wording, ambience only: the soundtrack is generated separately and synced in compose).

## 6. Final production tip
{tip}
"""


def record(path):
    p = json.loads(Path(path).read_text())
    hist = history()
    hist.append(
        {
            "date": datetime.date.today().isoformat(),
            "place": p["place"],
            "country": p["country"],
            "technique": p["technique"],
            "structure": p["structure"],
            "shots": p["shots"],
            "hook": p["hook"],
            "light": p["light"],
            "music": p["music"],
            "pace": p["pace"],
            "motion": p["water"],
            "timelapse": p["timelapse"],
        }
    )
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(hist, indent=1))
    print(f"recorded episode {len(hist)}: {p['place']} ({p['structure']}, {p['technique']})")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--place")
    ap.add_argument("--country", default="")
    ap.add_argument(
        "--setting",
        default="nature",
        choices=[
            "coast",
            "island",
            "mountain",
            "canyon",
            "lake",
            "city",
            "oldtown",
            "nature",
            "desert",
            "snow",
        ],
    )
    ap.add_argument("--view", help="what is really there: landmarks, terrain, water, vegetation")
    ap.add_argument("--focus", help="the main subject the camera serves")
    ap.add_argument("--water", default="none", choices=list(LIB["water"]))
    ap.add_argument("--photo", help="reference image: first frame of segment 1")
    ap.add_argument(
        "--photo-light",
        help="with --photo: its light and weather in words, for the segments rendered without it",
    )
    ap.add_argument(
        "--treeless", action="store_true", help="Arctic, highlands, desert: no trees anywhere"
    )
    ap.add_argument("--north", action="store_true", help="aurora possible (Arctic winter)")
    ap.add_argument("--foreground", help="close foreground for low-angle / parallax / crane moves")
    ap.add_argument("--cover", help="what hides the view before a reveal (ridge, cliff edge)")
    ap.add_argument("--over", help="what an aerial glide flies over")
    ap.add_argument("--side", default="right", choices=["left", "right"])
    ap.add_argument("--sun", default="left", help="where the sun is: left, right, behind the peaks")
    ap.add_argument(
        "--timelapse", help="structure E: the sky event (clouds rolling over the peaks, ...)"
    )
    ap.add_argument("--seconds", type=float, default=15)
    ap.add_argument("--aspect", default="9:16", choices=["9:16", "16:9"])
    ap.add_argument("--technique", choices=list(LIB["techniques"]))
    ap.add_argument("--structure", choices=list(LIB["structures"]))
    ap.add_argument("--shots", choices=["1", "2", "3"])
    ap.add_argument("--hook", choices=list(LIB["hooks"]))
    ap.add_argument("--light", choices=list(LIB["lighting"]))
    ap.add_argument("--music", choices=list(LIB["music"]))
    ap.add_argument("--vocals", default="auto", choices=["auto", "on", "off"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--out", help="work folder (default ~/Movies/museai/scenic-<slug>)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--record", metavar="PLAN")
    a = ap.parse_args()

    if a.list:
        for dim in ("techniques", "structures", "hooks", "lighting", "music"):
            print(f"\n{dim}:")
            for k, v in LIB[dim].items():
                print(
                    f"  {k:28} {v['name']}" + (f"  [photo: {v['photo']}]" if "photo" in v else "")
                )
        return
    if a.history:
        for h in history():
            print(
                " | ".join(
                    str(h.get(k, ""))
                    for k in (
                        "date",
                        "place",
                        "structure",
                        "technique",
                        "shots",
                        "hook",
                        "light",
                        "music",
                    )
                )
            )
        return
    if a.record:
        record(a.record)
        return
    if not (a.place and a.view):
        ap.error("--place and --view are required")
    a.focus = a.focus or a.place
    if a.photo and not a.photo_light and not a.light:
        ap.error("--photo needs --photo-light (its light and weather in words) or --light")
    if a.photo:
        a.photo = str(Path(a.photo).expanduser().resolve())
    p = build(a)
    out = Path(a.out or f"~/Movies/museai/{p['name']}").expanduser()
    out.mkdir(parents=True, exist_ok=True)
    p["work"] = str(out)
    for old in out.glob("seg*.txt"):
        old.unlink()
    for s in p["segments"]:
        (out / f"seg{s['n']}.txt").write_text(s["prompt"])
    (out / "plan.json").write_text(json.dumps(p, indent=1, ensure_ascii=False))
    (out / "episode.md").write_text(episode_md(p, a))
    print(f"{out}/episode.md")
    print(
        f"structure {p['structure']} ({LIB['structures'][p['structure']]['name']}), technique {p['technique']}, "
        f"{p['shots']} shot(s) {p['moves']}, hook {p['hook']}, light {p['light']}, music {p['music']}"
    )
    if any(h["place"].lower() == p["place"].lower() for h in history()):
        print(
            "NOTE: this destination was an earlier episode; check shot-history and pick new views",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
