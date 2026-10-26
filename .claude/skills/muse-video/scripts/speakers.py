"""Usage: speakers.py video.mp4 cues.json SPEAKERS mouths.jpg
       speakers.py video.mp4 script.txt words.json mouths.jpg   (one clip, before captions)
  uv run --no-project --python 3.12 --with mediapipe==0.10.14 --with opencv-python-headless --with librosa \\
      python scripts/speakers.py video.mp4 cues.json WWMWMWMWMWMW mouths.jpg

Checks that the right person says each line. SPEAKERS has one letter per cue: W = woman, M = man.
FEMALE=W (env) names who has the higher voice. script.txt has "W: line" / "M: line" per line; the
line times come from aligning it to words.json (transcribe.py / check_clip.sh output).
  voice   median pitch per cue (pyin): female > 165 Hz, male < 165 Hz; must fit the speaker.
          Automatic: exit 1 on a mismatch.
  mouths  writes mouths.jpg: one column per cue (labelled "n W" / "n M"), 6 frames down, each a
          full-width band around the mouths, so every visible mouth is in the strip. LOOK AT IT:
          only the labelled speaker's lips may move; the listener's stay closed and still.
          A listener whose lips open and change shape with the other voice is a lip-sync failure
          (EP09: the man mimed 3 of the woman's lines). Lip landmarks (face mesh) could not tell
          a miming listener from a silent one at this size, so this check stays visual."""
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile

import cv2
import librosa
import mediapipe as mp
import numpy as np

video, sheet = sys.argv[1], sys.argv[-1]
if sys.argv[2].endswith(".json"):  # cues.json SPEAKERS
    cues, who = json.load(open(sys.argv[2])), sys.argv[3].upper()
else:  # script.txt words.json: line times from aligning the script to the transcript
    lines = [t.split(":", 1) for t in open(sys.argv[2], encoding="utf-8") if ":" in t]
    who = "".join(x[0].strip()[0].upper() for x in lines)
    words = json.load(open(sys.argv[3]))
    chars = [(ch, w["s"] + (w["e"] - w["s"]) * k / len(w["w"])) for w in words for k, ch in enumerate(w["w"])]
    han = lambda t: re.findall(r"[一-鿿]", t)  # noqa: E731
    script = [(i, ch) for i, (_, t) in enumerate(lines) for ch in han(t)]
    heard = [(ch, t) for ch, t in chars if han(ch)]
    sm = difflib.SequenceMatcher(None, [c for _, c in script], [c for c, _ in heard], autojunk=False)
    times = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            times.setdefault(script[blk.a + k][0], []).append(heard[blk.b + k][1])
    cues = [[min(times[i]), max(times[i]) + 0.2, t.strip()] if i in times else [0, 0, t.strip()]
            for i, (_, t) in enumerate(lines)]
if len(who) != len(cues):
    sys.exit(f"SPEAKERS has {len(who)} letters for {len(cues)} cues")
female = os.environ.get("FEMALE", "W")
SPLIT_HZ = 165
ROWS, BAND = 6, 0.14  # frames per cue, band height as a fraction of the frame height

# voice
with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-ac", "1", "-ar", "16000", wav.name], check=True)
    y, sr = librosa.load(wav.name, sr=16000)
f0, voiced, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr, frame_length=1024)
f0_t = librosa.times_like(f0, sr=sr, hop_length=256)

# mouths
cap = cv2.VideoCapture(video)
det = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.3)
mouth_y = None  # the camera is locked, so the last mouth height stays valid when detection misses


def strip(t):
    global mouth_y
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, img = cap.read()
    if not ok:
        return None
    H, W = img.shape[:2]
    found = det.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).detections or []
    if found:
        r = [d.location_data.relative_bounding_box for d in found]
        mouth_y = float(np.mean([(b.ymin + 0.78 * b.height) for b in r])) * H
    cy = mouth_y if mouth_y is not None else 0.4 * H
    h = int(BAND * H)
    y0 = int(min(max(cy - h / 2, 0), H - h))
    return cv2.resize(img[y0:y0 + h], (360, int(360 * h / W)))


bad, cols = [], []
for i, (c, s) in enumerate(zip(cues, who, strict=True)):
    a, b = c[0], c[1]
    sel = (f0_t >= a) & (f0_t <= b) & voiced
    hz = float(np.nanmedian(f0[sel])) if sel.any() else float("nan")
    ok = np.isnan(hz) or ((hz > SPLIT_HZ) == (s == female))
    print(f"{i + 1:2d} {a:6.2f}-{b:6.2f} {s} {hz:5.0f}Hz  {c[2]}" + ("" if ok else "  <-- WRONG VOICE"))
    if not ok:
        bad.append(i + 1)
    tiles = [x for t in np.linspace(a + 0.1, max(a + 0.1, b - 0.1), ROWS) if (x := strip(t)) is not None]
    head = np.full((40, 360, 3), 255, np.uint8)
    cv2.putText(head, f"{i + 1} {s}", (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cols.append(np.vstack([head, *tiles]))
h = max(x.shape[0] for x in cols)
cols = [np.vstack([x, np.full((h - x.shape[0], 360, 3), 255, np.uint8)]) for x in cols]
cv2.imwrite(sheet, np.hstack([np.hstack([x, np.full((h, 6, 3), 255, np.uint8)]) for x in cols]))
print(f"mouths: {sheet}  (look: only the labelled speaker's lips move in each column)")
print(f"RESULT voice {'FAIL lines ' + ','.join(map(str, bad)) if bad else 'ok'}")
sys.exit(1 if bad else 0)
