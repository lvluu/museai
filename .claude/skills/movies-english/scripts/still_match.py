#!/usr/bin/env python3
"""Pull a chosen still onto the memoriescore reference colour before it seeds the render.

usage: uv run --no-project --python 3.12 --with numpy --with pillow --with scikit-image --with scipy \
           python scripts/still_match.py <in.png> <out.png>

Reinhard colour transfer in CIELAB, region by region: the skin pixels take the reference's skin mean and
standard deviation per channel, everything else takes the reference's background statistics, the two
blended by a blurred skin mask so no seam shows. The numbers below ARE the reference (the THAT WAS HIM
close-up, references/reference-study.md Round 3b): a hand-tuned ffmpeg chain only ever approximated them
(skin 137/111/95 against 136/106/91); this lands on them (137/105/90, sat 0.35, p10 87 / p90 140). A touch of
blur and a soft halation afterwards, then still_check.py.
"""
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter
from skimage import color

# reference CIELAB mean / std per channel (L, a, b), skin mask and the rest of the frame
REF_SKIN = (np.array([47.58, 10.00, 13.40]), np.array([8.35, 5.54, 3.66]))
REF_BG = (np.array([19.10, 2.58, 3.32]), np.array([22.93, 2.97, 4.30]))


def skin_mask(rgb):
    r, g, b = (rgb * 255).transpose(2, 0, 1)
    return (r > 95) & (g > 40) & (b > 20) & (r > g) & (g > b) & (r - b > 15) & (r - g > 10) & (r < 250)


def transfer(lab, mask, ref):
    mean, std = lab[mask].mean(0), lab[mask].std(0)
    return (lab - mean) / np.maximum(std, 1e-6) * ref[1] + ref[0]


def match(src):
    rgb = np.asarray(src.convert("RGB")).astype(float) / 255
    lab = color.rgb2lab(rgb)
    m = skin_mask(rgb)
    if m.sum() < 500:
        sys.exit("still_match: no skin found in the still")
    w = gaussian_filter(m.astype(float), 8)[..., None]
    out = color.lab2rgb(w * transfer(lab, m, REF_SKIN) + (1 - w) * transfer(lab, ~m, REF_BG))
    img = Image.fromarray((out * 255).clip(0, 255).astype(np.uint8))
    glow = img.filter(ImageFilter.GaussianBlur(30))
    img = Image.blend(img, Image.fromarray(np.maximum(np.asarray(img), np.asarray(glow))), 0.12)
    return img.filter(ImageFilter.GaussianBlur(1.2))


if __name__ == "__main__":
    src, dst = sys.argv[1:3]
    match(Image.open(src)).save(dst)
    print(dst)
