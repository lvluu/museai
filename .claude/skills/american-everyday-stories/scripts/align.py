"""Align the planned subtitles to the real speech of the assembled film.

  uv run --no-project --python 3.12 --with faster-whisper python scripts/align.py film.mp4 WORK

Reads WORK/cues.provisional.json and WORK/cut.json (assemble.py cut), transcribes the film in
English with word timestamps (WMODEL, default medium) and writes:
  WORK/words.json  [{"w", "s", "e"}, ...]
  WORK/cues.json   [[start, end, en, zh, KEY], ...] on the real speech
Each cue's words are matched (difflib) only against unused words heard within WIN s of its planned
time plus the drift of the last heard line, so repeated lines and skipped words don't pull
cues apart. A cue with no matched word keeps its planned time moved into the film (UNMATCHED: check by ear, the line may be missing).
Never stretch audio to fit the subtitles; the subtitles follow the speech."""
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

film, work = sys.argv[1], Path(sys.argv[2])
planned = json.loads((work / "cues.provisional.json").read_text())
cut = json.loads((work / "cut.json").read_text())

pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", film, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
WIN = float(os.environ.get("WIN", 4))
model = WhisperModel(os.environ.get("WMODEL", "medium"), device="cpu", compute_type="int8")
segments, _ = model.transcribe(audio, language="en", word_timestamps=True, vad_filter=True,
                                  condition_on_previous_text=False)  # no skipped or invented repeats
words = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for seg in segments for w in seg.words]
(work / "words.json").write_text(json.dumps(words))


def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower().replace("’", "'"))


used, cues, heard = set(), [], 0
shift = -cut[0]["trim_start"] if cut else 0.0  # planned time -> film time, updated by each heard line
for s, e, en, zh, who in planned:
    want = [norm(x) for x in en.split() if norm(x)]
    pool = [k for k, w in enumerate(words) if k not in used and s + shift - WIN <= w["s"] <= e + shift + WIN]
    sm = difflib.SequenceMatcher(None, want, [norm(words[k]["w"]) for k in pool], autojunk=False)
    got = [pool[b + i] for _, b, n in sm.get_matching_blocks() for i in range(n)]
    if got:
        while got[0] > 0 and got[0] - 1 not in used and words[got[0]]["s"] - words[got[0] - 1]["e"] < 0.4:
            got.insert(0, got[0] - 1)  # a misheard first word ("Hoppin" for "Hop in") still opens the line
        used.update(range(got[0], got[-1] + 1))
        hit = [words[k] for k in got]
        cues.append([hit[0]["s"], hit[-1]["e"], en, zh, who])
        shift, heard = hit[0]["s"] - s, heard + 1
        if len(got) / max(1, len(want)) < 0.6:
            print(f"PARTIAL {len(got) / max(1, len(want)):.0%} {hit[0]['s']:6.2f} {en}")
    else:
        cues.append([round(s + shift, 2), round(e + shift, 2), en, zh, who])
        print(f"UNMATCHED {s + shift:6.2f} {en}")
(work / "cues.json").write_text(json.dumps(cues, ensure_ascii=False, indent=1))
print(f"aligned {heard}/{len(planned)} cues -> {work / 'cues.json'}")
