"""curious: cartoon explainer illustration (The Curious Mechanism / Curious Mechanim channel).

The frame full bleed and ungraded (the cartoon colours stay as drawn), a 2-4 word chunky white title with a
thick ink-blue outline on the calm band at the top, an optional muted-red sub line and a small brass "CM"
mark. No badge, no emoji, no hanzi.
"""
import os
import sys

from core import CENTRE, SAFE, cover, ffprobe_duration, grab, to_pil
from PIL import ImageDraw, ImageFont

INK, WHITE, RED, BRASS = (31, 58, 95), (255, 255, 255), (166, 61, 50), (176, 141, 87)
SERIF = ["/System/Library/Fonts/Supplemental/Baskerville.ttc",  # macOS: Baskerville Bold face
         "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]
TITLE = ["/System/Library/Fonts/Supplemental/Arial Black.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
SANS = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def load(paths, size):
    """First installed font of ``paths``; in a collection, its Bold face."""
    for path in paths:
        if not os.path.exists(path):
            continue
        for i in range(8 if path.endswith(".ttc") else 1):
            try:
                f = ImageFont.truetype(path, size, index=i)
            except OSError:
                break
            if not path.endswith(".ttc") or f.getname()[1] == "Bold":
                return f
    sys.exit(f"curious: none of these fonts is installed: {', '.join(paths)}")


def wrap(text, paths, width, size, min_size, max_lines=3):
    """Largest font size at which ``text`` breaks into at most ``max_lines`` lines of ``width`` px."""
    words = text.split()
    while True:
        f = load(paths, size)
        lines = [""]
        for w in words:
            trial = f"{lines[-1]} {w}".strip()
            if f.getlength(trial) <= width or not lines[-1]:
                lines[-1] = trial
            else:
                lines.append(w)
        if (len(lines) <= max_lines and all(f.getlength(ln) <= width for ln in lines)) or size <= min_size:
            return f, lines
        size -= 6


def text_block(im, x0, y, width, args, size):
    """Title (and sub) centred on x0..x0+width from y; returns the y under it."""
    d = ImageDraw.Draw(im)
    f, lines = wrap(args.title, TITLE, width, size, size // 2)
    for ln in lines:
        d.text((x0 + width / 2, y), ln, font=f, fill=WHITE, anchor="ma",
               stroke_width=max(6, f.size // 12), stroke_fill=INK)
        y += int(f.size * 1.12)
    if args.sub:
        s, sub = wrap(args.sub.upper(), SANS, width, size // 3, 24, max_lines=2)
        y += s.size // 2
        for ln in sub:
            d.text((x0 + width / 2, y), ln, font=s, fill=RED, anchor="ma", stroke_width=4, stroke_fill=WHITE)
            y += int(s.size * 1.25)
    return y


def mark(im, cx, cy, r):
    """Small brass "CM" seal."""
    d = ImageDraw.Draw(im)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE, outline=BRASS, width=max(3, r // 10))
    d.text((cx, cy), "CM", font=load(SERIF, int(r * 0.9)), fill=BRASS, anchor="mm")


def add_args(p):
    p.add_argument("--title", required=True, help="2-4 words: the question or the object")
    p.add_argument("--sub", default="", help="small muted-red line under the title (optional)")
    p.add_argument("--at", type=float, help="frame time in seconds (default: a third into the video)")


def make(args):
    if len(args.videos) > 1:
        sys.exit("curious takes one video")
    video = args.videos[0]
    t = args.at if args.at is not None else ffprobe_duration(video) / 3
    frame = to_pil(grab(video, t))

    v = cover(frame, 1080, 1920).convert("RGB")
    text_block(v, CENTRE[0], SAFE[1], CENTRE[1] - CENTRE[0], args, 150)
    mark(v, SAFE[2] - 50, SAFE[3] - 50, 46)

    h = cover(frame, 1920, 1080).convert("RGB")
    text_block(h, 80, 90, 1000, args, 130)
    mark(h, 1920 - 110, 110, 54)  # top right: YouTube puts the duration bottom right
    return v, h, None, f"frame {t:.2f}s"
