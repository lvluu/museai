"""Usage: lipsync.py video.mp4 cues.json speakers [planned cut times...]

speakers: one letter per cue, left-to-right people are L and R, intro/solo shots use C,
e.g. "CLRLRLRLRLL". Checks per cue that the speaker's mouth moves and the listener's
does not. Talking = the lip gap opening and closing every frame; a smiling listener keeps
a steady gap. EP10 (man in near profile): 4 of 11 cues had the listener's lips moving as
much as the speaker's. Lip-gap vs voice-loudness correlation was tried and dropped: it
scored 0.0-0.4 with random lags on every episode, good or bad, so it cannot gate.
Run: uv run --no-project --python 3.12 --with "mediapipe==0.10.14" --with opencv-python-headless
     python lipsync.py video.mp4 cues.json CLRLRLRLRLL 3.17
"""
import json
import sys

import cv2
import mediapipe as mp
import numpy as np

video, cues_path, speakers = sys.argv[1], sys.argv[2], sys.argv[3]
cuts = [float(c) for c in sys.argv[4:]]
cues = json.load(open(cues_path))
assert len(speakers) == len(cues), f"{len(speakers)} speakers for {len(cues)} cues"

cap = cv2.VideoCapture(video)
fps = cap.get(cv2.CAP_PROP_FPS)
frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
n = len(frames)
h, w = frames[0].shape[:2]
t = np.arange(n) / fps
bounds = [0.0, *cuts, n / fps + 1]
shot = np.searchsorted(bounds, t, side="right") - 1

mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True,
                                       min_detection_confidence=0.3)
REGIONS = {"C": (0, w), "L": (0, w // 2), "R": (w // 2, w)}


def landmarks(frame, who):
    x0, x1 = REGIONS[who]
    crop = frame[: int(h * 0.6), x0:x1]
    r = mesh.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    if not r.multi_face_landmarks:
        return None
    p = np.array([(q.x * (x1 - x0) + x0, q.y * crop.shape[0]) for q in r.multi_face_landmarks[0].landmark])
    return p


# people present per shot: a shot whose cues are all C is solo
people = {}
for s in range(len(bounds) - 1):
    who = {speakers[i] for i, c in enumerate(cues) if bounds[s] <= c[0] < bounds[s + 1]}
    people[s] = ["C"] if who <= {"C"} else ["L", "R"]

# lip gap (inner lips 13-14) relative to face height (10-152), per person per frame
gap = {p: np.full(n, np.nan) for p in "CLR"}
for i in range(n):
    for who in people[shot[i]]:
        p = landmarks(frames[i], who)
        if p is not None:
            gap[who][i] = np.linalg.norm(p[13] - p[14]) / np.linalg.norm(p[10] - p[152])

fails = []
# talking = the lip gap opening and closing; a smiling listener keeps a steady gap
osc = {p: np.abs(np.diff(gap[p], prepend=np.nan)) for p in "CLR"}
print("cue  who  speaker-osc listener-osc  (lip-gap change per frame, x1000)")
for i, c in enumerate(cues):
    a, b = int(c[0] * fps), int(c[1] * fps)
    spk = speakers[i]
    lst = [p for p in people[shot[a]] if p != spk]
    so = 1000 * np.nanmean(osc[spk][a:b])
    lo = 1000 * np.nanmean(osc[lst[0]][a:b]) if lst else np.nan
    bad = []
    if so < 4:
        bad.append("speaker's lips barely move")
    if lst and lo > 0.5 * so:
        bad.append("listener's lips move too")
    print(f"{i + 1:>3}  {spk}    {so:6.1f}      {lo:6.1f}   {'; '.join(bad)}")
    if bad:
        fails.append(f"cue {i + 1} ({c[2]}): {', '.join(bad)}")

hits = {p: np.mean(~np.isnan(gap[p][::2][np.isin(shot[::2], [s for s in people if p in people[s]])]))
        for p in set(speakers)}
print("mesh hit rate:", {k: f"{v:.0%}" for k, v in hits.items()})
print("RESULT", "FAIL " + " | ".join(fails) if fails else "PASS")
sys.exit(1 if fails else 0)
