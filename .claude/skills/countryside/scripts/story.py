#!/usr/bin/env python3
"""Story template and gate for a countryside playlist film. REAL VIDEO ONLY: every beat is a motion clip.

  story.py new ct-0042 --style hydrangea-cottage --slug hydrangea-day [--songs 6] [--per-song 21] > story.json
      a story.json skeleton: the idea's six scenes as six songs, `per-song` clip beats each (shot/move = TODO),
      the style's world, camera, grade and music copied in.
  story.py check story.json [--work DIR]
      exit 1 on a rule break (a still beat, a beat without `move`, a TODO left, a film outside 1000-1320 s with
      6 songs); with --work, exit 3 when any sN.mp4 is missing: the clip queue is not done. Never compose then:
      wait for muse's video quota to reset and re-run the clip queue (no still fallback, user rule 2026-11-25).
  story.py chapters story.json
      the YouTube description's chapter list (00:00 - song title), from the beat timeline.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ideas  # noqa: E402

# The studied channel cuts every ~3 s (median 3.0 s, STUDY.md): each 10 s clip gives 3 shots, wide then two crops.
CUTS = [[0.2, 3.4], [3.5, 3.2, 1.3, 0.5, 0.5], [6.6, 3.2, 1.15, 0.5, 0.5]]
MIN_S, MAX_S = 1000, 1320


def beat_secs(b, xf):
    cuts = b.get("cuts")
    if cuts:
        return sum(c[1] for c in cuts) - xf * (len(cuts) - 1)
    return float(b.get("hold", 8.0))


def timeline(story):
    xf = float(story.get("xf", 0.4))
    t, out = 0.0, []
    for b in story["beats"]:
        out.append((t, b))
        t += beat_secs(b, xf) - xf
    return out, t + xf


def new(idea, style, slug, songs, per_song):
    places = {"house": f"inside {style['world']}", "garden": f"the garden and grounds of {style['world']}"}
    beats = []
    for k, sc in enumerate(idea["scenes"][:songs]):
        for j in range(per_song):
            beats.append({"ch": k + 1, "song": k, "where": "garden" if j % 3 == 0 else "house", "time": sc["time"],
                          "outfit": sc["time"], "kind": "clip", "cast": [] if j % 3 == 0 else ["ELLIE"],
                          "shot": "TODO", "move": "TODO", "cuts": CUTS, "chapter": False})
    return {
        "story_id": idea["id"], "slug": slug, "title": idea["title"], "eyebrow": "a slow day in the countryside",
        "format": "countryside-playlist", "xf": 0.4,
        "style": style["id"], "camera": style["camera"], "grade": style["grade"], "music_lufs": style["music_lufs"],
        "shake": 2, "max_slow": 1.12, "chapter_cards": False,
        "places": places,
        "light": {sc["time"]: "TODO one sentence of light for this time" for sc in idea["scenes"]},
        "outfits": {sc["time"]: style["outfits"] for sc in idea["scenes"]},
        "look": "healing-longform/prompt/look.txt",
        "refs": {"house": {"kind": "place", "brief": f"The house interior empty, nobody in it, seen from the doorway: {style['world']}."},
                 "garden": {"kind": "place", "brief": f"The garden and grounds empty, nobody in them: {style['world']}."}},
        "chapters": [{"n": k + 1, "title": sc["scene"], "sub": ""} for k, sc in enumerate(idea["scenes"][:songs])],
        "songs": [{"title": "TODO our own song title", "scene": sc["scene"], "tags": style["music"], "seed": 0}
                  for sc in idea["scenes"][:songs]],
        "beats": beats,
    }


def check(story, work=None):
    errs = []
    for i, b in enumerate(story["beats"], 1):
        if b.get("kind") != "clip":
            errs.append(f"beat {i}: kind={b.get('kind')!r}; real video only, every beat is a clip")
        if not b.get("move") or b.get("move") == "TODO":
            errs.append(f"beat {i}: no `move`; a clip beat needs its one motion")
        if "TODO" in json.dumps(b):
            errs.append(f"beat {i}: TODO left")
    for s in story.get("songs", []):
        if "TODO" in s.get("title", "TODO"):
            errs.append(f"song {s.get('scene')!r}: title TODO")
    _, total = timeline(story)
    n_songs = len(story.get("songs", []))
    if n_songs == 6 and not MIN_S <= total <= MAX_S:
        errs.append(f"film {total:.0f} s, aim {MIN_S}-{MAX_S} s for 6 songs")
    if errs:
        return 1, errs
    if work:
        miss = [i for i in range(1, len(story["beats"]) + 1) if not (Path(work) / f"s{i}.mp4").exists()]
        if miss:
            return 3, [f"{len(miss)} clips missing ({', '.join(f's{i}' for i in miss[:12])}"
                       f"{' ...' if len(miss) > 12 else ''}): re-run the clip queue after the quota reset; "
                       "never compose from stills"]
    return 0, [f"ok: {len(story['beats'])} clips, {total:.0f} s ({total / 60:.1f} min), {n_songs} songs"]


def chapters(story):
    tl, _ = timeline(story)
    first = {}
    for t, b in tl:
        first.setdefault(b.get("song", 0), t)
    lines = []
    for k, s in enumerate(story.get("songs", [])):
        t = int(first.get(k, 0))
        lines.append(f"{t // 60:02d}:{t % 60:02d} - {s['title']}")
    return lines


def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("id")
    n.add_argument("--style", required=True)
    n.add_argument("--slug", required=True)
    n.add_argument("--songs", type=int, default=6)
    n.add_argument("--per-song", type=int, default=21)
    c = sub.add_parser("check")
    c.add_argument("story")
    c.add_argument("--work")
    sub.add_parser("chapters").add_argument("story")
    a = ap.parse_args(argv)
    if a.cmd == "new":
        idea = next((i for i in ideas.bank() if i["id"] == a.id), None)
        style = next((s for s in json.loads(ideas.STYLES.read_text()) if s["id"] == a.style), None)
        if not idea or not style:
            sys.exit("unknown idea or style id")
        print(json.dumps(new(idea, style, a.slug, a.songs, a.per_song), indent=1))
        return 0
    story = json.loads(Path(a.story).read_text())
    if a.cmd == "chapters":
        print("\n".join(chapters(story)))
        return 0
    code, msgs = check(story, a.work)
    print("\n".join(msgs))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
