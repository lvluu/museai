#!/usr/bin/env python3
"""Quality gate for an assembled episode, before the title and subtitles are burned in.

  python3 scripts/qa_episode.py film.mp4 WORK [sheet.jpg]     # exit 1 on any FAIL

Needs WORK/cut.json (assemble.py cut), WORK/cues.json + WORK/words.json (align.py) and
WORK/speakers.txt (episode.py build; line 1 = character letters). muse-video's shared qa.py is
built for 9:16 Mandarin, so this gate reuses its jumps.py / voices.py and checks English itself:
  format   1920x1080, 24-30 fps, 120-180 s
  sound    peak < -0.5 dB, mean > -30 dB
  cuts     hard cuts only at the planned shot joins (a muse self-cut inside a shot = FAIL)
  words    each line heard >= 85 % (letters of the Whisper words inside the cue vs the script)
  pace     speech inside each line of >= 4 words at 120-270 words/min (natural conversation runs
           ~130-160 wpm overall, ~5 syllables/s inside a phrase), fastest / slowest <= 1.6 (one steady pace)
  smooth   no one-frame picture jump (jumps.py) except at planned joins
  voices   each character keeps one voice across shots (voices.py; VOICES=0 skips it, the
           check needs a uv env with resemblyzer)
  sheet    one frame mid-line per cue + mid each silent shot: check faces, wardrobe, period
           details and the listener's mouth by eye."""
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MV = Path(os.environ.get("MUSE_VIDEO", Path.home() / "Work/museai-main/.claude/skills/muse-video")) / "scripts"
film, work = sys.argv[1], Path(sys.argv[2])
sheet = sys.argv[3] if len(sys.argv) > 3 else str(work / "sheet.jpg")
cut = json.loads((work / "cut.json").read_text())
cues = json.loads((work / "cues.json").read_text())
words = json.loads((work / "words.json").read_text())
letters = (work / "speakers.txt").read_text().split()[0]
fails = []


def report(name, ok, msg):
    print(f"{'ok  ' if ok else 'FAIL'} {name:7} {msg}")
    if not ok:
        fails.append(name)


def sh(args):
    return subprocess.run(args, capture_output=True, text=True)


p = json.loads(sh(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height,r_frame_rate",
                   "-show_entries", "format=duration", "-of", "json", film]).stdout)
st, dur = p["streams"][0], float(p["format"]["duration"])
num, den = map(int, st["r_frame_rate"].split("/"))
fps = num / den
report("format", (st["width"], st["height"]) == (1920, 1080) and 24 <= fps <= 30 and 120 <= dur <= 180,
       f"{st['width']}x{st['height']} {fps:.2f} fps {dur:.1f} s")

vol = sh(["ffmpeg", "-i", film, "-af", "volumedetect", "-vn", "-f", "null", "-"]).stderr
mean = float(re.search(r"mean_volume: (-?[\d.]+)", vol).group(1))
peak = float(re.search(r"max_volume: (-?[\d.]+)", vol).group(1))
report("sound", peak < -0.5 and mean > -30, f"peak {peak} dB, mean {mean} dB")

joins = [c["film_start"] for c in cut[1:]]
sc = sh(["ffmpeg", "-i", film, "-vf", "select='gt(scene,0.3)',showinfo", "-an", "-f", "null", "-"]).stderr
found = [float(x) for x in re.findall(r"pts_time:([\d.]+)", sc)]
extra = [t for t in found if all(abs(t - j) > 0.25 for j in joins)]
report("cuts", not extra, f"{len(joins)} planned, extra cuts at {[round(t, 2) for t in extra]}" if extra
       else f"{len(joins)} planned joins, no cut inside a shot")


def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower().replace("’", "'"))


bad_words, rates = [], []
for s, e, en, *_ in cues:
    said = [w for w in words if s - 0.15 <= w["s"] <= e + 0.15]
    want = "".join(norm(x) for x in en.split())
    got = "".join(norm(w["w"]) for w in said)  # letters, so "Hoppin" still counts for "Hop in"
    m = sum(n for *_, n in difflib.SequenceMatcher(None, want, got, autojunk=False).get_matching_blocks())
    if m / max(1, len(want)) < 0.85:
        bad_words.append(f"{s:.1f}s {m / max(1, len(want)):.0%} {en!r}")
    if len(said) >= 4:  # speaking rate inside the line, pauses between lines excluded
        rates.append((len(said) / max(0.3, said[-1]["e"] - said[0]["s"]) * 60, s, en))
report("words", not bad_words, "; ".join(bad_words) or f"{len(cues)} lines heard")
slow = [r for r in rates if not 120 <= r[0] <= 270]
spread = max(r[0] for r in rates) / min(r[0] for r in rates) if rates else 1
report("pace", not slow and spread <= 1.6,
       "; ".join(f"{r:.0f} wpm at {s:.1f}s {en!r}" for r, s, en in slow) or f"spread {spread:.2f}")

jm = sh([sys.executable, str(MV / "jumps.py"), film]).stdout
jt = [float(x) for x in re.findall(r"JUMP\s+([\d.]+)s", jm)]
inside = [t for t in jt if all(abs(t - j) > 0.1 for j in joins)]
report("smooth", not inside, f"one-frame jumps inside shots at {inside}" if inside else "no jumps inside shots")

if os.environ.get("VOICES", "1") != "0" and len(set(letters)) < len(letters):
    v = sh(["uv", "run", "--no-project", "--python", "3.11", "--with", "resemblyzer", "--with", "librosa", "--with",
            "setuptools", "python", str(MV / "voices.py"), film, str(work / "cues.json"), letters])
    report("voices", v.returncode == 0, (v.stdout.strip().splitlines() or [v.stderr.strip()[-200:]])[-1])

times = [(s + e) / 2 for s, e, *_ in cues]
times += [c["film_start"] + c["seconds"] / 2 for c in cut
          if not any(c["film_start"] <= t < c["film_start"] + c["seconds"] for t in times)]
sel = "+".join(f"between(t,{t:.2f},{t + 0.04:.2f})" for t in sorted(times))
cols = 6
sh(["ffmpeg", "-v", "error", "-y", "-i", film, "-vf",
    f"select='{sel}',scale=320:-1,tile={cols}x{-(-len(times) // cols)}", "-frames:v", "1", "-vsync", "vfr", sheet])
print(f"sheet {sheet} ({len(times)} frames): check faces, wardrobe, period details, listeners' mouths")
print("RESULT", "PASS" if not fails else f"FAIL {', '.join(fails)}")
sys.exit(1 if fails else 0)
