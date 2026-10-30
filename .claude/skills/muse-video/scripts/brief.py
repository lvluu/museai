#!/usr/bin/env python3
"""Route one video brief to any museai format skill and print its first commands.

Usage: python3 brief.py brief.json [--format zoominview]

brief.json is the one input shape every format skill takes (see ../SKILL.md "Format skills"):
  {"format": "scenic-drop-reel",           # optional: scenic-drop-reel | zoominview | travel | scenery-director | product-ad | teaching-video
   "place": "Kelingking Beach, Nusa Penida", # place or subject (product name, lesson topic)
   "country": "Indonesia", "scope": "place",  # scope: country | region | city | place (scenic-drop-reel)
   "setting": "coast", "light": "sunset",     # coast island mountain canyon lake city oldtown nature desert snow
   "view": "...", "focus": "...",             # what is really there; what the zoom lands on (zoominview)
   "seconds": 15, "aspect": "9:16",           # optional; each format has its own default
   "music": "piano-swell",                    # optional style id or free-text style
   "out": "~/Movies/museai/zoom-kelingking"}  # optional work folder
It prints the format, the work folder, the final file name (prefix per format, so the dashboard's
posting.py TRAVEL_NAME puts travel formats on the Travel channel), the shot-history check and the plan
command. Without "format" a place goes to scenic-drop-reel, the default for every place request.
"""

import argparse
import json
import os
import re
import shlex
import sys
import unicodedata
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
# format -> (file-name prefix, aspects it renders, travel format)
FORMATS = {
    "scenic-drop-reel": ("reel", ("9:16",), True),
    "zoominview": ("zoom", ("9:16",), True),
    "travel": ("travel", ("9:16", "16:9"), True),
    "scenery-director": ("scenic", ("9:16", "16:9"), True),
    "chinese-scenery-style": ("scenic-china", ("9:16",), True),
    "product-ad": ("ad", ("9:16",), False),
    "teaching-video": ("lesson", ("9:16+16:9",), False),
}


def slug(text):
    text = unicodedata.normalize("NFKD", text.split(",")[0]).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "video"


def cmd(*parts):
    return " ".join(shlex.quote(str(p)) for p in parts if p not in (None, ""))


def route(b):
    # every place in China gets the China travel-story style unless the brief names a format
    china = (b.get("country") or "").strip().lower() in ("china", "prc", "中国")
    fmt = b.get("format") or ("chinese-scenery-style" if china else "scenic-drop-reel")
    if fmt not in FORMATS:
        sys.exit(f"unknown format {fmt!r}; one of {', '.join(FORMATS)}")
    prefix, aspects, travel = FORMATS[fmt]
    subject = b.get("place") or b.get("subject")
    if not subject:
        sys.exit("brief needs place (or subject)")
    aspect = b.get("aspect") or aspects[0]
    if aspect not in aspects:
        sys.exit(f"{fmt} renders {' / '.join(aspects)}, not {aspect}")
    name = f"{prefix}-{slug(subject)}"
    out = os.path.expanduser(b.get("out") or f"~/Movies/museai/{name}")
    r = {
        "format": fmt,
        "skill": str(SKILLS / ("muse-video" if fmt == "travel" else fmt) / "SKILL.md"),
        "aspect": aspect,
        "work": out,
        "final": f"{name}.mp4",
        "notes": [],
    }
    if travel:
        r["history"] = cmd(
            "python3",
            SKILLS / "shot-history/scripts/shots.py",
            "check",
            "--place",
            subject,
            "--country",
            b.get("country"),
        )
    music, seconds = b.get("music"), b.get("seconds")
    if fmt == "scenic-drop-reel":
        r["plan"] = (
            cmd(
                "python3",
                SKILLS / "scenic-drop-reel/scripts/pick.py",
                "--place",
                subject,
                "--scope",
                b.get("scope", "place"),
                "--setting",
                b.get("setting", "any"),
                "--country",
                b.get("country"),
                *(("--length", seconds) if seconds else ()),
            )
            + " > plan.json"
        )
        if music:
            r["notes"].append(
                "music: the template + --setting pick the track; a named style goes to music.py --style"
            )
    elif fmt == "zoominview":
        if not b.get("view"):
            sys.exit(
                "zoominview needs view: what is really there (landmarks, terrain, water, vegetation)"
            )
        r["plan"] = (
            cmd(
                "python3",
                SKILLS / "zoominview/scripts/plan.py",
                "--place",
                subject,
                "--setting",
                b.get("setting", "nature"),
                "--light",
                b.get("light", "golden"),
                "--country",
                b.get("country"),
                "--view",
                b["view"],
                *(("--focus", b["focus"]) if b.get("focus") else ()),
                *(("--music", music) if music else ()),
            )
            + " > plan.json"
        )
        if seconds:
            r["notes"].append("seconds: zoominview length follows the reveal (~11-16 s)")
    elif fmt == "travel":
        r["plan"] = (
            f"STYLE=travel SIZE={aspect} DURATION={seconds or 10} OUT_NAME={name}.mp4 NO_OPEN=1 "
            + cmd(
                SKILLS / "muse-video/scripts/muse-video",
                "-f",
                "prompt.txt",
                out,
            )
        )
        r["notes"].append(
            "prompt.txt: PLACE / TIME + WEATHER / SHOTS / MUSIC ("
            + (music or "fits the scenery")
            + ")"
        )
    elif fmt == "scenery-director":
        if not b.get("view"):
            sys.exit(
                "scenery-director needs view: what is really there (landmarks, terrain, water)"
            )
        r["plan"] = cmd(
            "python3",
            SKILLS / "scenery-director/scripts/plan.py",
            "--place",
            subject,
            "--country",
            b.get("country"),
            "--setting",
            b.get("setting", "nature"),
            "--view",
            b["view"],
            *(("--focus", b["focus"]) if b.get("focus") else ()),
            *(("--light", b["light"]) if b.get("light") else ()),
            *(("--seconds", seconds) if seconds else ()),
            "--aspect",
            aspect,
            "--out",
            out,
        )
        if music:
            r["notes"].append(
                "music: plan.py picks an instrumental style; --music <id> to force one"
            )
    else:
        r["notes"].append(f"plan by hand: follow {r['skill']} Steps")
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("brief")
    ap.add_argument(
        "--format", choices=list(FORMATS), help="route to this format instead of brief.format"
    )
    a = ap.parse_args()
    b = json.loads(Path(a.brief).read_text())
    if a.format:
        b["format"] = a.format
    print(json.dumps(route(b), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
