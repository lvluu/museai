#!/usr/bin/env python3
"""Turn one library script into still prompts, shot prompts and a render script.

  python3 scripts/build.py ME-0001 WORK      # WORK/stills/*.json, WORK/shots/*.prompt.txt, WORK/render.sh,
                                             # WORK/script.json, WORK/stills.sh

Stills: one first frame per (framing, cast, wardrobe, state) group, so all close-ups of one person in
one episode start from the same face (image generation takes no reference image; sharing the still is
what keeps a face identical across cuts). A shot may set "still": "<name>" to share or split a group,
and "state" (e.g. "soaked", or {"VIV": "soaked"} for one person of a two-shot) to change the look mid-episode.
Shots: one muse render per shot, first frame = its still, one line at most, timed so the line starts
at 0.6 s (a line at 0 s fails SOUND WITHOUT LIPS) and the clip runs `sec + 1` s for trimming room.
"""
import json
import math
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
CAST = json.loads((SKILL / "series/cast.json").read_text())
LOOK = (SKILL / "prompt/look.txt").read_text().strip()
# The reel's faces measure rgb 148/95/82, L 46-47, a 20-21, b 16-17 (reference-study.md Round 3e): a midtone, rosy,
# not yellow. "fair peach" rendered them light (L 50-52), grey (a 16-17) and yellow (b 19-23).
SKIN = ("medium-toned warm rose-tan skin, a full shade deeper than fair, like a lightly tanned Mediterranean complexion "
        "on 35 mm film: a midtone that reads darker than the pale surroundings, red clearly stronger than yellow "
        "(rosy, never yellow, never golden, never orange, never pale or porcelain), a soft rose flush on the cheeks and "
        "deep glossy rose lips")
FRAMING = {
    "ecu": "Extreme close-up: the face fills the frame, eyes and mouth large and centred, front view",
    "wide": "Wide shot, the whole scene and the people full-length, the place clearly established",
    "medium": "Medium close-up from the upper chest up, the person alone in the frame, the face big and the clear centre of the frame (about 40 % of the frame width), the top of the hair about a tenth below the top edge, the eyes about 40 % down, front three-quarter view, eyes on the other person who stands just outside the frame beside the camera",
    "close": "Tight close-up from the upper chest up like the memoriescore reels, the person alone in the frame: the face fills about half the frame width and the hair almost the whole width, the top of the hair about a tenth below the top edge, the eyes about 40 % down, both eyes and the whole mouth clearly visible, front three-quarter view, never profile, eyes on the other person who stands just outside the frame beside the camera",
    "ots": "Over-the-shoulder shot: the second person's shoulder, hair and cheek soft and out of focus in the near foreground at one side, the first person facing the camera in three-quarter view from the chest up, sharp, looking at the second person's eyes",
    "two-shot": "Medium two-shot from the waist up, both bodies facing the camera squarely, each turning only the head partway toward the other, both faces in front three-quarter view, both mouths visible",
    "insert": "Insert: a tight close-up of hands and an object (no face in the frame), shallow focus, the object large and centred, the action of the hands clear",
}
# CLEAN: tiny detail (boucle, sequins, racks of pastries, register keys) crawled frame to frame and read as
# "particles flickering"; the reel's backgrounds are a few large soft shapes (reference-study.md Round 3h).
CLEAN = ("A CLEAN PICTURE: no film grain, no noise, no dust, no sparkle, no glitter, no specks, no flicker. The "
         "background simple and calm: a few large soft shapes in muted warm grey-taupe, beige and cream, heavily and "
         "smoothly defocused, never a busy rack of small objects, no small repeating detail, no small bright points. "
         "Every fabric smooth and solid at a glance (plain wool, satin, velvet, silk, leather, plush), no small busy "
         "texture or print.")
