# /// script
# dependencies = ["pillow", "fonttools"]
# ///
"""Assemble a travel reel from a template (templates.json): intro, beat-synced shots, transitions,
text overlays, grade, music.

Usage:
  uv run --no-project --python 3.12 --with pillow --with fonttools python scripts/compose.py \
      --template pin-flow-right --place "Amalfi Coast" --music track.m4a --out reel.mp4 \
      s1.mp4 s2.mp4@2.0 s3.mp4 ...
  [--flag 🇮🇹] [--labels "Positano|Ravello|..."] [--coords "40.63° N  14.48° E"] [--beats track.beats.json]

Timing comes from the music's beat grid (track.beats.json written by music.py: {"beats": [...],
"drop": t|null}). With a "drop" the first shot starts on it (the intro card fills 0..drop);
otherwise after the template's intro.beats. Shot k lasts plan.shots[k].beats (--plan; pick.py
varies them per reel) or the template's pattern[k] beats; every cut sits on a
beat, every transition is centred on its beat. Output fps = the clips' fps (24 for muse), so each
source frame is shown once. Each shot's window defaults to @auto: the stretch whose motion is
closest to the template's target and most even (YDIF), skipping jumps; clip@seconds forces it.
"""
import argparse
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from fontTools.ttLib import TTCollection
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SKILL = Path(__file__).resolve().parent.parent
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"
FONTS = {  # (file, face index)
    "serif": ("/System/Library/Fonts/Supplemental/Georgia Bold.ttf", 0),
    "didot": ("/System/Library/Fonts/Supplemental/Didot.ttc", 2),
    "heavy": ("/System/Library/Fonts/Avenir Next.ttc", 8),
    "demi": ("/System/Library/Fonts/Avenir Next.ttc", 2),
    "futura": ("/System/Library/Fonts/Supplemental/Futura.ttc", 4),
    "light": ("/System/Library/Fonts/HelveticaNeue.ttc", 7),
}
GRADES = {
    "vivid": "eq=saturation=1.22:contrast=1.06,unsharp=5:5:0.6",
    "clean": "eq=saturation=1.08:contrast=1.03,unsharp=5:5:0.4",
    "warm-film": "colorbalance=rm=0.06:bm=-0.06:rh=0.04:bh=-0.05,eq=saturation=1.08:contrast=1.04,"
                 "vignette=PI/5,noise=alls=5:allf=t",
    "teal-orange": "colorbalance=rs=-0.06:bs=0.07:rh=0.07:bh=-0.07,eq=saturation=1.15:contrast=1.08,unsharp=5:5:0.5",
    "pastel": "eq=saturation=0.88:brightness=0.04:contrast=0.92,colorbalance=rh=0.03:bh=0.03",
    "moody": "eq=saturation=0.75:contrast=1.1:brightness=-0.03,colorbalance=bs=0.06:bm=0.03,vignette=PI/4",
    "neon": "eq=saturation=1.3:contrast=1.1,colorbalance=bs=0.06:rh=0.05,unsharp=5:5:0.5",
}
# transition -> (xfade name, duration s); whip/rise pick their direction from the outgoing move
XF = {"cut": ("fade", 0), "whip": ("slideleft", 0.2), "zoom": ("zoomin", 0.3), "flash": ("fadewhite", 0.3),
      "dip": ("fadeblack", 0.5), "dissolve": ("fade", 0.6), "circle": ("circleopen", 0.5),
      "rise": ("slidedown", 0.25), "blur": ("hblur", 0.25)}
WHIP_DIR = {"lateral-left": "slideright", "orbit-right": "slideright", "rise": "slidedown",
            "top-down": "slidedown", "pull-out": "slideup"}


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]))


def fps(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
               "-of", "csv=p=0", path]).strip()
    num, _, den = out.partition("/")
    return float(num) / float(den or 1)


def ydif(path, w=270):
    """Per-frame mean |luma change| (ffmpeg signalstats YDIF) on a small copy: how fast the picture moves."""
    out = run(["ffmpeg", "-v", "error", "-i", path, "-vf",
               f"scale={w}:-2,signalstats,metadata=print:key=lavfi.signalstats.YDIF:file=-", "-an", "-f", "null", "-"])
    return [float(line.split("=")[1]) for line in out.splitlines() if "YDIF=" in line]


