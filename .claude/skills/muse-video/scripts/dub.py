"""Usage: dub.py video.mp4 cues.json SPEAKERS out.mp4
  uv run --no-project --python 3.12 --with edge-tts --with librosa --with soundfile \\
      python scripts/dub.py video.mp4 cues.json WMWMWMWMWMWW dubbed.mp4

Replaces the dialogue with one fixed neural voice per person, timed to the original lips.
Every muse render picks its own voices, so a multi-clip video changes voice at each seam
(EP08: the woman went 258 -> 183 -> 229 Hz across 4 clips, the clerk 101-142 Hz, with a
different timbre and accent each time). Dubbing every line with the same voice fixes that.
  voices  VOICE_W (default zh-CN-XiaoxiaoNeural), VOICE_M (default zh-CN-YunyangNeural):
          standard Putonghua. SPEAKERS has one letter per cue (W / M).
  timing  each cue's speech span comes from the original audio (loud frames inside the cue).
          A line whose commas match the original's pauses (> 0.15 s) is synthesised per
          comma part and each part is stretched onto its own span; otherwise the whole line
          is stretched onto the whole span. The voice first speaks faster / slower itself
          (edge-tts rate, -20 % .. +40 %); librosa time_stretch only fixes the rest.
          A remaining ratio outside 0.75-1.33 is printed as STRETCH, since such a line sounds rushed or slow."""
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile

import edge_tts
import librosa
import numpy as np
import soundfile as sf

video, cues_path, who, out = sys.argv[1], sys.argv[2], sys.argv[3].upper(), sys.argv[4]
cues = json.load(open(cues_path))
if len(who) != len(cues):
    sys.exit(f"SPEAKERS has {len(who)} letters for {len(cues)} cues")
voices = {"W": os.environ.get("VOICE_W", "zh-CN-XiaoxiaoNeural"), "M": os.environ.get("VOICE_M", "zh-CN-YunyangNeural")}
SR, HOP = 24000, 120  # 5 ms frames
tmp = tempfile.mkdtemp()

subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-ac", "1", "-ar", str(SR), f"{tmp}/orig.wav"], check=True)
orig, _ = librosa.load(f"{tmp}/orig.wav", sr=SR)
db = librosa.amplitude_to_db(librosa.feature.rms(y=orig, frame_length=4 * HOP, hop_length=HOP)[0], ref=np.max)


def loud_runs(a, b, gap=0.15):
    """Speech runs inside [a, b] of the original, split at silences longer than gap."""
    i0, i1 = max(0, int(a * SR / HOP)), int(b * SR / HOP)
    on = db[i0:i1] > -35
    runs, start, last, quiet = [], None, 0, 0
    for k, v in enumerate(on):
        if v:
            if start is None:
                start = k
            elif quiet * HOP / SR > gap:
                runs.append([start, last + 1])
                start = k
            last, quiet = k, 0
        elif start is not None:
            quiet += 1
    if start is not None:
        runs.append([start, last + 1])
    return [((i0 + s) * HOP / SR, (i0 + e) * HOP / SR) for s, e in runs]


async def say(text, voice, path, pct):
    await edge_tts.Communicate(text, voice, rate=f"{pct:+d}%").save(path)


def tts(text, voice, n, pct=0):
    asyncio.run(say(text, voice, f"{tmp}/{n}.mp3", pct))
    y, _ = librosa.load(f"{tmp}/{n}.mp3", sr=SR)
    y, _ = librosa.effects.trim(y, top_db=35)
    return y


track = np.zeros(len(orig) + SR)
for i, (c, s) in enumerate(zip(cues, who, strict=True)):
    text = c[2]
    lo = max(c[0] - 0.05, cues[i - 1][1] if i else 0)
    hi = min(c[1] + 0.05, cues[i + 1][0] if i + 1 < len(cues) else c[1] + 0.05)
    nxt = cues[i + 1][0] if i + 1 < len(cues) else len(orig) / SR
    runs = [r for r in loud_runs(lo, hi) if r[1] - r[0] > 0.06]
    if not runs:
        sys.exit(f"cue {i + 1}: no speech found in the original between {c[0]} and {c[1]}")
    parts = [p for p in re.split(r"(?<=[，,、])", text) if p.strip()]
    if len(parts) == len(runs) > 1:
        spans = runs
    else:
        parts, spans = [text], [(runs[0][0], runs[-1][1])]
    for k, (p, (a, b)) in enumerate(zip(parts, spans, strict=True)):
        if k == len(parts) - 1 and (len(tts(p, voices[s], "probe")) / SR) / (b - a) > 1.6:
            b = min(b + 0.12, nxt - 0.08)  # too fast to say on the lips' span: run into the pause after
        y = tts(p, voices[s], f"{i}_{k}")
        rate = (len(y) / SR) / (b - a)
        pct = int(np.clip(round((rate - 1) * 100), -20, 40))  # the voice itself speeds up / slows down
        if abs(pct) >= 5:
            y = tts(p, voices[s], f"{i}_{k}", pct)
            rate = (len(y) / SR) / (b - a)
        flag = "" if 0.75 <= rate <= 1.33 else "  STRETCH"
        print(f"{i + 1:2d}.{k} {s} {a:6.2f}-{b:6.2f} tts {pct:+3d}% x{rate:4.2f}  {p}{flag}")
        y = librosa.effects.time_stretch(y, rate=rate)
        y = y / (np.sqrt(np.mean(y**2)) + 1e-9) * 0.08  # same loudness for every line
        fade = np.minimum(1, np.minimum(np.arange(len(y)), np.arange(len(y))[::-1]) / (0.01 * SR))
        o = int(a * SR)
        track[o : o + len(y)] += y * fade
track = track[: len(orig)] / max(1.0, np.abs(track).max() / 0.85)
sf.write(f"{tmp}/dub.wav", track, SR)
subprocess.run(
    ["ffmpeg", "-v", "error", "-y", "-i", video, "-i", f"{tmp}/dub.wav", "-map", "0:v", "-map", "1:a",
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out],
    check=True,
)
print(f"dubbed: {out}")
