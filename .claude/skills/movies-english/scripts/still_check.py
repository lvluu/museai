#!/usr/bin/env python3
"""Measure a still's face against the memoriescore reel (reference-study.md "Round 3e").

usage: uv run -q --no-project --python 3.12 --with numpy --with pillow --with scikit-image --with scipy \
    python scripts/still_check.py <png>...
Prints one line per still: the metrics, then PASS or the bands it misses. Exit 1 if any still fails.
The face is the largest pink blob of the frame (refgrade.face_mask), read at 1080x1920 in CIELAB, exactly
as the reel was measured in the browser; a whole-frame RGB skin rule (the earlier version) also took beige
walls and blonde hair and banded on that mix.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from skimage import color
from skimage.measure import label

sys.path.insert(0, str(Path(__file__).resolve().parent))
from refgrade import face_mask  # noqa: E402

# twelve face readings of the THAT WAS HIM reel: her close-ups rgb 148/95/82, L50 46-47, a50 20-21, b50 16-17;
# his 142-147/84-91/71-78, L50 43-46, a50 22, b50 17-19; small faces b50 up to 24. L p5 25-33, p95 51-71.
BANDS = {
    "L50": (41, 50),       # face brightness: a mid tone, never a bright glow
    "a50": (17, 25),       # pink-red: the face reads as skin, not grey (ours was 14-16 before)
    "b50": (14, 22),       # warm: never cold-grey, never orange-yellow
    "Lspread": (18, 45),   # p95 - p5: modelled, not flat, no hot highlight
    "faceR": (135, 160),   # mean red of the face
    "hiFrac": (0, 0.07),   # lights bloom, never clip (snow and a white blazer may)
}
# The reel's singles: the strict skin blob covers 7-12 % of the frame (face ~45-54 % of the width, hair top ~13 %).
# Our medium shots measured 3-5 % and read as "the face is not clear" (Round 3h). Only close-*/medium-* stills.
# A warning, not a fail: highlights and lighter skin break the strict blob apart, so a tight close-up can read
# 2-4 % (Round 3i); look at the frame before re-rendering.
FACE_AREA_MIN = 6.0


def face_area(lab):
    """Largest strict skin blob at 270 wide, % of the frame: the same measure as the browser read of the reel."""
    small = lab[::4, ::4]
    L, a, b = small[..., 0], small[..., 1], small[..., 2]
    strict = (a > 12) & (a < 40) & (L > 35) & (L < 85) & (b > 8) & (b < 26)
    lab_ = label(strict, connectivity=1)
    if lab_.max() == 0:
        return 0.0
    sizes = np.bincount(lab_.ravel())
    sizes[0] = 0
    return round(100.0 * sizes.max() / strict.size, 1)


def measure(path):
    im = Image.open(path).convert("RGB").resize((1080, 1920), Image.BICUBIC)
    rgb = np.asarray(im).astype(float)
    lab = color.rgb2lab(rgb / 255.0)
    m = face_mask(lab, rgb.shape[:2])
    if m is None or m.sum() < 2000:
        return None
    L, a, b = (lab[..., c][m] for c in range(3))
    lum = rgb @ [0.299, 0.587, 0.114]

    def p(v, q):
        return float(np.percentile(v, q))

    return {
        "faceRGB": [round(float(rgb[..., c][m].mean())) for c in range(3)],
        "faceR": round(float(rgb[..., 0][m].mean())),
        "L50": round(p(L, 50), 1),
        "a50": round(p(a, 50), 1),
        "b50": round(p(b, 50), 1),
        "Lspread": round(p(L, 95) - p(L, 5), 1),
        "hiFrac": round(float((lum > 235).mean()), 3),
        "facePx": int(m.sum()),
        "faceArea": face_area(lab),
    }


def main():
    bad = 0
    for path in sys.argv[1:]:
        m = measure(path)
        name = path.split("/")[-1]
        if m is None:
            print(f"{name}: no face found")
            bad += 1
            continue
        miss = [f"{k}={m[k]} not in {lo}-{hi}" for k, (lo, hi) in BANDS.items() if not lo <= m[k] <= hi]
        warn = (f"\n  WARN faceArea={m['faceArea']}% < {FACE_AREA_MIN}%: check the face is about half the width"
                if name.startswith(("close-", "medium-")) and m["faceArea"] < FACE_AREA_MIN else "")
        vals = " ".join(f"{k}={v}" for k, v in m.items())
        print(f"{name}: {vals}\n  {'PASS' if not miss else 'FAIL ' + '; '.join(miss)}{warn}")
        bad += bool(miss)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