def pick_window(d, n, src_fps, target):
    """(score, start frame, mean, std) of the n-frame window moving steadily at about `target` YDIF/frame.
    Reference shots move slowly and evenly; a window with a jump (> 3x its median) reads as a jolt."""
    lo, hi = round(0.5 * src_fps), len(d) - n - 1
    best = None
    for j in range(max(1, min(lo, hi)), max(hi, 1) + 1):
        win = d[j:j + n]
        if len(win) < n:
            break
        mean = sum(win) / n
        std = (sum((x - mean) ** 2 for x in win) / n) ** 0.5
        med = sorted(win)[n // 2]
        score = abs(mean - target) + 1.5 * std + (100 if max(win) > 3 * med + 5 else 0)
        if best is None or score < best[0]:
            best = (score, j, mean, std)
    return best or (0, 0, 0, 0)


# ---------- text ----------
def font(kind, size):
    path, idx = FONTS[kind]
    return ImageFont.truetype(path, size, index=idx)


def emoji(text, height):
    # Pillow without raqm can't shape emoji (flags are 2-codepoint ligatures), so take the glyph's
    # 160 px PNG straight from Apple Color Emoji's sbix table (named u1F1E8_u1F1ED, u1F4CD ...)
    f = TTCollection(EMOJI_FONT, lazy=True).fonts[0]
    name = "_".join(f"u{ord(c):04X}" for c in text if ord(c) != 0xFE0F)
    glyph = f["sbix"].strikes[160].glyphs.get(name)
    if glyph is None or glyph.graphicType != "png ":
        sys.exit(f"no emoji bitmap for {text!r} ({name})")
    img = Image.open(io.BytesIO(glyph.imageData)).convert("RGBA")
    img = img.crop(img.getbbox())
    return img.resize((round(img.width * height / img.height), height), Image.LANCZOS)


def split_emoji(text):
    """'Italy 🇮🇹' -> ('Italy', '🇮🇹'); emoji only at the end are supported."""
    i = len(text)
    while i and (ord(text[i - 1]) > 0x2500 or ord(text[i - 1]) == 0xFE0F):
        i -= 1
    return text[:i].rstrip(), text[i:]


def line(d, img, xy, text, f, fill="white", anchor="ms", shadow=True, stroke=0, spacing=0):
    """Draw text (+ trailing emoji) centred/anchored at xy, with a soft shadow; returns width."""
    words, emo = split_emoji(text)
    tw = d.textlength(words, font=f) + spacing * max(len(words) - 1, 0)
    eh = round(f.size * 0.8)
    em = emoji(emo, eh) if emo else None
    total = tw + (em.width + f.size * 0.2 if em else 0)
    x0 = xy[0] - total / 2 if anchor[0] == "m" else xy[0]
    if shadow:
        sh = Image.new("RGBA", img.size)
        sd = ImageDraw.Draw(sh)
        _chars(sd, (x0 + 3, xy[1] + 4), words, f, (0, 0, 0, 150), spacing, stroke)
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(f.size / 10)))
    _chars(d, (x0, xy[1]), words, f, fill, spacing, stroke)
    if em:
        img.alpha_composite(em, (round(x0 + tw + f.size * 0.2), round(xy[1] - eh)))
    return total


def _chars(d, xy, text, f, fill, spacing, stroke):
    if not spacing:
        d.text(xy, text, font=f, fill=fill, anchor="ls", stroke_width=stroke, stroke_fill=(0, 0, 0, 200))
        return
    x = xy[0]
    for c in text:
        d.text((x, xy[1]), c, font=f, fill=fill, anchor="ls", stroke_width=stroke, stroke_fill=(0, 0, 0, 200))
        x += d.textlength(c, font=f) + spacing


def canvas(w, h):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def fit(d, text, kind, start, maxw, spacing_ratio=0.0):
    size = start
    while size > 20:
        f = font(kind, size)
        words, emo = split_emoji(text)
        width = d.textlength(words, font=f) + size * spacing_ratio * max(len(words) - 1, 0)
        if emo:  # line() draws the emoji 0.8*size wide after a 0.2*size gap
            width += size
        if width <= maxw:
            return f, round(size * spacing_ratio)
        size -= 4
    return font(kind, size), 0