LIGHT = ("LIGHT exactly like the memoriescore reels: a broad SOFT FRONTAL key slightly to one side of the camera, gently "
         "modelling the face with soft shadows, no hard nose or cheek shadow, no hot spot; a subtle warm backlight "
         "catching single hairs. " + SKIN + "; natural skin texture under a light optical diffusion, never waxy or "
         "airbrushed. Warm neutrals with restrained pink-red accents (honey beige #B49A7D, rose-tan skin #BD8978, rose "
         "lips #A6534E, taupe #8C8277, deep brown-black #170F0B), creamy whites, about 5,500 K with a subtle warm "
         "finish, medium contrast with rich deep brown-black shadows in clothes and hair (never lifted, milky or "
         "faded), low-to-moderate saturation. The face big, evenly lit and clearly readable, eyes and lips crisp, "
         "smooth fine detail, no digital crispness. " + CLEAN + " Lamps bloom gently and never clip; no haze, no "
         "dramatic chiaroscuro, no HDR. A soft out-of-focus foreground piece (a shoulder, a glass, a door frame) may "
         "sit at one side.")
CAMERA = "A very slow gentle push-in or a slight natural handheld drift, eye level, never fast; ONE CONTINUOUS TAKE, no cuts, no zoom."


def load_script(sid):
    if sid.endswith(".json"):  # a one-off script file, e.g. a reference-cast episode
        return json.loads(Path(sid).read_text())
    for f in sorted((SKILL / "library").glob("batch_*.json")):
        for s in json.loads(f.read_text()):
            if s["id"] == sid:
                return s
    sys.exit(f"{sid} not in library/")


def person(key, sc, state="", first=False):
    # "look_as" names the person in a supplied first frame; their cast.json face would fight that frame
    if first and key in sc.get("look_as", {}):
        return f"{sc['look_as'][key]}, exactly as in the attached first frame: same face, hair and outfit."
    c = CAST[key]
    wk = sc.get("wardrobe", {}).get(key) or next(iter(c["wardrobe"]))
    state = state.get(key, "") if isinstance(state, dict) else state
    extra = f" Right now: {state}." if state else ""
    return f"{c['identity']} Wearing: {c['wardrobe'][wk]}.{extra}"


def still_key(shot, sc):
    if shot.get("still"):
        return shot["still"]
    who = "-".join(shot["cast"])
    st = shot.get("state", "")
    st = " ".join(st.values()) if isinstance(st, dict) else st
    state = "-".join(re.findall(r"[a-z]+", st.lower())[:2])
    return f"{shot['framing']}-{who}" + (f"-{state}" if state else "") \
        if shot["framing"] in ("close", "medium", "ots") else shot["id"]


def still_prompt(shot, sc):
    people = " ".join(person(k, sc, shot.get("state", "")) for k in shot["cast"])
    # close/medium stills are shared by every shot of that person: a calm face, the clip does the acting
    names = [CAST[k]["name"].split()[0] for k in shot["cast"]]
    pose = shot.get("still_pose") or (
        f"{names[0]} listens to {names[1]}, eyes on {names[1]}'s face, a quiet, thoughtful look, mouth closed."
        if shot["framing"] == "ots" else
        f"{' and '.join(names)} at ease, a natural relaxed face with the hint of a smile, mouth closed, eyes on the other person just outside the frame beside the camera."
        if shot["framing"] in ("close", "medium") else shot["action"])
    people = "" if shot["framing"] == "insert" else people
    return (f"A frame grab from a 1999 Hollywood romantic comedy, shot on 35 mm film with an 85 mm lens, "
            f"warm softly diffused vintage glamour, the face clearly readable. Vertical 9:16. {FRAMING[shot['framing']]}. "
            f"Place: {sc['setting']}. {LIGHT} The moment: {pose} Caught mid-moment, real and candid, not posing; a speaker's "
            f"mouth closed. {people} LEFT and RIGHT mean the person's own side. Original faces that resemble no actor, "
            f"celebrity or public figure. The face is in focus; the background is heavily out of focus. Real young actors on a real film set, 1990s supermodel "
            f"styling (big voluminous blown-out hair, strong brows, high-shine glossy lips that catch the light (the lips are the only gloss), gold "
            f"jewellery), not a render. Never flat, grey, milky, faded or washed out, never teal-and-orange, never sepia, "
            f"never HDR, no CGI look. No text, no logos, no watermark.")


