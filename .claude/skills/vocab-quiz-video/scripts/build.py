"""Build the finished quiz video from 6 scene clips + episode.json (made by fill_prompt.py).

Usage:
  uv run --no-project --python 3.12 --with edge-tts --with pillow \\
      python scripts/build.py <work_dir> <out.mp4>

<work_dir> holds episode.json and clip1.mp4 ... clip6.mp4. Text cards are drawn with Pillow and streamed
into ffmpeg as an RGBA overlay; voices come from edge-tts (answers in the language's tts_voice, hook and
end line in the English narrator voice); ticks and chime are synthesized here. Output: 1080x1920, 30 fps,
H.264 + AAC, 36 s, -14 LUFS, no music (added on TikTok).
"""

import array
import asyncio
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SR = 1080, 1920, 30, 48000
HOOK, SLOT, END = 1.5, 5.0, 4.5
TOTAL = HOOK + 6 * SLOT + END
GUESS, REVEAL, VOICE_AT = 2.0, 0.2, 2.3
END_LINE_AT = 2.1
NARRATOR = "en-US-AndrewNeural"
HOOK_LINE = "Can you get six out of six?"
END_LINE = "What was your score? Comment zero to six!"

# card in the upper third (the clip prompt keeps the object at 40-75 % height), x 130-950: clear of the
# right 12 % (platform buttons)
CARD_W, CARD_CY = 820, int(H * 0.30)
CARD_X = (W - CARD_W) // 2
PAD, RADIUS = 44, 36
WHITE, SHADOW, CARD_FILL = (255, 255, 255, 255), (0, 0, 0, 170), (12, 12, 16, 178)
GOLD = (255, 214, 92, 255)

work, out = Path(sys.argv[1]), Path(sys.argv[2])
ep = json.loads((work / "episode.json").read_text(encoding="utf-8"))
FONT_BOLD = ep.get("font_bold") or "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
FONT_REG = ep.get("font_regular") or "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
COLORS = ep.get("article_colors") or {}
WORDS = ep["words"]
LANG = ep["language"]
_fonts: dict = {}


def font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    key = (bold, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
    return _fonts[key]


def fit(text: str, bold: bool, size: int, width: int = CARD_W - 2 * PAD) -> ImageFont.FreeTypeFont:
    """Largest font up to `size` that keeps `text` on one line inside `width`."""
    while size > 24 and font(bold, size).getlength(text) > width:
        size -= 2
    return font(bold, size)


def runs(answer: str) -> list[tuple[str, tuple]]:
    """Answer split into colored runs: the article in its gender color, the noun in white."""
    first, _, rest = answer.partition(" ")
    color = COLORS.get(first.lower())
    if color and rest:
        rgb = tuple(int(color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)) + (255,)
        return [(first + " ", rgb), (rest, WHITE)]
    return [(answer, WHITE)]


# A line is a list of (runs, font, gap_after). A card draws its lines centered on one rounded box.
def line(text_or_runs, f, gap=14):
    r = [(text_or_runs, WHITE)] if isinstance(text_or_runs, str) else text_or_runs
    return (r, f, gap)


def line_size(ln):
    r, f, _ = ln
    asc, desc = f.getmetrics()
    return sum(f.getlength(t) for t, _ in r), asc + desc


def card(lines, cy=CARD_CY, w=CARD_W) -> Image.Image:
    """Full-frame RGBA layer with one dark rounded card holding `lines`, its center at height cy."""
    heights = [line_size(ln)[1] for ln in lines]
    inner = sum(heights) + sum(ln[2] for ln in lines[:-1])
    h = inner + 2 * PAD - 10
    x0, y0 = (W - w) // 2, cy - h // 2
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), RADIUS, fill=CARD_FILL)
    y = y0 + PAD - 6
    for ln, lh in zip(lines, heights, strict=True):
        lw = line_size(ln)[0]
        x = (W - lw) / 2
        r, f, gap = ln
        for text, color in r:
            d.text((x + 2, y + 3), text, font=f, fill=SHADOW)
            d.text((x, y), text, font=f, fill=color)
            x += f.getlength(text)
        y += lh + gap
    return img


