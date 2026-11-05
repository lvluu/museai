"""The memoriescore reference skin colour, as numbers, and the transfer that puts a face onto it.

Histogram matching in CIELAB of the skin pixels only: they take the reference's skin distribution per channel
(33 quantiles each); the rest of the frame keeps its own picture, the two blended by a dilated, softly
blurred skin mask so no seam shows. The table IS the reference (the THAT WAS HIM close-up,
references/reference-study.md Round 3c); nothing of the frame itself is kept. Matching the background too
(an earlier version) forced every scene onto that one frame's dark fur-coat surroundings: murky, vague.
The reference is clean and crisp (480-wide laplacian variance 25-145, like our clips after the 540 p
pass), so no blur and no halation here either. still_match.py uses it on a still, finish.py on every
frame of a clip. Needs numpy, pillow, scikit-image, scipy.
"""
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, gaussian_filter
from skimage import color

Q = np.linspace(0, 100, 33)
REF_SKIN = np.array([
    [24.87, 34.03, 35.82, 37.22, 38.40, 39.41, 40.40, 41.32, 42.19, 43.03, 43.79, 44.53, 45.22, 45.91, 46.55, 47.17, 47.75, 48.28, 48.78, 49.22, 49.68, 50.20, 50.63, 51.11, 51.58, 52.14, 52.85, 53.69, 54.64, 55.97, 58.64, 65.61, 94.33],
    [0.12, 2.32, 2.68, 3.10, 3.57, 4.24, 4.83, 5.25, 5.61, 5.94, 6.26, 6.55, 6.80, 7.07, 7.33, 7.60, 7.94, 8.39, 9.17, 11.76, 13.29, 14.05, 14.57, 14.99, 15.29, 15.60, 15.94, 16.29, 16.70, 17.10, 17.65, 18.72, 33.80],
    [2.45, 5.57, 7.16, 8.08, 8.52, 9.25, 9.98, 10.59, 11.10, 11.53, 11.93, 12.32, 12.65, 12.98, 13.35, 13.67, 13.96, 14.24, 14.52, 14.79, 15.03, 15.25, 15.48, 15.73, 16.01, 16.31, 16.60, 16.90, 17.29, 17.76, 18.29, 19.03, 26.88],
])


def skin_mask(rgb8):
    r, g, b = rgb8.astype(int).transpose(2, 0, 1)
    return (r > 95) & (g > 40) & (b > 20) & (r > g) & (g > b) & (r - b > 15) & (r - g > 10) & (r < 250)


def source_quantiles(rgb8):
    """Per-channel Lab quantiles of a frame's skin: the 'from' side of the mapping."""
    lab = color.rgb2lab(rgb8 / 255.0)
    m = skin_mask(rgb8)
    if m.sum() < 500:
        raise ValueError("no skin found in the frame")
    return np.array([np.percentile(lab[m][:, c], Q) for c in range(3)])


def _map(lab, src, ref):
    out = np.empty_like(lab)
    for c in range(3):
        xs = np.maximum.accumulate(src[c])  # monotone, so interp is well defined on flat runs
        out[..., c] = np.interp(lab[..., c], xs, ref[c])
    return out


def transfer(rgb8, src=None):
    """Put the skin of one frame onto the reference. src = source_quantiles(...) (default: this frame).
    Returns a PIL image."""
    if src is None:
        src = source_quantiles(rgb8)
    lab = color.rgb2lab(rgb8 / 255.0)
    # the whole face keeps weight 1 (dilate first): a wide soft edge pulled a small face toward the
    # untouched edge pixels (clip skin mean 106 against 113 with a plain sigma-8 blur)
    w = gaussian_filter(binary_dilation(skin_mask(rgb8), iterations=6).astype(float), 3)[..., None]
    out = color.lab2rgb(w * _map(lab, src, REF_SKIN) + (1 - w) * lab)
    return Image.fromarray((out * 255).clip(0, 255).astype(np.uint8))
