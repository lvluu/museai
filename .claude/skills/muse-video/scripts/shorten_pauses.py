"""Usage: shorten_pauses.py video.mp4 out.mp4 [max_gap=1.0] [keep=0.45]
Shortens every pause longer than max_gap s to about keep s by cutting inside the silence and
joining the two sides with a 0.2 s xfade + acrossfade. Nothing is retimed, so lip sync stays.
EP08: four 1-2 s pauses between lines, shortened this way; on a locked camera the dissolves
were invisible and no syllable moved. Run it on the stitched video, before dub.py and cues
(it changes every time after the first cut). Speech spans come from gaps.py (audio energy).
KEEP=12.5-17.0 (comma-separated a-b spans, seconds of the input): pauses inside are left alone, e.g. the
review pauses of a vocabulary recap (EP30: those pauses are wanted, see REVIEW= in pace.py)."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gaps import speech_spans  # noqa: E402

video, out = sys.argv[1], sys.argv[2]
max_gap = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
keep = float(sys.argv[4]) if len(sys.argv) > 4 else 0.45
FADE = 0.2
KEEP = [tuple(map(float, x.split("-"))) for x in os.environ.get("KEEP", "").split(",") if x]

dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                           capture_output=True, text=True, check=True).stdout)
fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                      "-of", "csv=p=0", video], capture_output=True, text=True, check=True).stdout.strip()
spans = speech_spans(video)
pad = (keep + FADE) / 2  # silence left on each side of a cut; the xfade eats FADE of it
segs, start = [], 0.0
for (_, b), (a, _) in zip(spans, spans[1:], strict=False):
    if a - b > max_gap and not any(k0 <= b and a <= k1 for k0, k1 in KEEP):
        segs.append((start, b + pad))
        start = a - pad
        print(f"pause {b:6.2f}-{a:6.2f} ({a - b:.2f} s) -> ~{keep:.2f} s")
segs.append((start, dur))
if len(segs) == 1:
    sys.exit(f"no pause over {max_gap} s; nothing to do")

f, t = [], 0.0
for k, (a, b) in enumerate(segs):
    f.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,fps={fps},settb=1/24[v{k}]")
    f.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{k}]")
v, a_ = "[v0]", "[a0]"
t = segs[0][1] - segs[0][0]
for k in range(1, len(segs)):
    t -= FADE
    f.append(f"{v}[v{k}]xfade=transition=fade:duration={FADE}:offset={t:.3f}[x{k}]")
    f.append(f"{a_}[a{k}]acrossfade=d={FADE}[y{k}]")
    v, a_ = f"[x{k}]", f"[y{k}]"
    t += segs[k][1] - segs[k][0]
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-filter_complex", ";".join(f), "-map", v, "-map", a_,
                "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", out], check=True)
print(f"WROTE {out}  {dur:.2f} s -> {t:.2f} s")
