"""Usage: dub.py video.mp4 cues.json SPEAKERS out.mp4
  uv run --no-project --python 3.12 --with edge-tts --with librosa --with soundfile \\
      python scripts/dub.py video.mp4 cues.json WMWMWMWMWMWW dubbed.mp4

Replaces the dialogue with one fixed neural voice per person, timed to the original lips.
Every muse render picks its own voices, so a multi-clip video changes voice at each seam
(EP08: the woman went 258 -> 183 -> 229 Hz across 4 clips, the clerk 101-142 Hz, with a
different timbre and accent each time). Dubbing every line with the same voice fixes that.
  voices  VOICE_W (default zh-CN-XiaoxiaoNeural), VOICE_M (default zh-CN-YunjianNeural):
          standard Putonghua. SPEAKERS has one letter per cue (W / M).
  timing  each cue's speech span comes from the original audio (loud frames inside the cue).
          A line whose commas match the original's pauses (> 0.15 s) is synthesised per
          comma part and each part is placed on its own span; otherwise the whole line
          is placed on the whole span. Each part starts on the lips and plays at the voice's
          own speed; it may run on into the silence after, up to the next part or speaker.
          Only when it would not fit there does the voice speak faster itself (edge-tts rate,
          up to MAX_PCT, default +20 %). Never time-stretched or slowed: EP08 v4/v5 used
          +40 % and a phase-vocoder stretch, and the user heard a pitched, unnatural voice.
          OVERRUN marks a part that still runs into the next one. MAX_PCT can be lowered, never
          raised above 20. The voice is never pitch-shifted, slowed or time-stretched (no
          librosa time_stretch / pitch_shift here): EP08 v4-v5 used them and sounded pitched.
  out     dubbed.mp4 and dubbed.cues.json: the cues retimed to the new voice. Burn captions
          and run qa.py / speakers.py with them; the old cues end with the lips, so captions
          vanish early and qa reads the voice as too fast (EP08: 5.6-5.7 syl/s on the lips'
          spans for lines the voice says at a normal pace)."""
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
voices = {"W": os.environ.get("VOICE_W", "zh-CN-XiaoxiaoNeural"), "M": os.environ.get("VOICE_M", "zh-CN-YunjianNeural")}
SR, HOP = 24000, 120  # 5 ms frames
MAX_PCT = min(20, int(os.environ.get("MAX_PCT", 20)))  # faster sounds hurried and pitched; hard cap
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
voice_cues = []  # the same cues, timed to the new voice: captions and the pace check use these
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
        # room: up to the next part, or the next speaker; never slowed, never time-stretched
        room = (spans[k + 1][0] - 0.05 if k + 1 < len(spans) else nxt - 0.12) - a
        y = tts(p, voices[s], f"{i}_{k}")
        pct = int(np.clip(np.ceil((len(y) / SR / room - 1) * 100), 0, MAX_PCT))
        if pct >= 3:
            y = tts(p, voices[s], f"{i}_{k}", pct)
        dur = len(y) / SR
        flag = "  OVERRUN" if dur > room else ""
        print(f"{i + 1:2d}.{k} {s} lips {a:6.2f}-{b:6.2f} voice {dur:4.2f}s ({dur / (b - a):4.2f}x) tts {pct:+3d}%  {p}{flag}")
        y = y / (np.sqrt(np.mean(y**2)) + 1e-9) * 0.08  # same loudness for every line
        fade = np.minimum(1, np.minimum(np.arange(len(y)), np.arange(len(y))[::-1]) / (0.01 * SR))
        o = int(a * SR)
        track[o : o + len(y)] += y * fade
        end = a + len(y) / SR
    voice_cues.append([round(spans[0][0], 2), round(end, 2), *c[2:]])
track = track[: len(orig)] / max(1.0, np.abs(track).max() / 0.85)
sf.write(f"{tmp}/dub.wav", track, SR)
subprocess.run(
    ["ffmpeg", "-v", "error", "-y", "-i", video, "-i", f"{tmp}/dub.wav", "-map", "0:v", "-map", "1:a",
     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out],
    check=True,
)
json.dump(voice_cues, open(out.rsplit(".", 1)[0] + ".cues.json", "w"), ensure_ascii=False, indent=1)
print(f"dubbed: {out}  cues timed to the voice: {out.rsplit('.', 1)[0]}.cues.json (caption and QA with these)")
