"""Usage: gaps.py video.mp4 [threshold_db=-28]  -> speech spans and the silent gaps between them.
Measured from audio energy (50 ms windows, spans < 0.25 s apart merged), not from Whisper,
whose word starts absorb leading silence. Use it to find where to cut a pause, and to check
the pace rule (no gap > 1.0 s) before QA."""
import math
import struct
import subprocess
import sys

video = sys.argv[1]
thr = float(sys.argv[2]) if len(sys.argv) > 2 else -28
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
s = struct.unpack(f"<{len(pcm) // 2}h", pcm)
W = 800  # 50 ms at 16 kHz
loud = []
for i in range(0, len(s) - W, W):
    rms = math.sqrt(sum(x * x for x in s[i:i + W]) / W)
    loud.append(20 * math.log10(rms / 32768 + 1e-9) > thr)

spans, start = [], None
for i, on in enumerate(loud + [False]):
    if on and start is None:
        start = i
    if not on and start is not None:
        if i - start >= 2:
            spans.append([start * 0.05, i * 0.05])
        start = None
merged = []
for a, b in spans:
    if merged and a - merged[-1][1] < 0.25:
        merged[-1][1] = b
    else:
        merged.append([a, b])

prev = None
for a, b in merged:
    gap = "" if prev is None else f"   gap {a - prev:4.2f}s" + ("  LONG" if a - prev > 1.0 else "")
    print(f"{a:6.2f}-{b:6.2f}{gap}")
    prev = b
