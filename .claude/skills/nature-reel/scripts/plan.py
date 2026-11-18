#!/usr/bin/env python3
"""Pick the style for the next nature reel (skips the last 4 used) and print the plan as JSON.

  python3 scripts/plan.py --place "Milford Sound, New Zealand" --setting fjord [--style indie-folk] [--shots 6]

--setting is matched against each style's `fits`; with no match any style qualifies. The pick is recorded in
~/.config/nature-reel/history.json (--no-record to skip). Output: per-shot light and move (rotating through
the style's moves), seconds per shot, music prompt + BPM, in-app audio search keywords.
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CFG = json.loads((HERE / "styles.json").read_text())
HIST = Path(CFG["history"]).expanduser()
SHOT_S, MAX_S, MIN_S = 7, 36, 21
XF = 0.7


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--place", required=True)
    ap.add_argument("--setting", default="")
    ap.add_argument("--style")
    ap.add_argument("--shots", type=int)
    ap.add_argument("--no-record", action="store_true")
    a = ap.parse_args()
    styles = CFG["styles"]
    hist = json.loads(HIST.read_text()) if HIST.exists() else []
    if a.style:
        if a.style not in styles:
            sys.exit(f"unknown style {a.style}; one of {', '.join(styles)}")
        sid = a.style
    else:
        recent = [h["style"] for h in hist[-4:]]
        pool = [k for k in styles if k not in recent]
        fit = [k for k in pool if any(a.setting and a.setting in f for f in styles[k]["fits"])]
        sid = random.choice(fit or pool)
    s = styles[sid]
    cut = s.get("cut_s")
    if cut:  # energetic style: cuts on the beat, shots render only as long as the cut needs; the camera stays slow
        n = a.shots or random.choice([6, 7, 8])
        dur = round(cut + XF + 0.6)
    else:
        n = a.shots or random.choice([3, 4, 5])
        n = max(MIN_S // SHOT_S, min(n, MAX_S // SHOT_S))
        dur = SHOT_S
    shots = [{"n": i + 1, "duration": dur, "light": s["light"], "move": s["moves"][i % len(s["moves"])]}
             for i in range(n)]
    total = n * (cut + XF if cut else SHOT_S) - (n - 1) * XF - (0 if cut else 0)
    secs = (cut or SHOT_S - XF)
    plan = {"place": a.place, "style": sid, "name": s["name"], "shots": shots, "seconds": round(total, 1), "beat_secs": round(secs, 1),
            "music": s["music"], "bpm": s["bpm"], "grade": s["grade"], "audio_search": s["audio_search"],
            "body_beats": int(total * s["bpm"] / 60) + 4}
    if not a.no_record:
        HIST.parent.mkdir(parents=True, exist_ok=True)
        hist.append({"style": sid, "place": a.place})
        HIST.write_text(json.dumps(hist[-50:], indent=1))
    print(json.dumps(plan, indent=1))


if __name__ == "__main__":
    main()
