#!/usr/bin/env python3
"""Turn a story (stories/<slug>.json) and its cut soundtrack into a shot plan and muse prompts.

Usage:
  python3 scripts/plan.py stories/shangri-la.json --work ~/Movies/museai/scenic-china-shangri-la

Needs <work>/track.beats.json (music_sections.py cut, or muse-video music.py). Each shot lasts its
`bars` (4 beats each, cut on the music's own beat grid, so every cut lands on a downbeat); the last
shot (`bars` 0) takes the rest of the track, the lingering ending. Writes <work>/plan.json and
<work>/shot<N>.txt (place + season + light + shot + traveller + china.txt + travel.txt without its
music line). Shots with the traveller get the recurring character's face photo as a reference.
"""

import argparse
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SKILLS = HERE.parent
LIGHT = {
    "day": "Clear bright daylight, sun high from the left, crisp shadows",
    "golden": "Warm late-afternoon golden light from the left, long soft shadows",
    "dusk": "Dusk just after sunset: soft pink and blue sky, the last warm light on the high points, the first warm artificial lights glowing",
    "blue-hour": "Blue hour: deep-blue sky, every window and lantern glowing warm amber, no harsh light",
    "mist": "Soft misty morning, low sun from the left diffused through thin mist",
    "overcast": "Soft bright overcast, even light, no hard shadows",
}
FACE_REF = (
    "FACE REFERENCE: The attached photo shows the traveller's real face and hair. It is NOT the first "
    "frame and NOT the location: do not show its background or pose. Render her with exactly this face, "
    "eye colour, freckles, hairstyle and bangs in every frame, at the place below.\n\n"
)
PERSON = {
    "none": "Nobody is the subject of this shot: the traveller is not in it; at most a few distant passers-by, small and natural.",
    "back": "The traveller is seen from behind or three-quarter behind; her face is not the focus.",
    "walk": "The traveller walks naturally at normal speed, seen side-on or from behind, medium-wide, never a face close-up.",
    "side": "The traveller is seen side-on, medium-wide, calm natural expression, mouth closed.",
    "hands": "Only the traveller's hands and sleeves are in frame: her red jacket cuffs over the cream knit sweater.",
}


def travel_block():
    t = (SKILLS / "muse-video/prompt/travel.txt").read_text()
    # the soundtrack is added in compose: clips carry location sound only
    return re.sub(r"SOUND\n\n.*?\n\n", "", t, flags=re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    story = json.loads(Path(a.story).read_text())
    styles = json.loads((HERE / "styles.json").read_text())
    zoom = json.loads((SKILLS / "zoominview/styles.json").read_text())["character"]
    work = Path(a.work).expanduser().resolve()
    beats_file = work / "track.beats.json"
    bf = json.loads(beats_file.read_text())
    beats, total = bf["beats"], bf["seconds"]
    bar_times = [0.0] + beats[4::4]  # bar 0 starts at frame 0 (the swell already plays)
    china = (HERE / "prompt/china.txt").read_text()
    travel = travel_block()
    # her own clothes line gives way to this style's wardrobe
    char = re.sub(r"\s+and a [^,]*(sweater|top)[^,]*,?$", "", zoom["text"].strip()).rstrip(",") + ", wearing " + styles["character"]["wardrobe"] + ". " + styles["character"]["manner"]
    face = str((SKILLS / "zoominview" / zoom["image"]).resolve())

    shots, bar = [], 0
    for n, s in enumerate(story["shots"], 1):
        start = bar_times[bar] if bar < len(bar_times) else total
        last = n == len(story["shots"])
        bar += s["bars"]
        end = total if last or s["bars"] == 0 else bar_times[min(bar, len(bar_times) - 1)]
        if end - start < 1.6:
            raise SystemExit(f"shot {n}: {end - start:.2f} s, too short (track {total} s, {len(bar_times)} bars)")
        length = end - start
        person = s.get("person", "none")
        lines = []
        if person != "none":
            lines.append(FACE_REF.strip())
        lines.append(f"PLACE: {story['where']}. {s['view']}.")
        lines.append(f"SHOT ({length:.1f} s used of this clip): {s['action'] or 'Pure scenery.'} {PERSON[person]}")
        if person != "none":
            lines.append(f"TRAVELLER (the same woman in every shot): {char}")
        block = (china.replace("{SEASON}", story["season"]).replace("{LIGHT}", LIGHT[s.get("light", "day")])
                 .replace("{MOVE}", s["move"]).replace("{AMBIENCE}", s.get("ambience", "natural ambience")))
        prompt = "\n\n".join([*lines, block, travel])
        (work / f"shot{n}.txt").write_text(prompt)
        shots.append({
            "n": n, "label": s.get("label", ""), "start": round(start, 3), "end": round(end, 3),
            "length": round(length, 3), "in": s.get("in", "cut") if n > 1 else "open",
            "person": person, "image": face if person != "none" else "",
            # render long enough for a steady window after muse's 0.5 s settle-in, at most 10 s
            # (longer requests may come back as two self-joined clips)
            "render": min(10, max(6, math.ceil(length + 2))),
            "subject": s["view"].split(":")[0][:90], "move": s["move"].split(".")[0], "light": s.get("light", "day"),
        })
    plan = {
        "name": f"scenic-china-{re.sub(r'[^a-z0-9]+', '-', story['place'].lower()).strip('-')}",
        "place": story["place"], "seconds": total, "bpm": bf["bpm"],
        "hook_text": story.get("hook_text", styles["hook_text"]).replace("{place}", story["place"]),
        "music": story.get("music"), "shots": shots,
    }
    (work / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    for s in shots:
        print(f"shot{s['n']:<2} {s['start']:6.2f}-{s['end']:6.2f}  {s['length']:4.1f} s  render {s['render']:2d}  "
              f"{s['in']:8s} {s['person']:5s} {s['subject'][:60]}")
    print(f"PLAN {work / 'plan.json'} ({total} s, {len(shots)} shots)")


if __name__ == "__main__":
    main()
