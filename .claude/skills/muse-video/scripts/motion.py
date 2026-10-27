"""Usage: motion.py video.mp4  -> does nature move like real footage? (exit 1 if not)
Dense optical flow (Farneback, 270 px wide, every 2nd frame) per horizontal band of 10 %.
For each band: mag = mean flow per step, net = length of the summed flow vectors / steps,
coherence = net / mag (1 = everything drifts one way, 0 = moves back and forth in place).
  STILL PHOTO  no band has coherent motion (mag >= 0.03 and coherence >= 0.12): a frozen
               picture, maybe with a warp on top. Hallstatt take 2 (2026-10-27): sky, mist,
               village 0.00, lake mag 0.05-0.08 at coherence 0.04-0.08; the user saw the
               view "shaking like a current" instead of water flowing.
  WOBBLE       a band moves (mag >= 0.03) with coherence < 0.12: the picture warps in place
               (heat-haze/jelly look), not ripples or mist travelling. Real lake ripples in
               Hallstatt take 1 measured 0.18-0.20.
  TIME-LAPSE   a band drifts coherently (coherence >= 0.5) faster than 3 % of the frame width
               per second. Hallstatt take 1: sky 8.7 %/s, clouds filled the sky in 15 s.
Buildings and mountains should read ~0; they are part of the bands, which is fine: a band
only has to show its moving part travelling one way."""
import sys

import cv2
import numpy as np

W, H_BANDS, STEP = 270, 10, 2
MOVING, COHERENT, WOBBLE, TIMELAPSE_PCT = 0.03, 0.12, 0.12, 3.0


def bands(video):
    """[(top_pct, mag, net, coherence, speed_pct_per_s), ...]"""
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    prev, total, mags, n, i = None, None, None, 0, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        i += 1
        if i % STEP:
            continue
        h = round(frame.shape[0] * W / frame.shape[1])
        g = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (W, h))
        if prev is not None:
            fl = cv2.calcOpticalFlowFarneback(prev, g, None, 0.5, 3, 9, 3, 5, 1.1, 0)
            m = np.hypot(fl[..., 0], fl[..., 1])
            total = fl if total is None else total + fl
            mags = m if mags is None else mags + m
            n += 1
        prev = g
    if not n:
        return []
    net = np.hypot(total[..., 0], total[..., 1]) / n
    mag = mags / n
    rows, h = [], mag.shape[0]
    for b in range(H_BANDS):
        r = slice(h * b // H_BANDS, h * (b + 1) // H_BANDS)
        mm, nn = float(mag[r].mean()), float(net[r].mean())
        rows.append((b * 100 // H_BANDS, mm, nn, nn / max(mm, 1e-6), nn / STEP * fps / W * 100))
    return rows


def verdict(rows):
    problems = []
    if not any(m >= MOVING and c >= COHERENT for _, m, _, c, _ in rows):
        problems.append("STILL PHOTO: nothing travels (frozen picture, at most a warp)")
    for top, m, _, c, speed in rows:
        if m >= MOVING and c < WOBBLE:
            problems.append(f"WOBBLE {top}-{top + 10}%: moves in place (coherence {c:.2f} < {WOBBLE})")
        if c >= 0.5 and speed > TIMELAPSE_PCT:
            problems.append(f"TIME-LAPSE {top}-{top + 10}%: drifts {speed:.1f}% of width/s (> {TIMELAPSE_PCT})")
    return problems


if __name__ == "__main__":
    rows = bands(sys.argv[1])
    for top, m, nn, c, speed in rows:
        print(f"band {top:3d}-{top + 10:3d}%  mag {m:.3f}  net {nn:.3f}  coherence {c:.2f}  drift {speed:.1f}%/s")
    problems = verdict(rows)
    for p in problems:
        print(p)
    print("RESULT", "ok" if not problems else "FAIL")
    sys.exit(1 if problems else 0)