def ov_title(w, h, text, y=0.45, kind="didot", size=0.13):
    img, d = canvas(w, h)
    f, _ = fit(d, text, kind, round(w * size), w * 0.86)
    line(d, img, (w / 2, h * y), text, f)
    return img


def ov_bigword(w, h, text):
    img, d = canvas(w, h)
    t = text.upper()
    f, sp = fit(d, t, "futura", round(w * 0.24), w * 0.9, spacing_ratio=0.12)
    line(d, img, (w / 2, h * 0.53), t, f, spacing=sp)
    return img


def ov_pin(w, h, text):
    img, d = canvas(w, h)
    f = font("demi", round(w * 0.045))
    pin = emoji("📍", round(f.size * 1.0))
    tw = d.textlength(text, font=f)
    pad = f.size * 0.55
    x0, y1 = w * 0.07, h * 0.80
    box = (x0, y1 - f.size - pad * 1.6, x0 + pin.width + pad * 2.6 + tw, y1)
    d.rounded_rectangle(box, radius=(box[3] - box[1]) / 2, fill=(255, 255, 255, 230))
    img.alpha_composite(pin, (round(x0 + pad), round(box[1] + (box[3] - box[1] - pin.height) / 2)))
    d.text((x0 + pad * 1.6 + pin.width, (box[1] + box[3]) / 2), text, font=f, fill=(20, 20, 20), anchor="lm")
    return img


def ov_pov(w, h, text):
    img, d = canvas(w, h)
    f = font("heavy", round(w * 0.058))
    words, rows, cur = text.split(), [], ""
    for wd in words:
        nxt = (cur + " " + wd).strip()
        if d.textlength(nxt, font=f) > w * 0.82 and cur:
            rows.append(cur)
            cur = wd
        else:
            cur = nxt
    rows.append(cur)
    for i, r in enumerate(rows):
        line(d, img, (w / 2, h * 0.2 + i * f.size * 1.2), r, f, stroke=round(f.size * 0.06))
    return img


def ov_card(w, h, title, sub=None):
    """Black full-frame card: title (with trailing emoji) at 28 % height, optional line below."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    f, _ = fit(d, title, "serif", round(w * 0.068), w * 0.86)
    y = round(h * 0.28)
    line(d, img, (w / 2, y), title, f, shadow=False)
    if sub is not None:
        line(d, img, (w / 2, y + round(f.size * 1.15)), sub, f, shadow=False)
    return img


def ov_center_card(w, h, text):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    f, sp = fit(d, text, "futura", round(w * 0.11), w * 0.86, spacing_ratio=0.08)
    line(d, img, (w / 2, h * 0.5), text, f, shadow=False, spacing=sp)
    return img


def ov_coords(w, h, coords, place, shown):
    """Typewriter frame: first `shown` chars of coords, place name under it once complete."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    f = font("light", round(w * 0.05))
    d.text((w / 2 - d.textlength(coords, font=f) / 2, h * 0.47), coords[:shown] + ("|" if shown < len(coords) else ""),
           font=f, fill="white", anchor="ls")
    if shown >= len(coords):
        g, sp = fit(d, place.upper(), "futura", round(w * 0.075), w * 0.86, spacing_ratio=0.2)
        line(d, img, (w / 2, h * 0.56), place.upper(), g, shadow=False, spacing=sp)
    return img


def ov_number(w, h, n, label):
    img, d = canvas(w, h)
    f = font("futura", round(w * 0.2))
    line(d, img, (w * 0.08, h * 0.2), f"{n}", f, anchor="ls")
    if label:
        g = font("heavy", round(w * 0.058))
        line(d, img, (w * 0.09, h * 0.2 + g.size * 1.3), label, g, anchor="ls")
    return img


def ov_label(w, h, label):
    img, d = canvas(w, h)
    g = font("demi", round(w * 0.05))
    d.line((w * 0.08, h * 0.83, w * 0.18, h * 0.83), fill="white", width=4)
    line(d, img, (w * 0.08, h * 0.81), label, g, anchor="ls")
    return img


