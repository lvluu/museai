"""The memoriescore reference skin colour, as numbers, and the transfer that puts a face onto it.

Histogram matching in CIELAB of the skin pixels only: they take the reference's FACE distribution per channel
(33 quantiles each); the rest of the frame keeps its own picture, the two blended by a dilated, softly
blurred skin mask so no seam shows. The table IS the reference: the mean of twelve face-only readings of
the THAT WAS HIM reel at 1080x1920 (seven close-ups of her, five of him), each the largest connected
pink blob (Lab a > 12) of the frame, dilated, read with a loose skin rule (references/reference-study.md
Round 3e). Round 3c's table came from a whole-frame RGB skin rule that also took the beige wall and the
blonde hair: its a median was 14 where the face is 21 and b 15.5 where the face is 17.5, so every matched
face came out grey and muddy ("vague"). The source side is read the same way (largest blob of the frame
being graded), so wall and hair never enter the mapping on either side.
The reference is clean and crisp (480-wide laplacian variance 25-145, like our clips after the 540 p
pass), so no blur and no halation here either. still_match.py uses it on a still, finish.py on every
frame of a clip. Needs numpy, pillow, scikit-image, scipy.
"""
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, gaussian_filter, zoom
from skimage import color
from skimage.measure import label

Q = np.linspace(0, 100, 33)
REF_SKIN = np.array([
    [20.00, 29.03, 32.34, 34.65, 36.38, 37.72, 38.85, 39.81, 40.62, 41.36, 42.05, 42.73, 43.38, 43.98, 44.60, 45.19, 45.77, 46.33, 46.86, 47.40, 47.92, 48.43, 48.94, 49.46, 50.00, 50.56, 51.06, 51.65, 52.27, 52.95, 53.74, 55.08, 86.59],
    [5.15, 12.99, 14.59, 15.83, 16.86, 17.62, 18.18, 18.66, 19.05, 19.39, 19.68, 19.94, 20.18, 20.40, 20.59, 20.78, 20.99, 21.18, 21.39, 21.60, 21.81, 22.03, 22.25, 22.47, 22.72, 23.07, 23.47, 24.01, 24.77, 25.83, 27.38, 31.54, 39.97],
    [5.17, 13.23, 13.83, 14.20, 14.57, 14.84, 15.08, 15.30, 15.49, 15.68, 15.87, 16.08, 16.30, 16.50, 16.68, 16.84, 17.00, 17.15, 17.32, 17.50, 17.70, 17.91, 18.12, 18.31, 18.50, 18.70, 18.92, 19.20, 19.56, 19.95, 20.50, 21.54, 29.39],
])


def skin_mask(rgb8):
    r, g, b = rgb8.astype(int).transpose(2, 0, 1)
    return (r > 95) & (g > 40) & (b > 20) & (r > g) & (g > b) & (r - b > 15) & (r - g > 10) & (r < 250)


def face_mask(lab, shape):
    """The largest connected pink blob of the frame (the face), dilated, read with a loose skin rule.
    Found at 270 px wide, as the reference was measured. None when there is no blob of 300 px there."""
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    h, w = shape
    sw, sh = 270, max(1, round(h * 270 / w))
    small = zoom(lab, (sh / h, sw / w, 1), order=1)
    sL, sa, sb = small[..., 0], small[..., 1], small[..., 2]
    strict = (sa > 12) & (sa < 40) & (sL > 35) & (sL < 85) & (sb > 8) & (sb < 26)
    labels, n = label(strict, connectivity=1, return_num=True)
    if n == 0:
        return None
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    if sizes.max() < 300:
        return None
    blob = binary_dilation(labels == sizes.argmax(), iterations=3)
    blob = np.asarray(Image.fromarray(blob.astype(np.uint8) * 255).resize((w, h), Image.NEAREST)) > 0
    return blob & (a > 5) & (a < 45) & (L > 20) & (L < 98) & (b > 4) & (b < 32)


def source_quantiles(rgb8):
    """Per-channel Lab quantiles of a frame's face: the 'from' side of the mapping."""
    lab = color.rgb2lab(rgb8 / 255.0)
    m = face_mask(lab, rgb8.shape[:2])
    if m is None:
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
