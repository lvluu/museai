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
from pypinyin import Style, lazy_pinyin, load_phrases_dict

# pypinyin reads a bare 还车 (recap word) as hái chē; it is huán chē (EP40)
load_phrases_dict({"还车": [["huán"], ["chē"]]})

video, cues = sys.argv[1], json.load(open(sys.argv[2]))
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000",
                      "-f", "s16le", "-"], capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
# large-v3: medium heard correct syllables as wrong ones (EP10: 当然 -> 倒然, 横 -> 行)
model = WhisperModel(os.environ.get("WMODEL", "large-v3"), device="cpu", compute_type="int8")
t2s = opencc.OpenCC("t2s").convert


DIGITS = "零一二三四五六七八九"  # Whisper writes 六点半 as 6点半


def number(m):
    # read a whole number as spoken: Whisper writes 八十块 as 80块, and digit by digit that read 八零 (EP16)
    s = m.group()
    if len(s) > 4 or (len(s) > 1 and s[0] == "0"):
        return "".join(DIGITS[int(d)] for d in s)
    out = ""
    for d, unit in zip(s, ["千", "百", "十", ""][4 - len(s):], strict=True):
        out += "零" if d == "0" else DIGITS[int(d)] + unit
    out = re.sub("零+", "零", out).rstrip("零") or "零"
    return out[1:] if out.startswith("一十") else out


def syl(text):
    s = lazy_pinyin(re.sub(r"[^一-鿿]", "", re.sub(r"\d+", number, text)), style=Style.TONE3, neutral_tone_with_five=True)
    # 3-3 tone sandhi, applied to script and transcript alike: 几点 is spoken jí diǎn, and Whisper
    # writes it as 急点 ji2 (EP14: a correct 几点 failed as ji3 -> ji2). Right to left, so a chain
    # 你几点 becomes nǐ jí diǎn as spoken, not ní jí diǎn
    for i in reversed(range(len(s) - 1)):
        if s[i].endswith("3") and s[i + 1].endswith("3"):
            s[i] = s[i][:-1] + "2"
    return s


def hear(clip):
    segs, _ = model.transcribe(clip, language="zh", vad_filter=False, condition_on_previous_text=False)
    return t2s("".join(x.text for x in segs)).strip()


def check(zh, heard):
    want, got = syl(zh), syl(heard)
    sm = difflib.SequenceMatcher(None, want, got, autojunk=False)
    diffs = [(op, " ".join(want[a1:a2]) or "-", " ".join(got[b1:b2]) or "-")
             for op, a1, a2, b1, b2 in sm.get_opcodes() if op != "equal"]
    # neutral-tone particle swaps (了 le5 -> 啦 la5) are not tone errors
    diffs = [d for d in diffs if not (d[0] == "replace" and all(x.endswith("5") for x in f"{d[1]} {d[2]}".split()))]
    # extra heard syllables are neighbouring lines bleeding in; a missing or changed one is an error
    return sm, diffs, all(op == "insert" for op, *_ in diffs)


fails = []
for i, (s, e, zh, *_) in enumerate(cues):
    # pad with silence: Whisper drops a syllable that starts right at the clip edge (EP10: 不 after the cut)
    pad = np.zeros(8000, np.float32)
    clip = np.concatenate([pad, audio[int(max(s - 0.2, 0) * 16000):int((e + 0.25) * 16000)], pad])
    heard = hear(clip)
    if not heard:  # very short lines (可以, 0.4 s) come back empty when padded; retry on the bare audio
        heard = hear(audio[int(max(s - 0.4, 0) * 16000):int((e + 0.4) * 16000)])
    sm, diffs, ok = check(zh, heard)
    if not ok and i:
        # a 2-syllable line alone is too little audio (EP10 dub: 可以 heard as 课题, but right
        # together with the line before it), so retry with the previous line as context
        ps, _, pzh, *_ = cues[i - 1]
        ctx = hear(np.concatenate([pad, audio[int(max(ps - 0.2, 0) * 16000):int((e + 0.25) * 16000)], pad]))
        csm, cdiffs, cok = check(pzh + zh, ctx)
        if cok:
            heard, sm, diffs, ok = f"{ctx} (with line {i})", csm, cdiffs, True
    print(f"{'ok  ' if ok else 'FAIL'} {i + 1:>2} {sm.ratio():4.0%} {zh}  heard {heard}  "
          + "; ".join(f"{a} -> {b}" for _, a, b in diffs))
    ok or fails.append(str(i + 1))
print("RESULT", "PASS" if not fails else "FAIL lines " + ",".join(fails))
sys.exit(1 if fails else 0)
