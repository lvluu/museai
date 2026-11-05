#!/usr/bin/env python3
"""Measure a still against the memoriescore close-up bands (reference-study.md "Round 3").

usage: uv run -q --no-project --python 3.12 --with numpy --with pillow python scripts/still_check.py <png>...
Prints one line per still: the metrics, then PASS or the bands it misses. Exit 1 if any still fails.
"""
import sys

import numpy as np
from PIL import Image

# measured on memoriescore close-ups (reference-study.md): soft frontal light, matte-glow skin, dark glowing room
BANDS = {
    "skinMean": (100, 130),  # face brightness
    "skinP10": (75, 999),    # no dark shadow side
    "skinP90": (0, 150),     # no hot highlight
    "skinRange": (0, 70),    # low contrast skin (p90-p10)
    "skinSat": (0.28, 0.42), # muted warmth, never orange
    "bgP50": (8, 45),        # dark room behind the face
    "hiFrac": (0, 0.01),     # lights bloom, never clip
    "skinGB": (0.95, 1.25),  # green/blue of the skin: peach-pink, not orange (reference 1.09; ours was 1.5)
}


def measure(path):
    im = np.asarray(Image.open(path).convert("RGB").resize((135, 240))).astype(float)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    skin = (r > 95) & (g > 40) & (b > 20) & (r > g) & (g > b) & (r - b > 15) & (r - g > 10) & (r < 250)
    sl, bl = lum[skin], lum[~skin]
    if sl.size < 200:
        return None
    mx, mn = im.max(2), im.min(2)
    sat = ((mx - mn) / np.maximum(mx, 1))[skin]
    p = lambda a, q: float(np.percentile(a, q))
    rgb = [float(r[skin].mean()), float(g[skin].mean()), float(b[skin].mean())]
    return {
        "skinRGB": [round(v) for v in rgb],
        "skinGB": round(rgb[1] / max(rgb[2], 1), 2),
        "skinMean": round(float(sl.mean())),
        "skinP10": round(p(sl, 10)),
        "skinP90": round(p(sl, 90)),
        "skinRange": round(p(sl, 90) - p(sl, 10)),
        "skinSat": round(float(sat.mean()), 2),
        "bgP50": round(p(bl, 50)),
        "hiFrac": round(float((lum > 235).mean()), 3),
        "skinFrac": round(float(skin.mean()), 2),
    }


def main():
    bad = 0
    for path in sys.argv[1:]:
        m = measure(path)
        name = path.split("/")[-1]
        if m is None:
            print(f"{name}: no face found (skin < 200 px)")
            bad += 1
            continue
        miss = [f"{k}={m[k]} not in {lo}-{hi}" for k, (lo, hi) in BANDS.items() if not lo <= m[k] <= hi]
        vals = " ".join(f"{k}={v}" for k, v in m.items())
        print(f"{name}: {vals}\n  {'PASS' if not miss else 'FAIL ' + '; '.join(miss)}")
        bad += bool(miss)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
