"""Burn the opening title card and the bilingual subtitles (English above Simplified Chinese).

  uv run --no-project --python 3.12 --with pillow python scripts/finish.py film.mp4 WORK final.mp4

WORK/title.json  {"en": "Larkmont, Pennsylvania", "year": "October 1985", "zh": "宾夕法尼亚州·拉克蒙特",
                  "start": 0.8, "hold": 4.5,                       (start/hold optional)
                  "series": "The Larkmont Years · Episode 1",      (optional: the series frame)
                  "episode": {"en": "The Car That Wouldn't Start", "zh": "打不着火的车"},
                  "next": {"en": "Lunch at the Ridge Diner", "zh": "山脊餐馆的午餐", "hold": 4.0}}
  With "series"/"episode" the opening card names the series and the episode (the place and month
  go small underneath); with "next" an end card over the last shot teases the next episode, so
  every episode reads as one chapter of the series.
WORK/cues.json   [[start, end, en, zh, KEY], ...] aligned to the speech (align.py)
Also writes final.srt and final.vtt next to final.mp4 from the same cues.

Look (references/look.md): title in a warm-white serif with a soft shadow, centred a little above
the middle, fading in and out; subtitles small, white, thin dark outline, bottom-centre inside a
safe area (x 10-90 %, last row ends at 93 % height), at most two rows per language, one cue per
utterance, shown 0.1 s before the speech until 0.5 s after it (or the next cue)."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"
SANS = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
ZH = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb"
      ".asset/AssetData/PingFang.ttc")
for f in (SERIF, SANS, ZH):
    if not Path(f).exists():
        sys.exit(f"font missing: {f}")
SAFE_X, BOTTOM, MAXW = int(W * 0.10), int(H * 0.93), int(W * 0.80)
EN_PX, ZH_PX, STROKE, GAP = 46, 44, 3, 6


def font(path, size):
    return ImageFont.truetype(path, size, index=11 if path.endswith(".ttc") else 0)


def wrap(text, f, cjk):
    """At most two rows: split at the space (or CJK punctuation) nearest the middle."""
    if f.getlength(text) <= MAXW:
        return [text]
    half = f.getlength(text) / 2
    if cjk:
        marks = [i + 1 for i, ch in enumerate(text[:-1]) if ch in "，。？！、；：,?!"] or list(range(1, len(text)))
        k = min(marks, key=lambda i: abs(f.getlength(text[:i]) - half))
        return [text[:k], text[k:]]
    ws = text.split()
    k = min(range(1, len(ws)), key=lambda i: abs(f.getlength(" ".join(ws[:i])) - half))
    return [" ".join(ws[:k]), " ".join(ws[k:])]


def sub_png(en, zh, dest):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fe, fz = font(SANS, EN_PX), font(ZH, ZH_PX)
    rows = [(fe, r) for r in wrap(en, fe, False)] + [(fz, r) for r in wrap(zh, fz, True)]
    y = BOTTOM - sum(f.size * 1.18 for f, _ in rows) - GAP * (len(rows) - 1)
    for f, r in rows:
        x = (W - f.getlength(r)) / 2
        d.text((x + 2, y + 2), r, font=f, fill=(0, 0, 0, 120))  # soft drop shadow
        d.text((x, y), r, font=f, fill=(255, 255, 255, 255), stroke_width=STROKE, stroke_fill=(16, 16, 16, 220))
        y += f.size * 1.18 + GAP
    img.save(dest)


def title_png(t, dest):
    if t.get("episode"):
        lines = [(font(SERIF, 40), t.get("series", "").upper()), (font(SERIF, 92), t["episode"]["en"]),
                 (font(ZH, 54), t["episode"].get("zh", "")), (font(SERIF, 40), f"{t['en']} · {t.get('year', '')}")]
    else:
        lines = [(font(SERIF, 84), t["en"]), (font(SERIF, 76), t.get("year", "")), (font(ZH, 50), t.get("zh", ""))]
    card_png([(f, x) for f, x in lines if x], dest, 0.40)


def next_png(t, dest):
    series = t.get("series", "").split(" · ")[0]
    lines = [(font(SERIF, 40), f"NEXT TIME ON {series.upper()}" if series else "NEXT TIME"),
             (font(SERIF, 72), t["next"]["en"]), (font(ZH, 50), t["next"].get("zh", ""))]
    card_png([(f, x) for f, x in lines if x], dest, 0.36)


def card_png(lines, dest, centre):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y = H * centre - sum(f.size * 1.2 for f, _ in lines) / 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds, dt = ImageDraw.Draw(shadow), ImageDraw.Draw(img)
    for f, txt in lines:
        x = (W - f.getlength(txt)) / 2
        ds.text((x + 3, y + 4), txt, font=f, fill=(30, 20, 10, 170))
        dt.text((x, y), txt, font=f, fill=(255, 248, 236, 255))
        y += f.size * 1.2
    Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)), img).save(dest)


def ts(t, sep):
    return f"{int(t // 3600):02}:{int(t % 3600 // 60):02}:{int(t % 60):02}{sep}{int(round(t % 1 * 1000)) % 1000:03}"


def main():
    film, work, out = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    cues = json.loads((work / "cues.json").read_text())
    title = json.loads((work / "title.json").read_text())
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", film],
                               capture_output=True, text=True, check=True).stdout)
    tmp = Path(tempfile.mkdtemp())
    t0, hold = title.get("start", 0.8), title.get("hold", 4.5)
    title_png(title, tmp / "title.png")
    args = ["ffmpeg", "-v", "error", "-y", "-i", film, "-loop", "1", "-t", f"{t0 + hold + 1:.2f}", "-i", str(tmp / "title.png")]
    chain = [f"[1:v]format=rgba,fade=t=in:st={t0}:d=0.7:alpha=1,fade=t=out:st={t0 + hold - 0.8}:d=0.8:alpha=1[tt]",
             "[0:v][tt]overlay=0:0:eof_action=pass[v0]"]
    prev, timed, k = "v0", [], 2
    if title.get("next"):
        nh = title["next"].get("hold", 4.0)
        ns = dur - nh
        next_png(title, tmp / "next.png")
        args += ["-loop", "1", "-t", f"{dur:.2f}", "-i", str(tmp / "next.png")]
        chain += [f"[2:v]format=rgba,fade=t=in:st={ns:.2f}:d=0.8:alpha=1[nt]",
                  f"[v0][nt]overlay=0:0:enable='gte(t,{ns:.2f})'[vn]"]
        prev, k = "vn", 3
    for i, (s, e, en, zh, *_) in enumerate(cues):
        nxt = cues[i + 1][0] - 0.05 if i + 1 < len(cues) else dur
        a, b = max(0.0, s - 0.1), min(nxt, e + 0.5)
        timed.append((a, b, en, zh))
        png = tmp / f"c{i:03}.png"
        sub_png(en, zh, png)
        args += ["-i", str(png)]
        chain.append(f"[{prev}][{i + k}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[v{i + 1}]")
        prev = f"v{i + 1}"
    args += ["-filter_complex", ";".join(chain), "-map", f"[{prev}]", "-map", "0:a", "-c:v", "libx264", "-crf", "17",
             "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", out]
    subprocess.run(args, check=True)
    stem = Path(out).with_suffix("")
    Path(f"{stem}.srt").write_text("\n".join(f"{n}\n{ts(a, ',')} --> {ts(b, ',')}\n{en}\n{zh}\n"
                                             for n, (a, b, en, zh) in enumerate(timed, 1)))
    Path(f"{stem}.vtt").write_text("WEBVTT\n\n" + "\n".join(f"{ts(a, '.')} --> {ts(b, '.')}\n{en}\n{zh}\n"
                                                            for a, b, en, zh in timed))
    print(f"WROTE {out}, {stem}.srt, {stem}.vtt ({len(cues)} cues)")


main()
