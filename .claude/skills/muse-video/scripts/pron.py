"""Usage: pron.py video.mp4 cues.json  -> per-line Mandarin pronunciation check.
Transcribes each cue's audio on its own (no script hint, VAD off) and compares the
toned pinyin of what Whisper heard with the toned pinyin of the script. A wrong tone
or syllable makes Whisper hear a different word (EP10 small model: 横 héng -> 哼 hēng),
while a homophone with the same tones counts as correct. Per-line audio avoids the
whole-file transcript dropping words at chunk edges (EP10: 不 of 不好意思 lost).
Fails when a script syllable is missing or heard with another sound or tone.
Run: uv run --no-project --python 3.12 --with faster-whisper --with pypinyin
     --with opencc-python-reimplemented python pron.py video.mp4 cues.json
"""
import difflib
import json
import os
import re
import subprocess
import sys

import numpy as np
import opencc
from faster_whisper import WhisperModel
from pypinyin import Style, lazy_pinyin

video, cues = sys.argv[1], json.load(open(sys.argv[2]))
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000",
                      "-f", "s16le", "-"], capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
# large-v3: medium heard correct syllables as wrong ones (EP10: 当然 -> 倒然, 横 -> 行)
model = WhisperModel(os.environ.get("WMODEL", "large-v3"), device="cpu", compute_type="int8")
t2s = opencc.OpenCC("t2s").convert


def syl(text):
    return lazy_pinyin(re.sub(r"[^一-鿿]", "", text), style=Style.TONE3, neutral_tone_with_five=True)


def hear(clip):
    segs, _ = model.transcribe(clip, language="zh", vad_filter=False, condition_on_previous_text=False)
    return t2s("".join(x.text for x in segs)).strip()


fails = []
for i, (s, e, zh, *_) in enumerate(cues):
    # pad with silence: Whisper drops a syllable that starts right at the clip edge (EP10: 不 after the cut)
    pad = np.zeros(8000, np.float32)
    clip = np.concatenate([pad, audio[int(max(s - 0.2, 0) * 16000):int((e + 0.25) * 16000)], pad])
    heard = hear(clip)
    if not heard:  # very short lines (可以, 0.4 s) come back empty when padded; retry on the bare audio
        heard = hear(audio[int(max(s - 0.4, 0) * 16000):int((e + 0.4) * 16000)])
    want, got = syl(zh), syl(heard)
    sm = difflib.SequenceMatcher(None, want, got, autojunk=False)
    diffs = [(op, " ".join(want[a1:a2]) or "-", " ".join(got[b1:b2]) or "-")
             for op, a1, a2, b1, b2 in sm.get_opcodes() if op != "equal"]
    # neutral-tone particle swaps (了 le5 -> 啦 la5) are not tone errors
    diffs = [d for d in diffs if not (d[0] == "replace" and all(x.endswith("5") for x in f"{d[1]} {d[2]}".split()))]
    # extra heard syllables are neighbouring lines bleeding in; a missing or changed one is an error
    ok = all(op == "insert" for op, *_ in diffs)
    print(f"{'ok  ' if ok else 'FAIL'} {i + 1:>2} {sm.ratio():4.0%} {zh}  heard {heard}  "
          + "; ".join(f"{a} -> {b}" for _, a, b in diffs))
    ok or fails.append(str(i + 1))
print("RESULT", "PASS" if not fails else "FAIL lines " + ",".join(fails))
sys.exit(1 if fails else 0)
