"""Voice-clone TTS worker for dub.py (F5-TTS, zero-shot, Mandarin + English).
  uv run -q --no-project --python 3.11 --with f5-tts --with faster-whisper --with pypinyin \\
      python scripts/clone_tts.py
Reads one JSON request per stdin line: {"ref": wav, "ref_text": str, "text": str, "out": wav,
"speed": 1.0} and prints {"out": wav, "heard": str, "ok": bool} when the file is written. The
models load once (~1.3 GB F5 + ~3 GB Whisper from Hugging Face on first use), then ~15-30 s per
line on a Mac CPU.
F5 now and then puts a sound before the line (付好了 -> 付付好了 / 还复好了, 请问 -> 就请问: 5 of 36
test lines from the bank). Whisper (large-v3) checks each take and a mismatch is regenerated with
the next seed, up to SEEDS takes. Some voice + line pairs add the sound on every seed, speed and
duration (W-mid-01 + 付好了: 合幅 / 也复 / 安抚 ...); then the line is said after "……": the stray
sound lands before that pause ("哦，付好了") and is cut off at the quietest point before the line's
first word. ok false means no take was heard right and dub.py names the line.
Seeds are fixed (7, 8, ...), so regenerating a line gives the same take."""
import json
import re
import sys

import librosa
import numpy as np
import soundfile as sf
from f5_tts.api import F5TTS
from faster_whisper import WhisperModel
from pypinyin import lazy_pinyin

SEEDS = 4
reply = sys.stdout
sys.stdout = sys.stderr  # f5_tts prints progress to stdout; keep that pipe for replies only
tts = F5TTS(model="F5TTS_v1_Base")
asr = WhisperModel("large-v3", device="cpu", compute_type="int8")


def syl(t):
    # number words out: Whisper writes 五十块 as 50块
    return lazy_pinyin(re.sub(r"[^一-鿿]|[零一二三四五六七八九十百千两]", "", t))


def hear(path, words=False):
    y, _ = librosa.load(path, sr=16000)
    pad = np.zeros(8000, np.float32)  # Whisper drops a syllable that starts right at the clip edge
    segs, _ = asr.transcribe(np.concatenate([pad, y, pad]), language="zh", vad_filter=False, condition_on_previous_text=False,
                             word_timestamps=words)
    segs = list(segs)
    ws = [(w.start - 0.5, w.end - 0.5, w.word) for s in segs for w in s.words or []]
    return "".join(s.text for s in segs).strip(), ws


def cut_lead(path, first):
    """Drop what F5 said before the "……" pause: cut at the quietest 10 ms before the line's first word."""
    _, ws = hear(path, words=True)
    k = next((i for i, w in enumerate(ws) if i and syl(w[2])[:1] == [first]), None)
    if k is None:
        return False
    y, sr = sf.read(path)
    a, b = int(ws[k - 1][1] * sr), int((ws[k][0] + 0.08) * sr)
    a = max(0, min(a, b - int(0.05 * sr)))
    hop = sr // 100
    e = librosa.feature.rms(y=y[a:b], frame_length=2 * hop, hop_length=hop)[0]
    sf.write(path, y[a + int(np.argmin(e)) * hop:], sr)
    return True


def say(r, text, seed):
    tts.infer(r["ref"], r["ref_text"], text, speed=r.get("speed", 1.0), seed=seed,
              file_wave=r["out"], show_info=lambda *a, **k: None)


for line in sys.stdin:
    r = json.loads(line)
    want = syl(r["text"])
    takes = [(r["text"], s) for s in range(7, 7 + SEEDS)] + [("……" + r["text"], s) for s in (7, 8)]
    for text, seed in takes:
        say(r, text, seed)
        if text != r["text"] and want and not cut_lead(r["out"], want[0]):
            heard = ""
            continue
        heard = hear(r["out"])[0]
        # toneless: Whisper's tones on a short clip are unreliable; pron.py checks tones on the video
        if syl(heard) == want or not want:
            break
    print(json.dumps({"out": r["out"], "heard": heard, "ok": syl(heard) == want}, ensure_ascii=False),
          file=reply, flush=True)
