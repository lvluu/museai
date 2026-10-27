"""Usage: gaze.py video.mp4 cues.json TARGETS [gaze.jpg]
       gaze.py clip.mp4 - O|C [gaze.jpg]   (one clip, the whole clip as one line; check_clip.sh GAZE=)
  uv run --no-project --python 3.12 --with mediapipe==0.10.14 --with opencv-python-headless==4.10.0.84 \\
      python scripts/gaze.py video.mp4 cues.json CMWMWMWMWMC gaze.jpg

Checks that people look where the scene needs them to: at each other while talking, not off
into the room, at the floor or at the lens. The user saw this as "AI generated" on EP12 (the
woman looked past the man while speaking to him), and no other check caught it.
TARGETS has one letter per cue:
  W / M   the speaker of a dialogue line: both people look at each other (O: same, for a whole clip).
  C       a line to the camera (intro, ending question): the speaker looks at the lens, the
          other person (if in frame) keeps looking at the speaker, never at the lens.
Env: LEFT=W (who stands on screen left), STEP=3 (check every 3rd frame), MIN=0.7.
  gaze    per face: head yaw (nose against the cheek line, in face widths) + iris position between
          the eye corners, both in screen x: + looks toward screen right, - toward screen left,
          about 0 at the lens. On target: past TOWARD (0.2) toward the other person, or within CAM
          (0.15) of 0 for the lens, and eyes not cast down (iris past 62 % of the eye opening).
          EP12 calibration: the man looking at the woman -0.36 yaw / -0.10 iris; both to camera
          +0.1 to +0.13; the man half-turned to the lens in the ending -0.11 (the user saw it).
  profile |yaw| > 0.9 (side profile): the iris cannot be read and the mouth check is unreliable,
          so the frame counts as off. EP12: the woman sat at yaw 1.0-1.5 for every dialogue line and
          her eyes wandered; the user called it looking "at another place".
  verdict each person must be on target in >= MIN of the line's checked frames: OFF GAZE otherwise
          (the counts say how many frames were profile, looked away, or looked down).
  sheet   gaze.jpg: per line, 4 frames of each face's eye band, to look at the flagged lines.
Exit 1 when any line has OFF GAZE."""
import json
import os
import sys

import cv2
import mediapipe as mp
import numpy as np

video, cues_path, targets = sys.argv[1], sys.argv[2], sys.argv[3].upper()
sheet = sys.argv[4] if len(sys.argv) > 4 else None
if cues_path == "-":
    cap = cv2.VideoCapture(video)
    cues = [[0, cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS), "whole clip"]]
else:
    cues = json.load(open(cues_path))
if len(targets) != len(cues):
    sys.exit(f"TARGETS has {len(targets)} letters for {len(cues)} cues")
left = os.environ.get("LEFT", "W").upper()
right = "M" if left == "W" else "W"
STEP, MIN = int(os.environ.get("STEP", 3)), float(os.environ.get("MIN", 0.7))
TOWARD, CAM, DOWN, PROFILE = float(os.environ.get("TOWARD", 0.2)), float(os.environ.get("CAM", 0.15)), 0.62, 0.9

det = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.3)
mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True,
                                       min_detection_confidence=0.2)


def direction(lm):
    """Head yaw, iris offset (both + = toward screen right) and how far down the irises sit."""
    width = lm[454].x - lm[234].x
    yaw = (lm[1].x - (lm[234].x + lm[454].x) / 2) / max(1e-6, abs(width))
    iris, down = [], []
    for c0, c1, ir, top, bot in ((33, 133, 468, 159, 145), (362, 263, 473, 386, 374)):
        a, b = sorted((lm[c0].x, lm[c1].x))
        iris.append((lm[ir].x - a) / max(1e-6, b - a) - 0.5)
        down.append((lm[ir].y - lm[top].y) / max(1e-6, lm[bot].y - lm[top].y))
    return yaw, float(np.mean(iris)), float(np.mean(down))


