# /// script
# dependencies = ["pillow", "fonttools"]
# ///
"""Cover image (thumbnail) for a finished travel video: the sharpest, most colourful frame of the
shots, graded a little punchier, with a short hook line, the place name in big letters and the flag.

Usage:
  uv run --no-project --python 3.12 --with pillow --with fonttools python scripts/thumbnail.py \
      --place "Geirangerfjord" [--flag 🇳🇴] [--country Norway] [--hook "7 WATERFALLS. 1 FJORD."] \
      --out reel-geiranger.thumb.jpg s1.mp4 s2.mp4 ...   [--at s1.mp4@2.5]

Pass the raw shots, not the reel: the reel has intro text, dips to black and transitions on its
frames. The first clip is the hook shot (the most striking view) and gets a small bonus. The output
keeps the source frame size and aspect (9:16 reels → 1080x1920 cover, 16:9 → 1920x1080).
Text sits in the upper band, clear of TikTok/Reels UI at the bottom and right and of the centred
subject the drone shots frame.
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scenic-drop-reel" / "scripts"))
from compose import canvas, duration, fit, line  # noqa: E402

STEP = 0.25  # s between candidate frames
EDGE = 0.5  # s skipped at both ends of a clip (muse settles in / fades out there)
HOOK_BONUS = 1.15
YELLOW = (255, 214, 10)


def grab(clip, t, dest):
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-ss",
            f"{t:.3f}",
            "-i",
            str(clip),
            "-frames:v",
            "1",
            str(dest),
        ],
        check=True,
    )
    return Image.open(dest).convert("RGB")


def score(img):
    """Sharp (edge variance) x colourful (Hasler-Süsstrunk) x well exposed (mid luma)."""
    sharp = ImageStat.Stat(img.convert("L").filter(ImageFilter.FIND_EDGES)).var[0] ** 0.5
    r, g, b = (c.tobytes() for c in img.split())
    rg = [x - y for x, y in zip(r, g, strict=True)]
    yb = [(x + y) / 2 - z for x, y, z in zip(r, g, b, strict=True)]

    def ms(v):
        m = sum(v) / len(v)
        return m, (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5

    (mrg, srg), (myb, syb) = ms(rg), ms(yb)
    colour = (srg**2 + syb**2) ** 0.5 + 0.3 * (mrg**2 + myb**2) ** 0.5
    luma = ImageStat.Stat(img.convert("L")).mean[0]
    exposure = max(0.2, 1 - abs(luma - 120) / 120)
    return sharp * colour * exposure


def best_frame(clips, tmp):
    best = None
    for i, clip in enumerate(clips):
        d = duration(str(clip))
        # one ffmpeg per clip: small frames every STEP s from EDGE (an ffmpeg per frame took 2.5 min for 9 shots)
        for old in tmp.glob("c_*.png"):
            old.unlink()
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-ss",
                str(EDGE),
                "-t",
                str(max(d - 2 * EDGE, 0)),
                "-i",
                str(clip),
                "-vf",
                f"fps={1 / STEP},scale=270:-2",
                str(tmp / "c_%04d.png"),
            ],
            check=True,
        )
        for k, png in enumerate(sorted(tmp.glob("c_*.png"))):
            s = score(Image.open(png).convert("RGB")) * (HOOK_BONUS if i == 0 else 1)
            if best is None or s > best[0]:
                best = (s, clip, EDGE + k * STEP)
    if best is None:
        sys.exit("no frames: clips shorter than 1 s?")
    return best


def gradient(w, h, top, bottom):
    """Dark band behind the text at the top, lighter one at the bottom so the cover reads on any feed."""
    g = Image.new("L", (1, h))
    for y in range(h):
        a = 0
        if y < h * top[0]:
            a = top[1] * (1 - y / (h * top[0])) ** 1.4
        elif y > h * (1 - bottom[0]):
            a = bottom[1] * ((y - h * (1 - bottom[0])) / (h * bottom[0])) ** 1.6
        g.putpixel((0, y), round(a))
    black = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    black.putalpha(g.resize((w, h)))
    return black


def title_lines(d, text, base, w):
    """One line when it fits big; else two balanced lines (long names like 'Plitvice Lakes National Park')."""
    t = text.upper()
    f, sp = fit(d, t, "futura", round(base * 0.22), w * 0.9, spacing_ratio=0.08)
    words = t.split()
    if f.size >= base * 0.14 or len(words) < 2:
        return [(t, f, sp)]
    cut = min(
        range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(" ".join(words[k:])))
    )
    rows = [" ".join(words[:cut]), " ".join(words[cut:])]
    f, sp = min(
        (fit(d, r, "futura", round(base * 0.2), w * 0.9, spacing_ratio=0.08) for r in rows),
        key=lambda x: x[0].size,
    )
    return [(r, f, sp) for r in rows]


def render(frame, place, flag, country, hook):
    w, h = frame.size
    base = min(
        w, h * 9 / 16
    )  # type scale follows the short side, so 16:9 covers don't get giant text
    img = ImageEnhance.Contrast(ImageEnhance.Color(frame).enhance(1.15)).enhance(1.06)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2)).convert("RGBA")
    img.alpha_composite(gradient(w, h, (0.42, 190), (0.18, 120)))
    ov, d = canvas(w, h)
    y = h * 0.11
    if hook:
        f, _ = fit(d, hook.upper(), "heavy", round(base * 0.075), w * 0.86)
        line(d, ov, (w / 2, y), hook.upper(), f, fill=YELLOW, stroke=max(2, f.size // 18))
        y += f.size * 1.35
    for text, f, sp in title_lines(d, place, base, w):
        y += f.size * 0.85
        line(d, ov, (w / 2, y), text, f, spacing=sp, stroke=max(2, f.size // 22))
        y += f.size * 0.25
    sub = " ".join(x for x in (country, flag) if x)
    if sub:
        f, _ = fit(d, sub, "demi", round(base * 0.06), w * 0.7)
        line(d, ov, (w / 2, y + f.size * 1.2), sub, f)
    img.alpha_composite(ov)
    return img.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+", type=Path)
    ap.add_argument("--place", required=True)
    ap.add_argument("--flag", default="")
    ap.add_argument("--country", default="")
    ap.add_argument(
        "--hook", default="", help="2-5 words, the same promise as the caption's first line"
    )
    ap.add_argument("--at", help="force the frame: clip.mp4@seconds")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if a.at:
            clip, _, t = a.at.rpartition("@")
            clip, t = Path(clip), float(t)
        else:
            _, clip, t = best_frame(a.clips, tmp)
        frame = grab(clip, t, tmp / "full.png")
    render(frame, a.place, a.flag, a.country, a.hook).save(a.out, quality=92)
    print(f"THUMB {a.out} from {clip.name}@{t:.2f} ({frame.width}x{frame.height})")


if __name__ == "__main__":
    main()
