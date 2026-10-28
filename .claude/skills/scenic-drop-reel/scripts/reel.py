# /// script
# dependencies = ["pillow", "fonttools"]
# ///
"""Assemble a scenic drop reel: black countdown card, then drone shots hard-cut on the beat.

Usage:
  uv run --no-project --python 3.12 --with pillow --with fonttools python scripts/reel.py \
      --title SWITZERLAND --flag 🇨🇭 --out reel.mp4 shot1.mp4 shot2.mp4@2.4 ...

Layout copied from the reference reel (100 BPM; default music assets/music-default.m4a from music.py):
  0.000-3.233 s  black card, "TITLE <flag>" with a countdown 3 (0-1 s), 2 (1-2 s), 1 (2 s-drop)
  3.233 s        beat drop: hard cut to shot 1
  every 1.2 s    (2 beats) hard cut to the next shot, no fades, no zooms between shots
Each shot's 1.2 s window is picked automatically (@auto, default): the stretch whose motion is
slowest and most even, because that is what makes the reference's hard cuts feel smooth; @start
(seconds) overrides it. With the default track 7 shots fill it; extra clips are dropped with a warning.
"""
import argparse
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from fontTools.ttLib import TTCollection
from PIL import Image, ImageDraw, ImageFont

SKILL = Path(__file__).resolve().parent.parent
TITLE_FONT = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def emoji(text):
    # Flags are ligatures of two regional indicators; Pillow without raqm can't shape them, so take
    # the glyph's 160 px PNG straight from Apple Color Emoji's sbix table (named u1F1E8_u1F1ED etc.)
    font = TTCollection(EMOJI_FONT, lazy=True).fonts[0]
    name = "_".join(f"u{ord(c):04X}" for c in text if ord(c) != 0xFE0F)
    glyph = font["sbix"].strikes[160].glyphs.get(name)
    if glyph is None or glyph.graphicType != "png ":
        sys.exit(f"no emoji bitmap for {text!r} ({name})")
    img = Image.open(io.BytesIO(glyph.imageData)).convert("RGBA")
    return img.crop(img.getbbox())


