"""Usage: transcribe.py video.mp4 out.json [hint text]  -> word timestamps (zh)."""
import json
import os
import subprocess
import sys

import numpy as np
from faster_whisper import WhisperModel

video, out = sys.argv[1], sys.argv[2]
# The default hint keeps output in simplified characters (the scripts are simplified).
hint = sys.argv[3] if len(sys.argv) > 3 else "以下是普通话的句子。"
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000",
                      "-f", "s16le", "-"], capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
model = WhisperModel(os.environ.get("WMODEL","small"), device="cpu", compute_type="int8")
# Whisper skips most of a stitched multi-clip file in one pass (it jumped from 3 s to 30 s on
# a 32 s video), so transcribe ~10 s chunks, each cut at the quietest 50 ms between 8 and 12 s.
SR, HOP = 16000, 800
energy = np.convolve(audio ** 2, np.ones(HOP), "valid")[::HOP]
cuts = [0]
while len(audio) - cuts[-1] > 12 * SR:
    lo, hi = (cuts[-1] + 8 * SR) // HOP, (cuts[-1] + 12 * SR) // HOP
    cuts.append((lo + int(np.argmin(energy[lo:hi]))) * HOP)
cuts.append(len(audio))
words = []
for a, b in zip(cuts, cuts[1:]):
    segments, _ = model.transcribe(audio[a:b], language="zh", word_timestamps=True,
                                   initial_prompt=hint, condition_on_previous_text=False,
                                   vad_filter=os.environ.get("VAD", "0") == "1",
                                   vad_parameters=dict(threshold=0.2, speech_pad_ms=300))
    t = a / SR
    for seg in segments:
        print(f"{seg.start + t:6.2f}-{seg.end + t:6.2f} {seg.text}")
        words += [{"w": w.word, "s": round(w.start + t, 2), "e": round(w.end + t, 2)} for w in seg.words]
json.dump(words, open(out, "w"), ensure_ascii=False)
