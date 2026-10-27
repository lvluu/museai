"""Usage: lock_camera.py in.mp4 out.mp4 FROM_S [ROCK_TOP=0.62]
Cancels a camera move that starts at FROM_S seconds (muse tilting or drifting late in a
locked travel take): every later frame is aligned (ORB + similarity, RANSAC) to the frame
at FROM_S using the rigid band 12 %..ROCK_TOP of the height (rocks, cliffs, buildings),
the transforms are smoothed over +-8 frames, and the whole video gets one fixed crop to
the area every frame covers, scaled back to full size. Frames before FROM_S are untouched
apart from that crop; nothing is retimed and the audio is copied.
Goloritze take 4 (2026-10-27): tilt from 9.6 s at ~48 px/s -> < 1.3 px/s, crop 7 %.
Run with: uv run --no-project --python 3.12 --with opencv-python-headless==4.10.0.84 python lock_camera.py ...
"""
import subprocess
import sys

import cv2
import numpy as np

src, dst, from_s = sys.argv[1], sys.argv[2], float(sys.argv[3])
top = float(sys.argv[4]) if len(sys.argv) > 4 else 0.62

cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
frames = []
while True:
    ok, f = cap.read()
    if not ok:
        break
    frames.append(f)
H, W = frames[0].shape[:2]
mask = np.zeros((H, W), np.uint8)
mask[int(0.12 * H):int(top * H)] = 255
orb = cv2.ORB_create(4000)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)


def features(f):
    return orb.detectAndCompute(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), mask)


R = min(int(round(from_s * fps)), len(frames) - 1)
ref = features(frames[R])
Ms = []
for i, f in enumerate(frames):
    if i <= R:
        Ms.append(np.eye(3))
        continue
    k = features(f)
    m = bf.match(ref[1], k[1])
    p0 = np.float32([ref[0][x.queryIdx].pt for x in m])
    p1 = np.float32([k[0][x.trainIdx].pt for x in m])
    A, _ = cv2.estimateAffinePartial2D(p1, p0, method=cv2.RANSAC, ransacReprojThreshold=1.5)
    Ms.append(np.vstack([A, [0, 0, 1]]))

arr = np.array(Ms)
for i in range(R + 1, len(arr)):
    Ms[i] = arr[max(R, i - 8):i + 9].mean(0)

# crop: largest 9:16 (or W:H) rect inside every warped frame
x0 = y0 = 0.0
x1, y1 = float(W), float(H)
for M in Ms:
    c = np.array([[0, 0, 1], [W, 0, 1], [0, H, 1], [W, H, 1]], float) @ M.T
    x0, x1 = max(x0, c[0, 0], c[2, 0]), min(x1, c[1, 0], c[3, 0])
    y0, y1 = max(y0, c[0, 1], c[1, 1]), min(y1, c[2, 1], c[3, 1])
x0, y0, x1, y1 = x0 + 2, y0 + 2, x1 - 2, y1 - 2
h = min(y1 - y0, (x1 - x0) * H / W)
w = h * W / H
cx = min(max((x0 + x1) / 2, x0 + w / 2), x1 - w / 2)
cy = min(max((y0 + y1) / 2, y0 + h / 2), y1 - h / 2)
z = H / h
print(f"lock from {R / fps:.2f}s, crop zoom {z:.4f}")
S = np.array([[z, 0, -z * (cx - w / 2)], [0, z, -z * (cy - h / 2)], [0, 0, 1]])

p = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
     "-r", str(fps), "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?",
     "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "copy", dst],
    stdin=subprocess.PIPE)
for f, M in zip(frames, Ms, strict=True):
    p.stdin.write(cv2.warpPerspective(f, S @ M, (W, H), flags=cv2.INTER_LANCZOS4,
                                      borderMode=cv2.BORDER_REFLECT).tobytes())
p.stdin.close()
p.wait()
