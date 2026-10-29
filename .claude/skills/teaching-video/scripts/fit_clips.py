"""Usage: fit_clips.py <fmt_dir> <out_dir> --format 9x16|16x9   (env MAXF, default 1.3 / 1.35 for 16x9)
Fits each rendered 10 s clip (fmt_dir/clipNN.mp4, plan in fmt_dir/clips.json) to its planned span before
ease_seams/stitch:
- speech part = 0 .. muse's last sound + 0.3 s, sped up (setpts + atempo) toward the planned span, at most MAXF;
- the silent tail after it is kept at 3x speed, never cut: a cut tail made the next clip's first frame jump
  against the cut point (4 seam jumps, bi_so_sanh 2026-10-29);
- every part is scaled to the format size: muse returned some clips at 720p and ease_seams failed on the
  shape mismatch.
Lip-sync gate: muse speaks its own, slower reading of the script, so its mouth moves ~9.5 s of each clip
while the dub has 5-9 s of voice for it. When muse's speech still runs > 15 % longer than the plan after
MAXF, the dub puts voice where the lips are closed and lips where the voice is silent (speakers.py FAIL,
0.5-1.2 s per line, bi_so_sanh 2026-10-29). Those clips print MISMATCH and the script exits 1: re-render
them (shorter script lines or a clearer pace line) before joining. FORCE=1 writes the parts anyway.
"""
import json
import os
import subprocess
import sys

import numpy as np

d, out = sys.argv[1], sys.argv[2]
fmt = sys.argv[sys.argv.index("--format") + 1]
wh = {"9x16": "1080:1920", "16x9": "1920:1080"}[fmt]
maxf = float(os.environ.get("MAXF", 1.3 if fmt == "9x16" else 1.35))
os.makedirs(out, exist_ok=True)
clips = json.load(open(f"{d}/clips.json"))["clips"]


def last_sound(path, floor_db=-35.0):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    hop = 320  # 20 ms
    rms = np.sqrt(np.mean(a[: len(a) // hop * hop].reshape(-1, hop) ** 2, 1)) + 1e-9
    db = 20 * np.log10(rms / rms.max())
    loud = np.nonzero(db > floor_db)[0]
    return (loud[-1] + 1) * hop / 16000 if len(loud) else 0.0, len(a) / 16000


bad, total = [], 0.0
for i, c in enumerate(clips):
    n = c["clip"]
    src = f"{d}/clip{n:02d}.mp4"
    span = (clips[i + 1]["start"] - c["start"]) if i + 1 < len(clips) else c["speech"] + 0.4
    said, dur = last_sound(src)
    b = min(dur, said + 0.3)
    f = min(maxf, max(1.0, b / span))
    fitted = b / f
    tail = dur - b
    total += fitted + tail / 3
    flag = ""
    if fitted > span * 1.15:
        flag = f"  MISMATCH: lips run {fitted - span:.1f} s past the voice, re-render"
        bad.append(n)
    print(f"clip{n:02d} speech 0-{b:.2f} x{f:.2f} -> {fitted:.2f} (plan {span:.2f}) +tail {tail / 3:.2f}  "
          f"cum {total:.2f}{flag}")
    fc = (f"[0:v]trim=0:{b},setpts=(PTS-STARTPTS)/{f},scale={wh}:flags=lanczos[v0];"
          f"[0:a]atrim=0:{b},asetpts=PTS-STARTPTS,atempo={f}[a0];")
    if tail > 0.05:
        fc += (f"[0:v]trim={b}:{dur},setpts=(PTS-STARTPTS)/3,scale={wh}:flags=lanczos[v1];"
               f"[0:a]atrim={b}:{dur},asetpts=PTS-STARTPTS,atempo=2,atempo=1.5[a1];"
               "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
    else:
        fc += "[v0]null[v];[a0]anull[a]"
    if not bad or os.environ.get("FORCE") == "1":
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                        "-r", "24", "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", f"{out}/part{n:02d}.mp4"], check=True)
print("RESULT", f"MISMATCH clips {bad}" if bad else "ok")
sys.exit(1 if bad and os.environ.get("FORCE") != "1" else 0)