def card_bottom(img: Image.Image) -> int:
    return img.getbbox()[3]


def pill(text: str, top: int, size: int = 46) -> Image.Image:
    f = font(True, size)
    tw = f.getlength(text)
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x0 = (W - tw) / 2 - 30
    d.rounded_rectangle((x0, top, x0 + tw + 60, top + asc + desc + 24), 30, fill=CARD_FILL)
    d.text(((W - tw) / 2, top + 10), text, font=f, fill=GOLD)
    return img


def progress(n: int) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(True, 56)
    text = f"{n}/6"
    d.rounded_rectangle(
        (48, int(H * 0.09), 48 + f.getlength(text) + 48, int(H * 0.09) + 92), 28, fill=CARD_FILL
    )
    d.text((72 + 2, int(H * 0.09) + 10 + 3), text, font=f, fill=SHADOW)
    d.text((72, int(H * 0.09) + 10), text, font=f, fill=WHITE)
    return img


def ring(base: Image.Image, top: int, u: float) -> Image.Image:
    """Countdown under the card: number 2 then 1, a white arc that empties during each second."""
    img = base.copy()
    d = ImageDraw.Draw(img)
    size, cx = 150, W // 2
    box = (cx - size // 2, top, cx + size // 2, top + size)
    d.ellipse(box, fill=CARD_FILL)
    d.ellipse(box, outline=(255, 255, 255, 70), width=10)
    left = 1 - (u % 1.0)
    d.arc(box, -90, -90 + 360 * left, fill=WHITE, width=10)
    f = font(True, 68)
    n = "2" if u < 1 else "1"
    d.text((cx, top + size / 2), n, font=f, fill=WHITE, anchor="mm")
    return img


def scaled(layer: Image.Image, p: float) -> Image.Image:
    """Reveal frame: `layer` faded to p and scaled from 92 % to 100 % around the card center."""
    s = 0.92 + 0.08 * p
    small = layer.resize((int(W * s), int(H * s)), Image.BICUBIC)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ox, oy = int(W / 2 - W * s / 2), int(CARD_CY - CARD_CY * s)
    out.paste(small, (ox, oy))
    alpha = out.getchannel("A").point(lambda a: int(a * p))
    out.putalpha(alpha)
    return out


# ---------- audio ----------


def tts(text: str, voice: str, rate: str, dest: Path) -> list[float]:
    mp3 = dest.with_suffix(".mp3")
    for attempt in range(5):  # the edge-tts service drops a request now and then (NoAudioReceived)
        try:
            asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(mp3)))
            break
        except edge_tts.exceptions.EdgeTTSException:
            if attempt == 4:
                raise
            time.sleep(2)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-ac", "1", "-ar", str(SR), str(dest)],
        check=True,
    )
    with wave.open(str(dest)) as w:
        a = array.array("h", w.readframes(w.getnframes()))
    s = [x / 32768 for x in a]
    # trim the silence edge-tts puts around every line
    thr = 0.02
    i = next((k for k, x in enumerate(s) if abs(x) > thr), 0)
    j = len(s) - next((k for k, x in enumerate(reversed(s)) if abs(x) > thr), 0)
    s = s[max(0, i - int(0.01 * SR)) : min(len(s), j + int(0.05 * SR))]
    rms = math.sqrt(sum(x * x for x in s) / len(s))
    return [x * 0.12 / rms for x in s]  # same loudness for every voice line


def tts_fit(text: str, voice: str, max_len: float, dest: Path, rate: int = 0) -> list[float]:
    """Speak `text`; if it is longer than max_len seconds, speak it faster (never cut it)."""
    for _ in range(6):
        s = tts(text, voice, f"{rate:+d}%", dest)
        if len(s) / SR <= max_len:
            return s
        rate += 10
    sys.exit(f"voice line too long even at {rate}%: {text}")


