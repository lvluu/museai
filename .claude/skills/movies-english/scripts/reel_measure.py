"""Measure a finished episode against the THAT WAS HIM reel, frame by frame (reference-study.md Round 3j).

  python scripts/reel_measure.py OUT.mp4 [step]      # needs numpy, scikit-image, scipy

The same read as the in-page measure of the reel: every `step` s (default 1) a frame at 270x480, CIELAB.
Singles (skin covers over 6 % of the frame) are compared with the reel's singles, the rest are printed only.
"""
import subprocess
import sys

import numpy as np
from scipy.ndimage import label
from skimage import color

W, H = 270, 480
# The reel's singles, 12 frames (2026-11): median and the band we accept
REEL = {
    "Lp95": (66, 60, 70),       # brightest 5 %: creamy, never white
    "Lp50": (40, 36, 46),
    "hiFrac": (0.006, 0, 0.015),  # near-white (luma > 200) share of the frame
    "skinL": (47, 43, 50),
    "skinA": (21, 18, 24),
    "skinB": (17, 14, 21),
    "bgRB": (1.35, 1.2, 1.5),   # red / blue of the top band: honey, not grey
    "shGB": (0.9, 0.8, 1.0),    # blue / green of the shadows: brown, not red
}


def frame(video, t):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(t), "-i", video, "-frames:v", "1",
                          "-vf", f"scale={W}:{H}:flags=bilinear", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, stdin=subprocess.DEVNULL).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(float) if len(raw) == W * H * 3 else None


def measure(rgb):
    lab = color.rgb2lab(rgb / 255)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    lum = rgb @ [0.299, 0.587, 0.114]
    sk = (a > 12) & (a < 40) & (L > 35) & (L < 85) & (b > 8) & (b < 26)
    sh = lum < 40
    top = np.zeros_like(sk)
    top[: int(H * 0.3)] = True
    bg = top & ~sk
    lb, _ = label(sk)
    sizes = np.bincount(lb.ravel())
    sizes[0] = 0
    m = {"Lp95": np.percentile(L, 95), "Lp50": np.percentile(L, 50), "hiFrac": (lum > 200).mean(),
         "skinFrac": sk.mean(), "blob": 100 * sizes.max() / sk.size}
    if sk.any():
        m |= {"skinL": np.median(L[sk]), "skinA": np.median(a[sk]), "skinB": np.median(b[sk])}
    if bg.any():
        m["bgRB"] = rgb[..., 0][bg].mean() / max(rgb[..., 2][bg].mean(), 1)
    if sh.any():
        m["shGB"] = rgb[..., 2][sh].mean() / max(rgb[..., 1][sh].mean(), 1)
    return m


def main():
    video, step = sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    singles, t = [], 0.5
    while (rgb := frame(video, t)) is not None:
        m = measure(rgb)
        kind = "single" if m["skinFrac"] > 0.06 else "other"
        print(f"{t:5.1f} {kind:6s} " + " ".join(f"{k}={v:.3g}" for k, v in m.items()))
        if kind == "single":
            singles.append(m)
        t += step
    if not singles:
        sys.exit("no singles found")
    bad = 0
    print(f"\n{len(singles)} singles vs the reel (median, band):")
    for k, (ref, lo, hi) in REEL.items():
        v = float(np.median([s[k] for s in singles if k in s]))
        ok = lo <= v <= hi
        bad += not ok
        print(f"  {k:7s} {v:7.3g}  reel {ref} ({lo}-{hi})  {'ok' if ok else 'OFF'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
