"""Usage: compose.py lesson.json teacher.mp4 teacher.timeline.json out.mp4 --format 9x16|16x9
Run: uv run --no-project --python 3.12 --with pillow --with numpy --with soundfile python scripts/compose.py ...

Lays the lesson cards over the dubbed teacher video of ONE format and mixes the sound effects
(and MUSIC=file.m4a, optional, ~-30 dB and ducked under the voice). Each format is composed on its
own render: nothing is cropped or stretched from the other format.
  9x16   teacher full frame, card panel x 6-84 %, from y 53 % down to at most 78 %: clear of her face
         and hands (upper half), of the right-side buttons and of the bottom 22 % (platform caption and UI).
  16x9   teacher in the left half, card panel on the right (x 52-95 %, y 13-87 %), vertically centred.
Cards (lesson.json "card" per beat; null keeps the previous card, false clears it):
  example   label pill, Chinese (PingFang SC Semibold), tone-marked pinyin, Vietnamese; [x] spans in the
            accent colour (red on a "wrong" card); "mark": wrong/right adds a red cross / green tick label.
  pattern   one big formula line, e.g. "A + [比] + B + tính từ".
  challenge prompt sentence + hint; a 3-2-1 countdown badge over the challenge pause.
Each card fades and slides in (0.25 s) with a soft pop; the answer after the countdown gets a chime.
Prints every card window: WARN when one stays over 8 s (the lesson needs a visible change every
4-7 s) or a Chinese sentence is shown for less than it takes to read.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PINGFANG = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb"
            ".asset/AssetData/PingFang.ttc")
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"  # covers Vietnamese and pinyin tone marks (Arial too; PingFang lacks Vietnamese)
FACES = {"zh": (PINGFANG, 11), "bold": (AVENIR, 0), "demi": (AVENIR, 2), "medium": (AVENIR, 5)}
INK, SOFT, RED, GREEN = (24, 24, 28), (88, 88, 96), (222, 56, 60), (36, 150, 84)
LAYOUT = {  # canvas, panel box (x0, y0, x1, max y1), anchor, base sizes
    "9x16": dict(W=1080, H=1920, box=(64, 1018, 908, 1500), anchor="top",
                 size=dict(label=38, zh=100, py=50, vi=46, pattern=74, prompt=62, hint=42, badge=64)),
    "16x9": dict(W=1920, H=1080, box=(1000, 140, 1824, 940), anchor="middle",
                 size=dict(label=34, zh=92, py=46, vi=42, pattern=68, prompt=58, hint=40, badge=58)),
}
PAD = 44


def font(face, size):
    path, idx = FACES[face]
    return ImageFont.truetype(path, size, index=idx)


def is_cjk(ch):
    return "　" <= ch <= "鿿" or "＀" <= ch <= "￯"


def runs(text, base, accent):
    """[x] spans -> [(chunk, colour)]"""
    out, col, buf = [], base, ""
    for ch in text:
        if ch in "[]":
            if buf:
                out.append((buf, col))
            buf, col = "", accent if ch == "[" else base
        else:
            buf += ch
    if buf:
        out.append((buf, col))
    return out


def tokens(text, base, accent, face, size):
    """Wrap units: one CJK char, or a Latin word with its trailing space; each knows its font."""
    toks = []
    for chunk, col in runs(text, base, accent):
        word = ""
        for ch in chunk:
            if is_cjk(ch):
                if word:
                    toks.append((word, col, font(face, size)))
                    word = ""
                toks.append((ch, col, font("zh", size)))
            else:
                word += ch
                if ch == " ":
                    toks.append((word, col, font(face, size)))
                    word = ""
        if word:
            toks.append((word, col, font(face, size)))
    return toks


def layout_line(text, base, accent, face, size, width, min_ratio=0.8):
    """Shrink up to 20 %, then wrap. Returns rows of tokens and the line height."""
    for s in range(size, int(size * min_ratio) - 1, -2):
        t = tokens(text, base, accent, face, s)
        if sum(f.getlength(x) for x, _, f in t) <= width:
            return [t], s
    t, rows, cur, w = tokens(text, base, accent, face, s), [], [], 0
    for tok in t:
        tw = tok[2].getlength(tok[0])
        if cur and w + tw > width:
            rows.append(cur)
            cur, w = [], 0
        cur.append(tok)
        w += tw
    return rows + ([cur] if cur else []), s


def draw_rows(d, rows, size, x0, width, y, align="left"):
    for row in rows:
        row = list(row)
        while row and row[-1][0].strip() == "":
            row.pop()
        if row:
            row[-1] = (row[-1][0].rstrip(), row[-1][1], row[-1][2])
        w = sum(f.getlength(x) for x, _, f in row)
        x = x0 + (width - w) / 2 if align == "center" else x0
        for txt, col, f in row:
            d.text((x, y + size * 0.95), txt, font=f, fill=col, anchor="ls")
            x += f.getlength(txt)
        y += int(size * 1.32)
    return y


def pill(d, x, y, text, size, colour, mark=None):
    f = font("bold", size)
    icon = int(size * 0.9) if mark else 0
    w = f.getlength(text) + size * 1.2 + (icon + size * 0.35 if mark else 0)
    h = int(size * 1.7)
    d.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=colour)
    tx = x + size * 0.6
    if mark:
        cx, cy, r = tx + icon / 2, y + h / 2, icon * 0.32
        lw = max(4, size // 7)
        if mark == "wrong":
            d.line((cx - r, cy - r, cx + r, cy + r), fill="white", width=lw)
            d.line((cx - r, cy + r, cx + r, cy - r), fill="white", width=lw)
        else:
            d.line((cx - r, cy, cx - r * 0.25, cy + r * 0.75, cx + r * 1.05, cy - r * 0.8), fill="white", width=lw,
                   joint="curve")
        tx += icon + size * 0.35
    d.text((tx, y + h / 2), text, font=f, fill="white", anchor="lm")
    return y + h


def card_image(card, fmt, accent, countdown=None, reveal=True):
    L = LAYOUT[fmt]
    S = L["size"]
    x0, y0, x1, ymax = L["box"]
    width = x1 - x0 - 2 * PAD
    content = Image.new("RGBA", (x1 - x0, ymax - y0 + 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(content)
    mark = card.get("mark")
    tag = RED if mark == "wrong" else GREEN if mark == "right" else accent
    hi = RED if mark == "wrong" else accent
    y = PAD
    if card.get("label"):
        y = pill(d, PAD, y, card["label"], S["label"], tag, mark) + int(S["label"] * 0.7)
    kind = card["type"]
    if kind == "example":
        rows, s = layout_line(card["zh"], INK, hi, "demi", S["zh"], width, min_ratio=0.68)
        y = draw_rows(d, rows, s, PAD, width, y)
        rows, s = layout_line(card["py"], SOFT, hi, "medium", S["py"], width)
        y = draw_rows(d, rows, s, PAD, width, y) + int(S["vi"] * 0.25)
        rows, s = layout_line(card["vi"], INK if reveal else (0, 0, 0, 0), hi if reveal else (0, 0, 0, 0),
                              "demi", S["vi"], width, min_ratio=0.9)
        y = draw_rows(d, rows, s, PAD, width, y)  # hidden until spoken, its space kept so nothing jumps
    elif kind == "pattern":
        rows, s = layout_line(card["text"], INK, accent, "bold", S["pattern"], width)
        y = draw_rows(d, rows, s, PAD, width, y + int(S["pattern"] * 0.1), align="center")
    elif kind == "challenge":
        rows, s = layout_line(card["vi"], INK, accent, "demi", S["prompt"], width, min_ratio=0.9)
        y = draw_rows(d, rows, s, PAD, width, y)
        if card.get("hint"):
            rows, s = layout_line(card["hint"], SOFT, accent, "medium", S["hint"], width)
            y = draw_rows(d, rows, s, PAD, width, y + int(S["hint"] * 0.3))
    else:
        raise SystemExit(f"unknown card type {kind}")
    h = y + PAD - int(S["label"] * 0.2)
    if y0 + h > ymax:
        print(f"WARN card '{card.get('label', kind)}' is {h}px tall, panel ends {y0 + h - ymax}px below its limit")
    canvas = Image.new("RGBA", (L["W"], L["H"]), (0, 0, 0, 0))
    top = y0 if L["anchor"] == "top" else (y0 + ymax) // 2 - h // 2
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x0, top + 10, x1, top + h + 10), radius=38, fill=(0, 0, 0, 70))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    ImageDraw.Draw(canvas).rounded_rectangle((x0, top, x1, top + h), radius=38, fill=(255, 255, 255, 238))
    canvas.alpha_composite(content.crop((0, 0, x1 - x0, h)), (x0, top))
    if countdown:
        r = int(S["badge"] * 0.95)
        cx, cy = x1 - PAD - r, top + PAD + r * 0.6
        dd = ImageDraw.Draw(canvas)
        dd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=accent)
        dd.text((cx, cy), str(countdown), font=font("bold", S["badge"]), fill="white", anchor="mm")
    return canvas


def tone(freqs, dur, tau, level_db, attack=0.003):
    t = np.arange(int(dur * 48000)) / 48000
    y = sum(np.sin(2 * np.pi * f * t) / (i + 1) for i, f in enumerate(freqs))
    env = np.minimum(t / attack, 1) * np.exp(-t / tau)
    y = y * env
    return y / np.abs(y).max() * 10 ** (level_db / 20)


def windows(lesson, timeline, total):
    """[(start, end, card, beat index)] from the placed timeline."""
    first = {}
    for it in timeline["items"]:
        first.setdefault(it["beat"], it["start"])
    shown = []
    for bi, b in enumerate(lesson["beats"]):
        c = b.get("card")
        if c is None:
            continue
        t = max(0.0, first[bi] - 0.15)
        if shown:
            shown[-1][1] = t
        if c:
            shown.append([t, None, c, bi])
    if shown and shown[-1][1] is None:
        shown[-1][1] = total - 0.2
    return shown


def accent_rgb(hexcol):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def compose(lesson, video, timeline, out, fmt):
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                       "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
                                      capture_output=True, text=True, check=True).stdout)
    st = probe["streams"][0]
    total = float(probe["format"]["duration"])
    L = LAYOUT[fmt]
    if (st["width"], st["height"]) != (L["W"], L["H"]):
        sys.exit(f"{video} is {st['width']}x{st['height']}, {fmt} needs {L['W']}x{L['H']}: render that format, never crop the other")
    fps = st["r_frame_rate"]
    accent = accent_rgb(lesson.get("accent", "#FF7A1A"))
    shown = windows(lesson, timeline, total)
    pauses = [it for it in timeline["items"] if it["kind"] == "pause" and it.get("countdown")]
    sfx = np.zeros(int((total + 1) * 48000))

    def put(y, t):
        a = int(t * 48000)
        sfx[a:a + len(y)] += y[: len(sfx) - a]

    with tempfile.TemporaryDirectory() as tmp:
        layers = []  # (png, start, end, fade-in s, fade out, slide in)
        for n, (a, b, c, _bi) in enumerate(shown):
            p = Path(tmp) / f"card{n:02d}.png"
            # an example card shows the Vietnamese line when the translation is spoken: a visible step
            # inside a long card, and the learner hears the Chinese before reading the meaning
            items = [it for it in timeline["items"] if a <= it["start"] < b and it["kind"] == "speech"]
            zh_at = next((it["start"] for it in items if it["lang"] == "zh"), None)
            vi_at = next((it["start"] for it in items if it["lang"] == "vi" and zh_at is not None and it["start"] > zh_at), None)
            if c["type"] == "example" and vi_at and vi_at - a >= 1.5:
                card_image(c, fmt, accent, reveal=False).save(p)
                q = Path(tmp) / f"card{n:02d}_vi.png"
                card_image(c, fmt, accent).save(q)
                layers += [(p, a, vi_at + 0.25, 0.25, False, True), (q, vi_at, b, 0.25, True, False)]
                print(f"{vi_at:6.1f}         reveal Vietnamese")
            else:
                card_image(c, fmt, accent).save(p)
                layers.append((p, a, b, 0.25, True, True))
            after_pause = any(abs(p_["end"] - a) < 3.5 and p_["end"] <= a + 0.3 for p_ in pauses)
            put(tone([1046.5, 1568], 0.7, 0.2, -27) if after_pause else tone([660, 990], 0.09, 0.025, -30), a)
            for pz in pauses:
                if a <= pz["start"] < b:
                    step = pz["dur"] / 3
                    for k in range(3):
                        q = Path(tmp) / f"card{n:02d}_cd{k}.png"
                        card_image(c, fmt, accent, countdown=3 - k).save(q)
                        t0 = pz["start"] + k * step
                        layers.append((q, t0, t0 + step, 0, False, False))
                        put(tone([1760], 0.04, 0.012, -34), t0)
            dur = b - a
            steps = [a] + ([vi_at] if c["type"] == "example" and vi_at and vi_at - a >= 1.5 else []) + [b]
            still = max(y - x for x, y in zip(steps, steps[1:], strict=False))
            if c["type"] == "example":
                need = max(2.5, 0.25 * len([ch for ch in c["zh"] if is_cjk(ch)]) + 1.5)
                flag = "  WARN too short to read" if dur < need else ""
            else:
                flag = ""
            if still > 8:
                flag += f"  WARN no visible change for {still:.1f} s (give the next beat its own card)"
            print(f"{a:6.1f}-{b:6.1f}  {c['type']:9s} {c.get('label', '')[:28]:28s}{flag}")
        sfx_wav = Path(tmp) / "sfx.wav"
        sf.write(sfx_wav, sfx.astype(np.float32), 48000)

        args = ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(sfx_wav)]
        music = os.environ.get("MUSIC")
        if music:
            args += ["-stream_loop", "-1", "-i", music]
        first_png = 3 if music else 2
        for p, a, b, *_ in layers:
            args += ["-loop", "1", "-framerate", fps, "-t", f"{b - a:.3f}", "-i", str(p)]
        fc, last = [], "0:v"
        for i, (_p, a, b, fin, fout, slide) in enumerate(layers):
            idx = first_png + i
            fade = f"fade=t=in:st=0:d={fin}:alpha=1," if fin else ""
            if fout:
                fade += f"fade=t=out:st={max(0, b - a - 0.2):.3f}:d=0.2:alpha=1,"
            fc.append(f"[{idx}:v]format=rgba,{fade}setpts=PTS+{a:.3f}/TB[c{i}]")
            y = f"'if(lt(t-{a:.3f},0.25),24*(1-(t-{a:.3f})/0.25),0)'" if slide else "0"
            fc.append(f"[{last}][c{i}]overlay=x=0:y={y}:eof_action=pass:eval=frame[v{i}]")
            last = f"v{i}"
        if music:
            fc.append("[0:a]asplit[v1][v2]")
            fc.append("[2:a]volume=-30dB[m]")
            fc.append("[m][v2]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400[duck]")
            fc.append("[v1][1:a][duck]amix=inputs=3:normalize=0[a]")
        else:
            fc.append("[0:a][1:a]amix=inputs=2:normalize=0[a]")
        args += ["-filter_complex", ";".join(fc), "-map", f"[{last}]", "-map", "[a]", "-t", f"{total:.3f}",
                 "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
        subprocess.run(args, check=True)
        # one gain for the whole mix (voice.py loudnorm_args): -16 LUFS without lifting the room tone
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from voice import loudnorm_args
        tmp_out = Path(tmp) / out.name
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-map", "0:v", "-map", "0:a", "-c:v", "copy",
                        "-af", loudnorm_args(out), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                        str(tmp_out)], check=True)
        os.replace(tmp_out, out)
    print(f"-> {out}")


if __name__ == "__main__":
    fmt = sys.argv[sys.argv.index("--format") + 1]
    compose(json.load(open(sys.argv[1])), Path(sys.argv[2]), json.load(open(sys.argv[3])), Path(sys.argv[4]), fmt)