def tick() -> list[float]:
    n = int(0.05 * SR)
    return [
        0.35 * math.sin(2 * math.pi * 1600 * k / SR) * math.exp(-k / (0.008 * SR)) for k in range(n)
    ]


def chime() -> list[float]:
    n = int(0.6 * SR)
    return [
        0.09
        * (math.sin(2 * math.pi * 880 * k / SR) + 0.6 * math.sin(2 * math.pi * 1320 * k / SR))
        * math.exp(-k / (0.15 * SR))
        for k in range(n)
    ]


def mix_in(track: list[float], sound: list[float], at: float) -> None:
    o = int(at * SR)
    for k, x in enumerate(sound[: len(track) - o]):
        track[o + k] += x


def build_audio(tmp: Path) -> list[float]:
    """Mixed track; returns the end time of each answer voice (seconds into its slot)."""
    track = [0.0] * int(TOTAL * SR)
    mix_in(track, tts_fit(HOOK_LINE, NARRATOR, HOOK - 0.15, tmp / "hook.wav", rate=10), 0.1)
    voice_end = []
    for i, w in enumerate(WORDS):
        t0 = HOOK + i * SLOT
        mix_in(track, tick(), t0)
        mix_in(track, tick(), t0 + 1.0)
        mix_in(track, chime(), t0 + GUESS)
        s = tts_fit(
            w["answer"], ep["tts_voice"], SLOT - VOICE_AT - 0.6, tmp / f"w{i}.wav", rate=-10
        )
        mix_in(track, s, t0 + VOICE_AT)
        voice_end.append(VOICE_AT + len(s) / SR)
    end0 = HOOK + 6 * SLOT
    mix_in(
        track,
        tts_fit(END_LINE, NARRATOR, END - END_LINE_AT - 0.1, tmp / "end.wav", rate=5),
        end0 + END_LINE_AT,
    )
    peak = max(abs(x) for x in track)
    if peak > 0.98:
        track = [x * 0.98 / peak for x in track]
    with wave.open(str(tmp / "mix.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(array.array("h", (int(x * 32767) for x in track)).tobytes())
    # loudnorm lands ~2 LU low on this sparse track and the limiter eats part of a plain gain,
    # so apply gain + limiter, measure again, repeat until within 0.5 LU of -14 LUFS
    src, gain = tmp / "mix.wav", 0.0
    for _ in range(4):
        if gain:
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(src),
                    "-af",
                    f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false",
                    "-ar",
                    str(SR),
                    str(tmp / "mix14.wav"),
                ],
                check=True,
            )
            src = tmp / "mix14.wav.tmp.wav"
            (tmp / "mix14.wav").replace(src)
        r = subprocess.run(
            ["ffmpeg", "-nostats", "-i", str(src), "-af", "ebur128", "-f", "null", "-"],
            capture_output=True,
            text=True,
        )
        gain = -14 - float(r.stderr.rsplit("I:", 1)[1].split("LUFS")[0])
        if abs(gain) < 0.5:
            break
    src.replace(tmp / "mix14.wav")
    return voice_end


# ---------- overlay frames ----------