def fps(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout.strip()
    num, _, den = out.partition("/")
    return float(num) / float(den or 1)


def card(title, flag, number, w, h, path):
    img = Image.new("RGB", (w, h), "black")
    d = ImageDraw.Draw(img)
    size = round(w * 0.068)
    font = ImageFont.truetype(TITLE_FONT, size)
    tw = d.textlength(title, font=font)
    fw = gap = 0
    if flag:
        em = emoji(flag)
        eh = round(size * 0.8)
        em = em.resize((round(em.width * eh / em.height), eh), Image.LANCZOS)
        fw, gap = em.width, round(size * 0.2)
    y = round(h * 0.28)
    x = round((w - tw - gap - fw) / 2)
    d.text((x, y), title, font=font, fill="white", anchor="ls")
    if flag:
        img.paste(em, (x + round(tw) + gap, y - em.height), em)
    d.text((w / 2, y + round(size * 1.15)), str(number), font=font, fill="white", anchor="ms")
    img.save(path)


def ydif(path, w=270):
    """Per-frame mean |luma change| (ffmpeg signalstats YDIF) on a small copy: how fast the picture moves."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf",
                          f"scale={w}:-2,signalstats,metadata=print:key=lavfi.signalstats.YDIF:file=-",
                          "-an", "-f", "null", "-"], capture_output=True, text=True, check=True).stdout
    return [float(line.split("=")[1]) for line in out.splitlines() if "YDIF=" in line]


def pick_window(d, n, src_fps, target):
    """Start frame of the n-frame window that moves steadily at about `target` YDIF per frame.

    Reference shots move slowly and evenly (YDIF 3-9 per frame at 30 fps, flat inside a shot); a
    window with a jump (> 3x its median) or a surge reads as a jolt, so it scores out."""
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
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+", help="shot.mp4, shot.mp4@start_seconds or shot.mp4@auto, in order")
    ap.add_argument("--title", required=True, help="place name shown on the countdown, e.g. SWITZERLAND")
    ap.add_argument("--flag", default="", help="emoji after the title, e.g. 🇨🇭")
    ap.add_argument("--out", required=True)
    ap.add_argument("--music", default=str(SKILL / "assets/music-default.m4a"),
                    help="track with its drop at --intro; make one with scripts/music.py")
    ap.add_argument("--intro", type=float, default=3.233, help="countdown length = time of the beat drop")
    ap.add_argument("--shot", type=float, default=1.2, help="seconds per shot (2 beats at 100 BPM)")
    ap.add_argument("--fps", type=float, default=None,
                    help="output fps; default the first clip's (24 for muse), so every source frame is shown once. "
                         "24 -> 30 by duplication judders, 1.25x speed-up makes the drone rush")
    ap.add_argument("--speed", type=float, default=1.0, help="playback speed of the shots")
    ap.add_argument("--target", type=float, default=7.0,
                    help="auto window: wanted motion, YDIF per output frame (reference 3-9)")
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--grade", type=float, default=1.0, help="0 = no grade; 1 = reference punchy grade")
    a = ap.parse_args()
    w, h = map(int, a.size.split("x"))

    music_len = duration(a.music)
    slots = max(1, int((music_len + 0.7 - a.intro) // a.shot))  # last shot may outrun the track's tail
    clips = a.clips
    if len(clips) > slots:
        print(f"warning: track fits {slots} shots, dropping {clips[slots:]}", file=sys.stderr)
        clips = clips[:slots]
    F = a.fps or fps(clips[0].partition("@")[0])
    # every boundary on an absolute frame grid, so cuts stay on the beat without drift
    times = [0.0, 1.0, 2.0] + [a.intro + k * a.shot for k in range(len(clips) + 1)]
    bounds = [round(t * F) for t in times]
    frames = [b - a_ for a_, b in zip(bounds, bounds[1:], strict=False)]
    total = bounds[-1] / F

    tmp = Path(tempfile.mkdtemp(prefix="reel-"))
    inputs, chains = [], []
    for i, n in enumerate((3, 2, 1)):
        png = tmp / f"card{n}.png"
        card(a.title, a.flag, n, w, h, png)
        inputs += ["-loop", "1", "-framerate", f"{F:g}", "-i", str(png)]
        chains.append(f"[{i}:v]trim=end_frame={frames[i]},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[v{i}]")

    sat, con = 1 + 0.22 * a.grade, 1 + 0.06 * a.grade
    used = []
    for k, spec in enumerate(clips):
        path, _, start = spec.partition("@")
        n_out = frames[3 + k]
        src_fps = fps(path)
        n_src = round(n_out * a.speed * src_fps / F)
        info = {"clip": path}
        if start in ("", "auto"):
            d = ydif(path)
            score, j, mean, std = pick_window(d, n_src, src_fps, a.target * a.speed ** -1 * F / src_fps)
            s = j / src_fps
            info.update(motion=round(mean, 1), steady=round(std, 1))
            if mean > 1.6 * a.target:
                print(f"warning: {path} moves fast even at its calmest (YDIF {mean:.1f} > {1.6 * a.target:.1f}/frame):"
                      " re-render slower or lower --speed", file=sys.stderr)
        else:
            s = float(start)
        dur = duration(path)
        s = max(0.0, min(s, dur - n_src / src_fps - 0.02))
        info.update(start=round(s, 2), clip_len=round(dur, 2))
        used.append(info)
        idx = 3 + k
        inputs += ["-ss", f"{s:.3f}", "-i", path]
        grade = f",eq=saturation={sat:.2f}:contrast={con:.2f},unsharp=5:5:0.6" if a.grade else ""
        chains.append(f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
                      f"setpts=(PTS-STARTPTS)/{a.speed:.4f},fps={F:g},trim=end_frame={n_out},setpts=PTS-STARTPTS"
                      f"{grade},format=yuv420p,setsar=1[v{idx}]")
    n = 3 + len(clips)
    chains.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]")
    inputs += ["-i", a.music]
    fade = max(0.0, min(total, music_len) - 0.25)
    chains.append(f"[{n}:a]apad,atrim=0:{total:.3f},afade=t=out:st={fade:.3f}:d=0.25[a]")

    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chains),
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-r", f"{F:g}",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}",
           a.out]
    subprocess.run(cmd, check=True)
    print(json.dumps({"out": a.out, "fps": F, "length": round(duration(a.out), 3),
                      "cuts": [round(b / F, 3) for b in bounds[3:-1]], "shots": used}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
