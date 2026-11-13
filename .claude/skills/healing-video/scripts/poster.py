"""Poster-style 9:16 thumbnail for a healing video: sage-green pill label, one huge rounded-bold white
title with a deep-green outline, a small sub line, over a softly green-graded, gently darkened frame.
Same layout as the viral "pill + giant number + subtitle" covers, recoloured to the healing look
(user 2026-11-13: "same theme as healing videos, with green a bit"). cover.py has the italic styles.

Usage: python3 scripts/poster.py --at healing-<slug>.mp4@auto --label "JUST A QUIET MORNING" \
           --title "slow down" --sub "cosy cottage life" --out thumbs/healing-<slug>_9x16.jpg
Text stays in the 9:16 safe box (x80-960, y300-1560).
"""
import argparse
from pathlib import Path

from cover import frame_at
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

BOLD = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"
W, H = 1080, 1920
GREEN = (92, 124, 88)  # sage pill
DEEP = (28, 52, 34)  # outline / shadow green
CREAM = (250, 246, 234)


def fit(d, text, max_w, size):
    """Largest font <= size where every line of text fits max_w; breaks on spaces, up to 3 lines."""
    words = text.split()
    while size > 70:
        f = ImageFont.truetype(BOLD, size)
        lines, cur = [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= max_w or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        if len(lines) <= 3 and all(d.textlength(ln, font=f) <= max_w for ln in lines):
            return f, lines
        size -= 8
    return f, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", required=True, help="clip.mp4@seconds or clip.mp4@auto")
    ap.add_argument("--label", default="", help="text in the green pill (uppercased)")
    ap.add_argument("--title", required=True, help="giant title, 1-3 short words work best")
    ap.add_argument("--sub", default="", help="small line under the title")
    ap.add_argument("--y", type=float, default=0.45, help="centre of the text block, fraction of height")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    a.sub = "".join(c for c in a.sub if ord(c) < 0x2000).strip()  # Arial Rounded has no emoji glyphs

    clip, _, t = a.at.partition("@")
    img = frame_at(clip, t)
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    img = img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width - W) // 2 + W, (img.height - H) // 2 + H))
    img = ImageEnhance.Color(img).enhance(1.05)
    img = Image.blend(img, Image.new("RGB", (W, H), (70, 110, 70)), 0.12)  # a bit of green over everything

    d0 = ImageDraw.Draw(Image.new("RGBA", (W, H)))
    tf, lines = fit(d0, a.title, 880, 300)
    lf = ImageFont.truetype(BOLD, 40)
    sf = ImageFont.truetype(BOLD, 60)
    lh = tf.size * 1.02
    pill_h = 96 if a.label else 0
    gap = 46 if a.label else 0
    sub_h = 100 if a.sub else 0
    block_h = pill_h + gap + lh * len(lines) + sub_h
    top = H * a.y - block_h / 2

    base = img.convert("RGBA")
    scrim = Image.new("L", (W, H), 0)
    ImageDraw.Draw(scrim).rectangle((0, top - 120, W, top + block_h + 120), fill=95)
    scrim = scrim.filter(ImageFilter.GaussianBlur(90))
    base = Image.composite(Image.new("RGBA", (W, H), DEEP + (255,)), base, scrim)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d, sd = ImageDraw.Draw(layer), ImageDraw.Draw(shadow)
    y = top
    if a.label:
        text = a.label.upper()
        tw = sum(d.textlength(c, font=lf) for c in text) + 4 * (len(text) - 1)
        x0 = (W - tw) / 2 - 48
        box = (x0, y, x0 + tw + 96, y + pill_h)
        sd.rounded_rectangle((box[0], box[1] + 8, box[2], box[3] + 8), radius=pill_h // 2, fill=(0, 0, 0, 150))
        d.rounded_rectangle(box, radius=pill_h // 2, fill=GREEN + (255,))
        x = x0 + 48
        for c in text:
            d.text((x, y + pill_h / 2 + 2), c, font=lf, fill=CREAM + (255,), anchor="lm")
            x += d.textlength(c, font=lf) + 4
        y += pill_h + gap
    for ln in lines:
        x = W / 2
        sd.text((x, y + 12), ln, font=tf, fill=(0, 0, 0, 170), anchor="mt", stroke_width=14, stroke_fill=(0, 0, 0, 170))
        d.text((x, y), ln, font=tf, fill=(255, 255, 255, 255), anchor="mt", stroke_width=12, stroke_fill=DEEP + (255,))
        y += lh
    if a.sub:
        y += 20
        sd.text((W / 2, y + 5), a.sub, font=sf, fill=(0, 0, 0, 170), anchor="mt", stroke_width=8, stroke_fill=(0, 0, 0, 170))
        d.text((W / 2, y), a.sub, font=sf, fill=CREAM + (255,), anchor="mt", stroke_width=7, stroke_fill=DEEP + (255,))
    layer = Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)), layer)
    out = Image.alpha_composite(base, layer).convert("RGB")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out, quality=92)
    print(f"THUMB {a.out} {Path(a.out).stat().st_size // 1024} KB lines={len(lines)} font={tf.size}")


if __name__ == "__main__":
    main()
