"""The memoriescore reference colour, as numbers, and the transfer that puts a frame onto them.

Histogram matching in CIELAB, region by region: the skin pixels take the reference's skin distribution
per channel (33 quantiles each), everything else takes its background distribution, the two blended by a
blurred skin mask so no seam shows. The tables ARE the reference (the THAT WAS HIM close-up,
references/reference-study.md Round 3c); nothing of the frame itself is kept. still_match.py uses it on a
still, finish.py on every frame of a clip (source quantiles per frame, smoothed over time, so each frame lands on
the reference and the mapping never jumps). Needs numpy, pillow, scikit-image, scipy.
"""
import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import binary_dilation, gaussian_filter
from skimage import color

Q = np.linspace(0, 100, 33)
REF_SKIN = np.array([
    [24.87, 34.03, 35.82, 37.22, 38.40, 39.41, 40.40, 41.32, 42.19, 43.03, 43.79, 44.53, 45.22, 45.91, 46.55, 47.17, 47.75, 48.28, 48.78, 49.22, 49.68, 50.20, 50.63, 51.11, 51.58, 52.14, 52.85, 53.69, 54.64, 55.97, 58.64, 65.61, 94.33],
    [0.12, 2.32, 2.68, 3.10, 3.57, 4.24, 4.83, 5.25, 5.61, 5.94, 6.26, 6.55, 6.80, 7.07, 7.33, 7.60, 7.94, 8.39, 9.17, 11.76, 13.29, 14.05, 14.57, 14.99, 15.29, 15.60, 15.94, 16.29, 16.70, 17.10, 17.65, 18.72, 33.80],
    [2.45, 5.57, 7.16, 8.08, 8.52, 9.25, 9.98, 10.59, 11.10, 11.53, 11.93, 12.32, 12.65, 12.98, 13.35, 13.67, 13.96, 14.24, 14.52, 14.79, 15.03, 15.25, 15.48, 15.73, 16.01, 16.31, 16.60, 16.90, 17.29, 17.76, 18.29, 19.03, 26.88],
])
REF_BG = np.array([
    [0.00, 0.63, 0.86, 1.10, 1.27, 1.47, 1.65, 1.90, 2.15, 2.42, 2.68, 2.94, 3.24, 3.61, 4.11, 4.68, 5.57, 7.09, 9.72, 13.96, 19.17, 23.42, 26.20, 28.23, 30.18, 32.26, 36.01, 47.79, 53.38, 56.59, 69.06, 74.11, 100.00],
    [-4.62, -0.92, -0.42, -0.14, -0.00, 0.15, 0.40, 0.54, 0.66, 0.88, 0.94, 1.10, 1.20, 1.35, 1.51, 1.69, 1.85, 2.06, 2.28, 2.48, 2.67, 2.86, 3.04, 3.26, 3.56, 3.83, 4.17, 4.80, 5.79, 6.76, 7.91, 9.52, 31.56],
    [-4.62, -1.02, -0.48, -0.19, -0.10, -0.00, 0.00, 0.10, 0.19, 0.38, 0.64, 0.75, 0.91, 1.13, 1.38, 1.64, 1.81, 2.08, 2.38, 2.71, 3.09, 3.44, 3.80, 4.22, 4.69, 5.18, 5.91, 6.92, 8.50, 11.33, 12.83, 14.29, 24.11],
])


def skin_mask(rgb8):
    r, g, b = rgb8.astype(int).transpose(2, 0, 1)
    return (r > 95) & (g > 40) & (b > 20) & (r > g) & (g > b) & (r - b > 15) & (r - g > 10) & (r < 250)


def source_quantiles(rgb8):
    """Per-region, per-channel Lab quantiles of a frame: the 'from' side of the mapping."""
    lab = color.rgb2lab(rgb8 / 255.0)
    m = skin_mask(rgb8)
    if m.sum() < 500:
        raise ValueError("no skin found in the frame")
    return (np.array([np.percentile(lab[m][:, c], Q) for c in range(3)]),
            np.array([np.percentile(lab[~m][:, c], Q) for c in range(3)]))


def _map(lab, src, ref):
    out = np.empty_like(lab)
    for c in range(3):
        xs = np.maximum.accumulate(src[c])  # monotone, so interp is well defined on flat runs
        out[..., c] = np.interp(lab[..., c], xs, ref[c])
    return out


def transfer(rgb8, src=None, glow=0.12, blur=1.2):
    """Put one frame onto the reference. src = source_quantiles(frame) of the clip's first frame
    (default: this frame). Returns a PIL image with the soft halation and blur of the reference."""
    if src is None:
        src = source_quantiles(rgb8)
    lab = color.rgb2lab(rgb8 / 255.0)
    # the whole face keeps weight 1 (dilate first): a wide soft edge pulled a small face toward the darker
    # background mapping (clip skin mean 106 against 113 with a plain sigma-8 blur)
    w = gaussian_filter(binary_dilation(skin_mask(rgb8), iterations=6).astype(float), 3)[..., None]
    out = color.lab2rgb(w * _map(lab, src[0], REF_SKIN) + (1 - w) * _map(lab, src[1], REF_BG))
    img = Image.fromarray((out * 255).clip(0, 255).astype(np.uint8))
    if glow:
        g = img.filter(ImageFilter.GaussianBlur(30))
        img = Image.blend(img, Image.fromarray(np.maximum(np.asarray(img), np.asarray(g))), glow)
    return img.filter(ImageFilter.GaussianBlur(blur)) if blur else img
