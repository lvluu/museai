"""Soft 9:16 cover for a healing video: one calm frame of a raw shot, the video's line in a large
white italic serif with a soft shadow, a small line under it. No banners, rings or shock hooks (the
thumbnail skill's travel style is the opposite of this format). Text stays in the 9:16 safe box
(x80-960, y300-1560) so platform crops and UI never cover it.

Usage: python3 scripts/cover.py --at s7.mp4@2.0 --title "living gently" --sub "a rainy summer in Wales" \
           --out thumbs/healing-<slug>_9x16.jpg
deliver.sh takes THUMB_DIR=thumbs (it looks for *_9x16.jpg).
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ITALIC = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
REGULAR = "/System/Library/Fonts/Supplemental/Georgia.ttf"
W, H = 1080, 1920


def fit(draw, text, path, size, max_w):
    while True:
        f = ImageFont.truetype(path, size)
        if draw.textlength(text, font=f) <= max_w or size < 30:
            return f
        size -= 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", required=True, help="clip.mp4@seconds")
    ap.add_argument("--title", required=True)
    ap.add_argument("--sub", default="")
    ap.add_argument("--y", type=float, default=0.40, help="title centre, fraction of the height")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    clip, _, t = a.at.partition("@")
    frame = Path(tempfile.mkdtemp()) / "f.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", t or "1", "-i", clip, "-frames:v", "1", str(frame)], check=True)
    img = Image.open(frame).convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    img = img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width - W) // 2 + W, (img.height - H) // 2 + H))
    img = ImageEnhance.Brightness(ImageEnhance.Color(img).enhance(1.05)).enhance(1.04)  # bright, never dark

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tf = fit(d, a.title, ITALIC, 120, 860)
    sf = ImageFont.truetype(REGULAR, 42)
    ty = H * a.y
    lines = [(a.title, tf, ty)] + ([(a.sub, sf, ty + tf.size * 0.95)] if a.sub else [])
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for text, f, y in lines:
        x = (W - d.textlength(text, font=f)) / 2
        sd.text((x, y + 3), text, font=f, fill=(0, 0, 0, 170), anchor="ls")
    layer = Image.alpha_composite(layer, shadow.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(layer)
    for text, f, y in lines:
        x = (W - d.textlength(text, font=f)) / 2
        d.text((x, y), text, font=f, fill=(255, 255, 255, 245), anchor="ls")
    out = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out, quality=92)
    print(f"THUMB {a.out} {Path(a.out).stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