def layers(voice_end: list[float]):
    hook = card(
        [
            line(ep["topic"], font(True, 44), 6),
            line(f"{LANG} {ep['level']}:", fit(f"{LANG} {ep['level']}:", True, 92), 4),
            line("Can you get 6/6?", fit("Can you get 6/6?", True, 92)),
        ]
    )
    words = []
    for w in WORDS:
        q = card([line(w["english"], fit(w["english"], True, 96))])
        a = card(
            [
                line(runs(w["answer"]), fit(w["answer"], True, 100), 12),
                line(w["pron"], fit(w["pron"], False, 60)),
            ]
        )
        words.append((q, card_bottom(q) + 36, a, pill("Listen & repeat", card_bottom(a) + 28)))
    recap = card(
        [line(runs(w["answer"]), fit(w["answer"], True, 64), 10) for w in WORDS], cy=int(H * 0.42)
    )
    nxt = f"Next: {LANG} {ep['next_level']} {ep['next_topic']}"
    score = card(
        [
            line("What was your score?", fit("What was your score?", True, 76), 4),
            line("0–6", font(True, 140), 4),
            line("Comment below", font(True, 54), 22),
            line(nxt, fit(nxt, False, 44), 0),
        ]
    )
    prog = [progress(n) for n in range(1, 7)]
    empty = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cache: dict = {}

    def stack(*imgs):
        key = tuple(id(i) for i in imgs)
        if key not in cache:
            base = empty.copy()
            for i in imgs:
                base.alpha_composite(i)
            cache[key] = base
        return cache[key]

    def frame(t: float) -> Image.Image:
        if t < HOOK:
            return hook
        if t >= HOOK + 6 * SLOT:
            return recap if t - HOOK - 6 * SLOT < 2.0 else score
        i = min(5, int((t - HOOK) // SLOT))
        u = t - HOOK - i * SLOT
        q, ring_top, a, listen = words[i]
        if u < GUESS:
            return ring(stack(prog[i], q), ring_top, u)
        if u < GUESS + REVEAL:
            img = prog[i].copy()
            img.alpha_composite(scaled(a, (u - GUESS) / REVEAL))
            return img
        return stack(prog[i], a, listen) if u >= voice_end[i] + 0.1 else stack(prog[i], a)

    return frame


# ---------- video ----------


def duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(r.stdout)


def main() -> None:
    clips = [work / f"clip{i}.mp4" for i in range(1, 7)]
    missing = [c.name for c in clips if not c.exists()]
    if missing:
        sys.exit(f"missing clips in {work}: {', '.join(missing)}")
    # (clip, start, length): hook and word 1 share clip 1 so the opening keeps moving; the end replays clip 1
    w1_start = HOOK if duration(clips[0]) >= HOOK + SLOT else 0
    segs = (
        [(clips[0], 0, HOOK), (clips[0], w1_start, SLOT)]
        + [(c, 0, SLOT) for c in clips[1:]]
        + [(clips[0], 0, END)]
    )

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        voice_end = build_audio(tmp)
        frame = layers(voice_end)
        cmd = ["ffmpeg", "-v", "error", "-y"]
        for c, _, _ in segs:
            cmd += ["-i", str(c)]
        n = len(segs)
        cmd += [
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgba",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "pipe:0",
            "-i",
            str(tmp / "mix14.wav"),
        ]
        parts = []
        for k, (_, start, length) in enumerate(segs):
            parts.append(
                f"[{k}:v]trim=start={start},setpts=PTS-STARTPTS,fps={FPS},"
                f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
                f"tpad=stop_mode=clone:stop_duration={SLOT},trim=duration={length},setpts=PTS-STARTPTS[v{k}]"
            )
        parts.append("".join(f"[v{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=0[bg]")
        parts.append(f"[bg][{n}:v]overlay=format=auto,format=yuv420p[v]")
        cmd += [
            "-filter_complex",
            ";".join(parts),
            "-map",
            "[v]",
            "-map",
            f"{n + 1}:a",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            str(SR),
            "-movflags",
            "+faststart",
            "-t",
            f"{TOTAL}",
            str(out),
        ]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for f in range(int(TOTAL * FPS)):
                p.stdin.write(frame(f / FPS).tobytes())
        except BrokenPipeError:
            pass
        p.stdin.close()
        if p.wait():
            sys.exit("ffmpeg failed")
    print(f"SAVED {out} ({duration(out):.1f}s)")
    if os.environ.get("SHEET"):
        sheet = out.with_suffix(".sheet.png")
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(out),
                "-vf",
                "fps=1,scale=270:-1,tile=8x5",
                "-frames:v",
                "1",
                str(sheet),
            ],
            check=True,
        )
        print(f"SHEET {sheet}")


if __name__ == "__main__":
    main()