def shot_prompt(shot, sc):
    dur = max(4, math.ceil(shot["sec"]) + 1)
    first = bool(shot.get("first"))
    people = "\n".join(f"- {CAST[k]['name'].split()[0]}: {person(k, sc, shot.get('state', ''), first)} "
                       f"Voice: {CAST[k]['voice']}." for k in shot["cast"])
    p = [f"NO TEXT ON SCREEN. One continuous {dur}-second shot of a short film. The attached image is the exact "
         f"first frame: keep every face, hairstyle, outfit, the framing and the camera position.",
         *([f"CAST (keep faces, hair, outfits and voices identical for the whole clip):\n{people}"] if people else []),
         f"SETTING: {sc['setting']}. {LIGHT}",
         f"CAMERA: {'Exactly the framing and camera position of the first frame' if first else FRAMING[shot['framing']]}. {CAMERA}",
         f"ACTION: {shot['action']}"]
    ln = shot.get("line")
    if ln:
        who = CAST[ln["who"]]["name"].split()[0].strip("'")
        others = [CAST[k]["name"].split()[0] for k in shot["cast"] if k != ln["who"]]
        listen = (f" {', '.join(others)} listens with lips closed, eyes on {who}, reacting only with the eyes."
                  if others else "")
        sex = "her" if CAST[ln["who"]]["sex"] == "F" else "his"
        p.append(f"SCRIPT (natural American English, normal conversational pace, the exact words, nothing added):\n"
                 f"0.0-0.6 s: silence, {who} holds the look, lips closed.\n"
                 f"0.6 s: {who} speaks, only {sex} lips move, in {sex} own voice: \"{ln['en']}\"{listen}\n"
                 f"After the line: {who} closes {sex} mouth and holds the expression to the end of the shot. "
                 f"Nobody says anything else.")
    else:
        p.append("SOUND: no dialogue at all, nobody speaks or moves their lips as if talking; only natural "
                 "ambient sound of the place.")
    p.append(LOOK)
    return "\n\n".join(p), dur


def build(sid, work):
    sc, work = load_script(sid), Path(work)
    sid = sc["id"]
    for d in ("stills", "shots", "clips"):
        (work / d).mkdir(parents=True, exist_ok=True)
    (work / "script.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1))
    stills, lines = {}, ["#!/usr/bin/env bash", "# render the shots one at a time (render-queue; JOBS=N for more), one muse call each",
                         "set -u", f"cd {work}", "MV=${MUSE_VIDEO:-$HOME/Work/museai-main/.claude/skills/muse-video/scripts/muse-video}", "export MV"]
    jobs = []
    for shot in sc["shots"]:
        # "first": a frame you supply (e.g. a reference frame) is the first frame; no still is generated
        k = shot.get("first") or still_key(shot, sc)
        if not shot.get("first"):
            stills.setdefault(k, still_prompt(shot, sc))
        text, dur = shot_prompt(shot, sc)
        (work / "shots" / f"{shot['id']}.prompt.txt").write_text(text)
        out = f"{sid.lower()}-{shot['id']}.mp4"
        jobs.append(f"[ -f clips/{out} ] || {{ SIZE=9:16 DURATION={dur} QUALITY=0 IMAGE={shot.get('first') or f'stills/{k}.png'} OUT_NAME={out} "
                    f"NO_OPEN=1 \"$MV\" -f shots/{shot['id']}.prompt.txt && cp ~/Movies/museai/{out} clips/; }}")
    (work / "jobs.txt").write_text("\n".join(jobs) + "\n")
    lines.append('"${MV%/muse-video}/render-queue" jobs.txt')
    for k, p in stills.items():
        (work / "stills" / f"{k}.json").write_text(json.dumps(
            {"prompt": p, "n": 2, "size": "1080x1920", "response_format": "b64_json"}))
    (work / "render.sh").write_text("\n".join(lines) + "\n")
    (work / "render.sh").chmod(0o755)
    print(f"{sid}: {len(sc['shots'])} shots, {len(stills)} stills -> {work}")
    for k in stills:
        print(f"  still {k}")


if __name__ == "__main__":
    build(*sys.argv[1:3])
