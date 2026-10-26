"""Usage: [BOX=x0,y0,x1,y1] burn_subs.py video.mp4 cues.json out.mp4
BOX: caption area in % of the frame when the brief sets one (e.g. BOX=10,62,82,76).
cues.json: [[speech_start, speech_end, zh, pinyin, vi], ...] -> 3-line subtitles burned in."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BOX = (65, 1094, 907, 1440)  # x6-84%, y57-75%: block centred ~66%, bottom 25% + right edge clear
if os.environ.get("BOX"):
    x0, y0, x1, y1 = (float(v) / 100 for v in os.environ["BOX"].split(","))
    BOX = (round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H))
ZH_FONT = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb"
           ".asset/AssetData/PingFang.ttc")
LATIN_FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
LINES = [(ZH_FONT, 112, 8), (LATIN_FONT, 66, 6), (LATIN_FONT, 66, 6)]  # font, max size, stroke
GAP = 6
MIN_RATIO = 0.75  # shrink a line at most to 75% of its size, then wrap it instead


def font_at(path, size):
    return ImageFont.truetype(path, size, index=11 if path.endswith(".ttc") else 0)


def fit(path, size, text):
    """Rows for one caption line: shrink a little, else wrap at the space nearest the middle."""
    width = BOX[2] - BOX[0]
    for s in range(size, int(size * MIN_RATIO) - 1, -2):
        if font_at(path, s).getlength(text) <= width:
            return [(font_at(path, s), text)]
    half = font_at(path, size).getlength(text) / 2
    words = text.split(" ")
    if len(words) >= 2:
        cut = min(range(1, len(words)),
                  key=lambda i: abs(font_at(path, size).getlength(" ".join(words[:i])) - half))
        parts = [" ".join(words[:cut]), " ".join(words[cut:])]
    else:  # Chinese has no spaces: break after the punctuation nearest the middle, else mid-text
        marks = [i + 1 for i, ch in enumerate(text[:-1]) if ch in "，。？！、；：,?!"]
        cut = min(marks or range(1, len(text)), key=lambda i: abs(font_at(path, size).getlength(text[:i]) - half))
        parts = [text[:cut], text[cut:]]
    s = size
    while s > 20 and max(font_at(path, s).getlength(p) for p in parts) > width:
        s -= 2
    return [(font_at(path, s), p) for p in parts]


def row_h(font, stroke):
    return font.size * 1.02 + 2 * stroke


def layout(texts, scale):
    rows = []
    for (path, size, stroke), text in zip(LINES, texts):
        rows += [(font, line, stroke) for font, line in fit(path, int(size * scale), text)]
    height = sum(row_h(f, st) for f, _, st in rows) + GAP * (len(rows) - 1)
    return rows, height


def render(texts, dest):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    scale = 1.0
    rows, height = layout(texts, scale)
    while height > BOX[3] - BOX[1] and scale > 0.6:  # wrapped lines overflow -> shrink all evenly
        scale -= 0.04
        rows, height = layout(texts, scale)
    y = BOX[1] + (BOX[3] - BOX[1] - height) / 2
    cx = (BOX[0] + BOX[2]) / 2
    for font, line, stroke in rows:
        draw.text((cx, y + row_h(font, stroke) / 2), line, font=font, anchor="mm", fill="white",
                  stroke_width=stroke, stroke_fill=(20, 20, 20, 235))
        y += row_h(font, stroke) + GAP
    img.save(dest)


def main():
    video, cues_path, out = sys.argv[1:4]
    cues = json.load(open(cues_path))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                "csv=p=0", video], capture_output=True, text=True).stdout)
    tmp = Path(tempfile.mkdtemp())
    args, chain, prev = ["ffmpeg", "-v", "error", "-y", "-i", video], [], "0:v"
    for i, (s, e, *texts) in enumerate(cues):
        nxt = cues[i + 1][0] - 0.15 if i + 1 < len(cues) else dur
        start, end = max(0, s - 0.15), min(nxt, e + 0.7) if i + 1 < len(cues) else dur
        png = tmp / f"c{i:02}.png"
        render(texts, png)
        args += ["-i", str(png)]
        chain.append(f"[{prev}][{i + 1}:v]overlay=0:0:enable='between(t,{start:.2f},{end:.2f})'[v{i}]")
        prev = f"v{i}"
    args += ["-filter_complex", ";".join(chain), "-map", f"[{prev}]", "-map", "0:a", "-c:v", "libx264",
             "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy",
             "-movflags", "+faststart", out]
    subprocess.run(args, check=True)
    print("WROTE", out, "pngs in", tmp)


main()