def ov_time(w, h, t, place):
    img, d = canvas(w, h)
    f = font("futura", round(w * 0.11))
    line(d, img, (w * 0.08, h * 0.16), t, f, anchor="ls")
    if place:
        g = font("demi", round(w * 0.045))
        line(d, img, (w * 0.085, h * 0.16 + g.size * 1.4), place, g, anchor="ls")
    return img


# ---------- timeline ----------
def beat_grid(a, music_len):
    side = Path(a.beats) if a.beats else Path(a.music).with_suffix(".beats.json")
    if side.exists():
        info = json.loads(side.read_text())
        return info["beats"], info.get("drop")
    if not a.bpm:
        sys.exit(f"no beat file {side}; run music.py or pass --bpm (and --drop)")
    step = 60 / a.bpm
    drop = a.drop or 0.0
    first = drop - step * int(drop / step)
    return [first + k * step for k in range(int((music_len - first) / step) + 64)], a.drop


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+", help="shot.mp4, shot.mp4@start_seconds or shot.mp4@auto, in order")
    ap.add_argument("--template", help="default: the plan's")
    ap.add_argument("--plan", help="plan.json from pick.py: per-shot beats (default: the template's pattern)")
    ap.add_argument("--place", required=True, help="name shown in titles, e.g. 'Amalfi Coast'")
    ap.add_argument("--title", help="override the intro text")
    ap.add_argument("--flag", default="", help="emoji after the title, e.g. 🇮🇹")
    ap.add_argument("--labels", default="", help="'A|B|C' per-shot names for number/label templates")
    ap.add_argument("--coords", default="", help="coords intro text, e.g. '40.63° N  14.48° E'")
    ap.add_argument("--music", required=True)
    ap.add_argument("--beats", help="beat file (default <music>.beats.json)")
    ap.add_argument("--bpm", type=float, help="no beat file: constant grid at this BPM")
    ap.add_argument("--drop", type=float, help="no beat file: time of the drop (first shot)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=float, help="default: first clip's")
    a = ap.parse_args()

    plan = json.loads(Path(a.plan).read_text()) if a.plan else None
    a.template = a.template or (plan and plan["template"]) or ap.error("--template or --plan")
    data = json.loads((SKILL / "templates.json").read_text())
    t = next((x for x in data["templates"] if x["id"] == a.template), None) or sys.exit(f"no template {a.template}")
    w, h = map(int, a.size.split("x"))
    clips = a.clips
    n = len(clips)
    if plan and len(plan["shots"]) != n:
        sys.exit(f"{n} clips for {len(plan['shots'])} planned shots")
    F = a.fps or fps(clips[0].partition("@")[0])
    music_len = duration(a.music)
    beats, drop = beat_grid(a, music_len)
    step = (beats[-1] - beats[0]) / max(len(beats) - 1, 1)

    def beat_t(i):
        return beats[i] if i < len(beats) else beats[-1] + (i - len(beats) + 1) * step

    intro = t["intro"]
    card_intro = intro["type"] in ("countdown", "black-title", "coords")
    if drop is not None and card_intro:
        b0 = min(range(len(beats)), key=lambda i: abs(beats[i] - drop))
    else:
        b0 = intro["beats"] if card_intro else 0
    idx = [b0]
    for k in range(n):
        idx.append(idx[-1] + (plan["shots"][k]["beats"] if plan else t["pattern"][k % len(t["pattern"])]))
    T = [round(beat_t(i) * F) for i in idx]  # frame of each cut; T[0] = first shot
    if not card_intro:
        T[0] = 0
    end = T[-1]
    if end / F > music_len + 0.7:
        print(f"warning: reel {end / F:.1f}s outruns the music {music_len:.1f}s", file=sys.stderr)

    # segments: optional black intro, then shots
    segs = ([{"kind": "intro", "a": 0, "b": T[0]}] if card_intro and T[0] > 0 else []) + \
           [{"kind": "shot", "k": k, "a": T[k], "b": T[k + 1]} for k in range(n)]
    moves = t["moves"]
    trans = t["transitions"]
    for i, s in enumerate(segs):  # transition INTO segment i (from i-1)
        if i == 0:
            s["xf"], s["d"] = None, 0
            continue
        name = trans[(i - 1) % len(trans)]
        if segs[i - 1]["kind"] == "intro" and intro["type"] == "countdown":
            name = "cut"
        xf, dur = XF[name]
        if name in ("whip", "rise") and segs[i - 1]["kind"] == "shot":
            xf = WHIP_DIR.get(moves[segs[i - 1]["k"] % len(moves)], xf)
        slot = min(s["b"] - s["a"], segs[i - 1]["b"] - segs[i - 1]["a"])
        d = max(1, min(round(dur * F), slot // 2))
        s["xf"], s["d"] = xf, d

    tmp = Path(tempfile.mkdtemp(prefix="compose-"))
    inputs, chains, used = [], [], []
    grade = GRADES[t["grade"]]
    for i, s in enumerate(segs):
        d_in = s["d"]
        d_out = segs[i + 1]["d"] if i + 1 < len(segs) else 0
        s["off"] = s["a"] - d_in // 2  # frame where this segment's xfade starts
        length = (s["b"] + d_out - d_out // 2) - s["off"]
        s["len"] = length
        if s["kind"] == "intro":
            inputs += ["-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={F:g}:d={length / F + 0.1:.3f}"]
            chains.append(f"[{_count(inputs)}:v]trim=end_frame={length},setpts=PTS-STARTPTS,format=yuv420p,"
                          f"setsar=1,settb=AVTB[s{i}]")
            continue
        k = s["k"]
        path, _, start = clips[k].partition("@")
        src_fps = fps(path)
        ramp = round(min(0.3, (s["b"] - s["a"]) / F / 3) * F) if t["ramp"] and d_out else 0
        n_src = round((length - ramp + 2.5 * ramp) * src_fps / F)
        info = {"clip": path, "beats": idx[k + 1] - idx[k]}
        if start in ("", "auto"):
            _, j, mean, std = pick_window(ydif(path), n_src, src_fps, t["target"] * F / src_fps)
            st = j / src_fps
            info.update(motion=round(mean, 1), steady=round(std, 1))
            if mean > 1.6 * t["target"]:
                print(f"warning: {path} moves fast even at its calmest (YDIF {mean:.1f}): re-render slower",
                      file=sys.stderr)
        else:
            st = float(start)
        st = max(0.0, min(st, duration(path) - n_src / src_fps - 0.02))
        info["start"] = round(st, 2)
        used.append(info)
        inputs += ["-ss", f"{st:.3f}", "-i", path]
        src = _count(inputs)
        base = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setpts=PTS-STARTPTS,fps={F:g},"
                f"{grade},format=yuv420p,setsar=1")
        if ramp:  # last `ramp` frames play 2.5x: the move accelerates into the cut
            keep = length - ramp
            chains.append(f"[{src}:v]{base},split[a{i}][b{i}];[a{i}]trim=end_frame={keep},setpts=PTS-STARTPTS[p{i}];"
                          f"[b{i}]trim=start_frame={keep},setpts=(PTS-STARTPTS)/2.5,fps={F:g},"
                          f"trim=end_frame={ramp},setpts=PTS-STARTPTS[q{i}];"
                          f"[p{i}][q{i}]concat=n=2:v=1:a=0,settb=AVTB[s{i}]")
        else:
            chains.append(f"[{src}:v]{base},trim=end_frame={length},setpts=PTS-STARTPTS,settb=AVTB[s{i}]")

    cur = "s0"
    for i in range(1, len(segs)):
        s = segs[i]
        # offset a quarter frame early: ffmpeg 9 xfade drops the second input when the offset lands
        # exactly on the first input's last frame (Tromsø reel: 53 of 262 frames)
        chains.append(f"[{cur}][s{i}]xfade=transition={s['xf']}:duration={s['d'] / F:.4f}:"
                      f"offset={(s['off'] - 0.25) / F:.4f}[x{i}]")
        cur = f"x{i}"

    # overlays: (image, start frame, end frame, fade)
    place = a.place
    title = a.title or intro.get("text", "{place}").replace("{place}", place).replace("{PLACE}", place.upper()) \
        .replace("{n}", str(n))
    ovs = []
    shot0 = segs[1] if segs[0]["kind"] == "intro" else segs[0]
    kind = intro["type"]
    if kind == "countdown":
        cuts = [0, round(T[0] / 3), round(2 * T[0] / 3), T[0]]
        for c, num in enumerate((3, 2, 1)):
            ovs.append((ov_card(w, h, f"{(a.title or place).upper()} {a.flag}".strip(), str(num)), cuts[c], cuts[c + 1], 0))
    elif kind == "black-title":
        ovs.append((ov_center_card(w, h, f"{title} {a.flag}".strip()), 0, T[0], 0.3))
    elif kind == "coords":
        coords = a.coords or place.upper()
        steps = min(len(coords), 24)
        typing = round(T[0] * 0.6)
        for c in range(steps):
            shown = round(len(coords) * (c + 1) / steps)
            ovs.append((ov_coords(w, h, coords, place, shown) if a.coords else ov_center_card(w, h, place.upper()),
                        round(typing * c / steps), round(typing * (c + 1) / steps) if c < steps - 1 else T[0], 0))
    elif kind == "pin":
        ovs.append((ov_pin(w, h, f"{place}"), round(0.25 * F), segs[min(1, len(segs) - 1)]["b"], 0.25))
    elif kind == "pov":
        ovs.append((ov_pov(w, h, title), 0, shot0["b"] + (segs[1]["b"] - segs[1]["a"] if len(segs) > 1 else 0), 0.2))
    elif kind == "title":
        ovs.append((ov_title(w, h, f"{title} {a.flag}".strip()), round(0.2 * F), shot0["b"], 0.4))
    elif kind == "bigword":
        ovs.append((ov_bigword(w, h, a.title or place), 0, shot0["b"], 0.15))
    labels = [x.strip() for x in a.labels.split("|")] if a.labels else []
    per = t["text"].get("per_shot")
    for s in segs:
        if s["kind"] != "shot" or not per:
            continue
        k = s["k"]
        lab = labels[k] if k < len(labels) else ""
        if per == "number":
            img = ov_number(w, h, k + 1, lab)
        elif per == "label" and lab:
            img = ov_label(w, h, lab)
        elif per == "time":
            img = ov_time(w, h, t["times"][k % len(t["times"])], lab)
        else:
            continue
        ovs.append((img, s["a"] + round(0.1 * F), s["b"] - 1, 0.15))
    if t["text"].get("outro"):
        last = segs[-1]
        ovs.append((ov_title(w, h, t["text"]["outro"], y=0.5, kind="heavy", size=0.07),
                    max(last["a"], last["b"] - round(1.6 * F)), last["b"], 0.25))

    for o, (img, fa, fb, fade) in enumerate(ovs):
        png = tmp / f"ov{o}.png"
        img.save(png)
        dur = max(1, fb - fa) / F
        inputs += ["-loop", "1", "-framerate", f"{F:g}", "-t", f"{dur:.4f}", "-i", str(png)]
        src = _count(inputs)
        fx = f",fade=t=in:st=0:d={fade}:alpha=1,fade=t=out:st={max(0, dur - fade):.4f}:d={fade}:alpha=1" if fade else ""
        chains.append(f"[{src}:v]format=rgba{fx},setpts=PTS+{fa / F:.4f}/TB[o{o}]")
        chains.append(f"[{cur}][o{o}]overlay=eof_action=pass:format=auto[y{o}]")
        cur = f"y{o}"

    inputs += ["-i", a.music]
    mi = _count(inputs)
    total = end / F
    chains.append(f"[{cur}]format=yuv420p[v]")
    chains.append(f"[{mi}:a]apad,atrim=0:{total:.4f},afade=t=out:st={max(0, min(total, music_len) - 0.4):.4f}:d=0.4[a]")
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-r", f"{F:g}", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.4f}", a.out]
    subprocess.run(cmd, check=True)
    print(json.dumps({"out": a.out, "template": t["id"], "fps": F, "length": round(duration(a.out), 3),
                      "cuts": [round(x / F, 3) for x in T[:-1]],
                      "transitions": [s["xf"] for s in segs[1:]], "shots": used}, indent=1, ensure_ascii=False))


def _count(inputs):
    """Index of the last input added (each input ends with '-i path')."""
    return sum(1 for x in inputs if x == "-i") - 1


if __name__ == "__main__":
    main()