cap = cv2.VideoCapture(video)
fps = cap.get(cv2.CAP_PROP_FPS)
seen = {}  # (time, person) -> (gaze x, down, eye-band crop)
n = 0
while True:
    ok, img = cap.read()
    if not ok:
        break
    t, n = n / fps, n + 1
    if (n - 1) % STEP:
        continue
    H, W = img.shape[:2]
    if W > 1080:  # 4K finals: face mesh needs no more, and it is 4x faster
        img = cv2.resize(img, (1080, int(H * 1080 / W)))
        H, W = img.shape[:2]
    found = [d.location_data.relative_bounding_box for d in det.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).detections or []]
    for b in found:
        x0, y0 = int(max(0, (b.xmin - 0.25 * b.width) * W)), int(max(0, (b.ymin - 0.3 * b.height) * H))
        x1, y1 = int(min(W, (b.xmin + 1.25 * b.width) * W)), int(min(H, (b.ymin + 1.2 * b.height) * H))
        if x1 - x0 < 20 or y1 - y0 < 20:
            continue
        crop = cv2.resize(img[y0:y1, x0:x1], (384, int(384 * (y1 - y0) / (x1 - x0))))
        r = mesh.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        if not r.multi_face_landmarks:
            continue
        lm = r.multi_face_landmarks[0].landmark
        solo = len(found) == 1 and abs(b.xmin + b.width / 2 - 0.5) < 0.12  # to-camera intro
        person = "solo" if solo else (left if b.xmin + b.width / 2 < 0.5 else right)
        h = crop.shape[0]
        ey = int(np.mean([lm[159].y, lm[386].y]) * h)
        w = crop.shape[1]
        ex0, ex1 = int(max(0, min(lm[234].x, lm[33].x) * w)), int(min(w, max(lm[454].x, lm[263].x) * w))
        band = cv2.resize(crop[max(0, ey - 30) : ey + 30, ex0:max(ex1, ex0 + 20)], (384, 80))
        seen[(t, person)] = (*direction(lm), band)


def verdict(yaw, iris, down, want):
    """'ok', or why the frame is off: 'profile', 'down' or 'away'."""
    if abs(yaw) > PROFILE:
        return "profile"
    if 0 <= down <= 1.5 and down > DOWN:  # outside 0-1.5 the lids were misread
        return "down"
    g = yaw + iris
    if want == "C":
        return "ok" if abs(g) < CAM else "away"
    return "ok" if (g > TOWARD if want == "R" else g < -TOWARD) else "away"


fail, tiles = [], []
for i, (c, tg) in enumerate(zip(cues, targets, strict=True)):
    a, b = c[0], c[1]
    report, col = [], []
    for p in (left, right):
        # C: the host (screen left, or alone and centred) talks to the lens, the other keeps looking at her
        want = ("C" if p == left else "L") if tg == "C" else {left: "R", right: "L"}[p]
        frames = [(k[0], v) for k, v in seen.items() if a <= k[0] <= b and (k[1] == p or (k[1] == "solo" and p == left))]
        if not frames:
            # in a two-shot a face nobody can find is turned away (EP12 line 10: the woman, in profile)
            others = any(a <= k[0] <= b for k in seen)
            report.append(f"{p} no face" + (" OFF" if others and tg != "C" else ""))
            if others and tg != "C":
                fail.append(i + 1)
            continue
        vs = [verdict(y, ir, d, want) for _, (y, ir, d, _) in frames]
        share = vs.count("ok") / len(vs)
        gx = np.median([y + ir for _, (y, ir, _, _) in frames])
        bad = share < MIN
        why = ",".join(f"{k} {vs.count(k)}" for k in ("profile", "away", "down") if vs.count(k))
        report.append(f"{p} {share:4.0%} (x {gx:+.2f})" + (f" OFF[{why}]" if bad else ""))
        if bad:
            fail.append(i + 1)
        pick = frames[:: max(1, len(frames) // 4)][:4]
        col.append(np.vstack([v[3] for _, v in pick] + [np.zeros((80, 384, 3), np.uint8)] * (4 - len(pick))))
    flag = "  <-- OFF GAZE" if (i + 1) in fail else ""
    print(f"{i + 1:2d} {a:6.2f}-{b:6.2f} {tg}  " + "   ".join(report) + f"   {c[2]}{flag}")
    if col:
        tile = np.vstack(col)
        cv2.putText(tile, f"{i + 1} {tg}", (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        tiles.append(tile)
if sheet and tiles:
    h = max(t.shape[0] for t in tiles)
    cv2.imwrite(sheet, np.hstack([np.vstack([t, np.zeros((h - t.shape[0], 384, 3), np.uint8)]) for t in tiles]))
    print(f"sheet: {sheet}")
fail = sorted(set(fail))
print("RESULT ok" if not fail else f"RESULT FAIL lines {','.join(map(str, fail))}")
sys.exit(1 if fail else 0)
