"""Per clip: does the speech hold every planned word, where does it end; then write trims.json.

  uv run --no-project --python 3.12 --with faster-whisper --with soundfile python scripts/audit.py WORK [S03 S07 ...]

Prints one line per shot (BAD under 85 % word recall: re-render it) and writes WORK/review/audit.txt.
WORK/trims.json: a dialogue shot runs to its last word + 0.7 s (never cut mid-line; Ep 1 lost
"cables" to a fixed 4 s trim), at least its planned `seconds`; a silent shot keeps `seconds`.
Only the shots audited are rewritten; adjust a silent shot by hand afterwards if it needs it."""
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import soundfile as sf
from faster_whisper import WhisperModel

work = Path(sys.argv[1])
want = set(sys.argv[2:])
ep = json.loads((work / "episode.json").read_text())
tag = f"aes-ep{ep['episode']:02}"
model = WhisperModel("small", compute_type="int8")
def norm(t):
    return re.findall(r"[a-z0-9']+", t.lower().replace("-", " "))


tp = work / "trims.json"
trims = json.loads(tp.read_text()) if tp.exists() else {}
report = []
for s in ep["shots"]:
    if want and s["id"] not in want:
        continue
    clip = work / "clips" / f"{tag}-{s['id']}.mp4"
    planned = " ".join(ln["en"] for ln in s.get("lines", []))
    wav = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-ac", "1", "-ar", "16000", "-f", "wav", "-"],
                         capture_output=True, check=True).stdout
    a, _ = sf.read(io.BytesIO(wav), dtype="float32")
    dur = len(a) / 16000
    segs = list(model.transcribe(a, language="en", vad_filter=True, word_timestamps=True)[0])
    heard = " ".join(x.text for x in segs).strip()
    pw, hw = norm(planned), set(norm(heard))
    rec = sum(w in hw for w in pw) / len(pw) if pw else 1.0
    end = max((x.end for x in segs), default=0.0)
    line = f"{'BAD ' if pw and rec < 0.85 else 'ok  '}{s['id']} rec {rec:.0%} end {end:.1f}/{dur:.1f}s"
    report += [line, f"     plan: {planned}", f"     said: {heard}"]
    print(report[-3], report[-2], report[-1], sep="\n")
    stop = max(s["seconds"], end + 0.7) if s.get("lines") else s["seconds"]
    trims[s["id"]] = [0.0, round(min(dur - 0.05, stop), 2)]
(work / "review").mkdir(exist_ok=True)
(work / "review" / "audit.txt").write_text("\n".join(report) + "\n")
tp.write_text(json.dumps(trims, indent=1))
print(f"WROTE {tp}")
