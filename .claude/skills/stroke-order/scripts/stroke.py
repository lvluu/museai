"""Usage: stroke.py words/<slug>.json out.mp4 [work_dir]
Run: uv run --no-project --python 3.12 --with pillow --with numpy --with soundfile --with edge-tts python scripts/stroke.py ...

One ~25 s vertical (9:16, 1080x1920) "Cách viết từ <hanzi>" Short, no muse clips: the hanzi + meaning on frame 0,
then every stroke drawn in order (current stroke in the accent colour, a tick per stroke), a slow + natural
Mandarin read, the Vietnamese meaning, an example sentence, a CTA to the full lesson; the last frame fades into
the first so it loops. Stroke data: hanzi-writer-data (Make Me a Hanzi), downloaded once per character from
cdn.jsdelivr.net and cached in scripts/.cache/hanzi/. Voices: edge-tts (zh-CN-XiaoxiaoNeural, vi-VN-HoaiMyNeural).
Safe zones: nothing above y 200, below y 1480, right of x 960 between y 900-1480.
"""

import asyncio
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageChops, ImageDraw, ImageFont

W, H, FPS, SR = 1080, 1920, 30, 48000
STROKE, DRAW = 0.55, 0.42  # seconds per stroke, of which drawing
HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache"
DATA = "https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/{}.json"
PINGFANG = (
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb"
    ".asset/AssetData/PingFang.ttc"
)
CJK = PINGFANG if Path(PINGFANG).exists() else "/System/Library/Fonts/Hiragino Sans GB.ttc"
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"
BG, PANEL, WHITE, ACCENT, GREEN = (
    (16, 16, 22),
    (32, 32, 44),
    (255, 255, 255),
    (255, 176, 46),
    (38, 196, 110),
)
TONES = {
    1: (255, 86, 86),
    2: (255, 170, 50),
    3: (80, 210, 120),
    4: (90, 160, 255),
    0: (200, 200, 210),
}
VOICES = {"zh": "zh-CN-XiaoxiaoNeural", "vi": "vi-VN-HoaiMyNeural"}


def font(face, size):
    if face == "zh":
        return ImageFont.truetype(CJK, size, index=11 if CJK == PINGFANG else 0)
    return ImageFont.truetype(AVENIR, size, index={"bold": 0, "demi": 2, "medium": 5}[face])


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


# ---------- stroke data ----------
def load_char(ch):
    f = CACHE / "hanzi" / f"{ch}.json"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        url = DATA.format(urllib.parse.quote(ch))
        f.write_bytes(urllib.request.urlopen(url, timeout=30).read())
    return json.loads(f.read_text())


def flatten(path):
    """Absolute M/L/Q/C/Z path of hanzi-writer-data -> polygon points (1024 space, y up)."""
    t = re.findall(r"[MLQCZ]|-?\d+\.?\d*", path)
    pts, i, cur = [], 0, (0.0, 0.0)
    while i < len(t):
        c = t[i]
        i += 1
        if c in "ML":
            cur = (float(t[i]), float(t[i + 1]))
            i += 2
            pts.append(cur)
        elif c == "Q":
            p1, p2 = (float(t[i]), float(t[i + 1])), (float(t[i + 2]), float(t[i + 3]))
            i += 4
            for k in range(1, 9):
                u = k / 8
                pts.append(
                    (
                        (1 - u) ** 2 * cur[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
                        (1 - u) ** 2 * cur[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1],
                    )
                )
            cur = p2
        elif c == "C":
            p1, p2, p3 = [(float(t[i + j]), float(t[i + j + 1])) for j in (0, 2, 4)]
            i += 6
            for k in range(1, 9):
                u = k / 8
                pts.append(
                    tuple(
                        (1 - u) ** 3 * cur[d]
                        + 3 * (1 - u) ** 2 * u * p1[d]
                        + 3 * (1 - u) * u * u * p2[d]
                        + u**3 * p3[d]
                        for d in (0, 1)
                    )
                )
            cur = p3
    return pts


class Glyph:
    """One character at box size S: a filled mask per stroke and its median polyline (screen space)."""

    def __init__(self, ch, S):
        d, k = load_char(ch), S / 1024
        self.S = S
        self.masks, self.medians = [], []
        for s, m in zip(d["strokes"], d["medians"], strict=False):
            big = Image.new("L", (S * 2, S * 2), 0)
            ImageDraw.Draw(big).polygon(
                [(x * k * 2, (900 - y) * k * 2) for x, y in flatten(s)], fill=255
            )
            self.masks.append(big.resize((S, S), Image.LANCZOS))
            self.medians.append([(x * k, (900 - y) * k) for x, y in m])
        self.n = len(self.masks)

    def reveal(self, i, p):
        """Mask of stroke i drawn up to fraction p along its median."""
        pts = self.medians[i]
        seg = [
            float(np.hypot(b[0] - a[0], b[1] - a[1])) for a, b in zip(pts, pts[1:], strict=False)
        ]
        goal, upto, run = p * sum(seg), [pts[0]], 0.0
        for (a, b), L in zip(zip(pts, pts[1:], strict=False), seg, strict=False):
            if run + L >= goal:
                f = (goal - run) / L if L else 1
                upto.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
                break
            upto.append(b)
            run += L
        r = Image.new("L", (self.S, self.S), 0)
        d, w = ImageDraw.Draw(r), int(self.S * 0.13)
        d.line(upto, fill=255, width=w, joint="curve")
        for x, y in upto:
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=255)
        return ImageChops.multiply(self.masks[i], r)


# ---------- voice ----------
async def say(text, voice, rate, dst):
    import edge_tts

    key = hashlib.sha1(f"{text}|{voice}|{rate}".encode()).hexdigest()[:12]
    mp3 = CACHE / "voice" / f"{key}.mp3"
    mp3.parent.mkdir(parents=True, exist_ok=True)
    if not mp3.exists():
        await edge_tts.Communicate(text.replace("!", "."), voice, rate=f"{rate:+d}%").save(str(mp3))
    trim = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse"
    await asyncio.to_thread(
        subprocess.run,
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(mp3),
            "-af",
            trim,
            "-ar",
            str(SR),
            "-ac",
            "1",
            str(dst),
        ],
        check=True,
    )
    data, _ = sf.read(dst)
    return data.astype(np.float32)


def tick(n=0.05):
    t = np.arange(int(SR * n)) / SR
    return (np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 70) * 0.35).astype(np.float32)


def chime():
    t = np.arange(int(SR * 0.5)) / SR
    return (
        (np.sin(2 * np.pi * 880 * t) + np.sin(2 * np.pi * 1320 * t)) * np.exp(-t * 6) * 0.22
    ).astype(np.float32)


# ---------- drawing ----------
def centered(d, text, y, f, fill, W_=W):
    w = d.textlength(text, font=f)
    d.text(((W_ - w) / 2, y), text, font=f, fill=fill)


def pinyin_row(d, syl, tones, y, size):
    f = font("demi", size)
    gap = size * 0.4
    total = sum(d.textlength(s, font=f) for s in syl) + gap * (len(syl) - 1)
    x = (W - total) / 2
    for s, t in zip(syl, tones, strict=False):
        d.text((x, y), s, font=f, fill=TONES[t])
        x += d.textlength(s, font=f) + gap


def hook_frame(w, flash=0.0):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    centered(d, "Cách viết từ", 250, font("demi", 56), (200, 200, 210))
    word = w["word"]
    size = 360 if len(word) <= 2 else 260
    centered(d, word, 440, font("zh", size), WHITE)
    pinyin_row(d, w["pinyin"], w["tones"], 440 + size + 60, 96)
    centered(d, w["vi"], 440 + size + 200, font("bold", 84), ACCENT)
    if flash:
        img = Image.blend(img, Image.new("RGB", (W, H), WHITE), flash)
    return img


def main():
    spec, out = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2])
    work = Path(sys.argv[3]) if len(sys.argv) > 3 else HERE.parent / "work" / out.stem
    work.mkdir(parents=True, exist_ok=True)
    word, n = spec["word"], len(spec["word"])
    S = min(480, (W - 120 - 40 * (n - 1)) // n)
    glyphs = [Glyph(c, S) for c in word]
    ex = spec.get("example")

    # voice
    v = {}

    async def voices():
        v["hook"] = await say(word, VOICES["zh"], 0, work / "hook.wav")
        v["slow"] = await say(word, VOICES["zh"], -20, work / "slow.wav")
        v["mean"] = await say(f"Nghĩa là: {spec['vi']}", VOICES["vi"], 0, work / "mean.wav")
        if ex:
            v["ex"] = await say(ex["zh"], VOICES["zh"], 0, work / "ex.wav")

    asyncio.run(voices())

    def dur(k):
        return len(v[k]) / SR

    # timeline
    t_hook = max(2.2, 0.25 + dur("hook") + 0.6)
    t_write = t_hook + 0.3
    sched, t = [], t_write  # (char, stroke, start)
    for ci, g in enumerate(glyphs):
        for si in range(g.n):
            sched.append((ci, si, t))
            t += STROKE
    t_rev = t + 0.4
    t_mean = t_rev + dur("slow") + 0.35
    t_ex = t_mean + dur("mean") + 0.35
    t_end_voice = t_ex + (dur("ex") if ex else 0)
    t_outro = t_end_voice + 0.9
    total = t_outro + 2.0

    # audio
    mix = np.zeros(int(total * SR) + SR, dtype=np.float32)

    def put(a, at):
        i = int(at * SR)
        mix[i : i + len(a)] += a

    put(v["hook"], 0.25)
    for _, _, s in sched:
        put(tick(), s)
    put(chime(), t - 0.05)
    put(v["slow"], t_rev)
    put(v["mean"], t_mean)
    if ex:
        put(v["ex"], t_ex)
    mix = np.clip(mix[: int(total * SR)], -1, 1)
    sf.write(work / "mix.wav", mix, SR)

    hook0 = hook_frame(spec)
    cy = 380
    xs = [(W - (n * S + 40 * (n - 1))) // 2 + i * (S + 40) for i in range(n)]

    def box(img, d, g, x, done, active):
        d.rounded_rectangle([x - 14, cy - 14, x + S + 14, cy + S + 14], 28, fill=PANEL)
        for k in (0.5,):  # 田字格 guide lines
            d.line([(x, cy + S * k), (x + S, cy + S * k)], fill=(70, 70, 88), width=2)
            d.line([(x + S * k, cy), (x + S * k, cy + S)], fill=(70, 70, 88), width=2)
        faint = Image.new("L", (S, S), 0)
        for m in g.masks:
            faint = ImageChops.lighter(faint, m)
        img.paste(Image.new("RGB", (S, S), (62, 62, 80)), (x, cy), faint)
        for i in done:
            img.paste(Image.new("RGB", (S, S), WHITE), (x, cy), g.masks[i])
        if active:
            i, p = active
            img.paste(Image.new("RGB", (S, S), ACCENT), (x, cy), g.reveal(i, ease(p)))

    def frame(t):
        if t < t_hook:
            return hook_frame(spec, flash=max(0.0, 0.5 - t * 4))
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        writing = t < t_rev
        centered(d, "Cách viết từ", 250, font("demi", 56), (200, 200, 210))
        cur = next((s for s in sched if s[2] <= t < s[2] + STROKE), None)
        for ci, g in enumerate(glyphs):
            done = [si for c, si, s in sched if c == ci and s + DRAW <= t]
            act = None
            if cur and cur[0] == ci and t - cur[2] < DRAW:
                act = (cur[1], (t - cur[2]) / DRAW)
            box(img, d, g, xs[ci], done, act)
        if writing:
            idx = sum(1 for c, si, s in sched if s <= t)
            lab = f"Nét {idx}/{len(sched)}"
            centered(d, lab, cy + S + 50, font("bold", 64), ACCENT)
        else:
            pinyin_row(d, spec["pinyin"], spec["tones"], cy + S + 50, 88)
            centered(d, spec["vi"], cy + S + 160, font("bold", 76), ACCENT)
            if ex and t >= t_ex:
                a = ease((t - t_ex) / 0.3)
                card = Image.new("RGB", (W - 160, 250), PANEL)
                cd = ImageDraw.Draw(card)
                centered(cd, ex["zh"], 14, font("zh", 78), WHITE, W - 160)
                centered(cd, ex["py"], 118, font("medium", 44), (200, 200, 210), W - 160)
                centered(cd, ex["vi"], 178, font("demi", 48), GREEN, W - 160)
                img.paste(Image.blend(Image.new("RGB", card.size, BG), card, a), (80, cy + S + 300))
        if t >= t_outro:
            a = ease((t - t_outro) / 0.3)
            ov = Image.new("RGB", (W, H), BG)
            od = ImageDraw.Draw(ov)
            centered(
                od,
                spec.get("cta", "Học trọn bộ ở video dài trên kênh"),
                780,
                font("bold", 62),
                WHITE,
            )
            centered(od, "Xem bình luận ghim", 880, font("demi", 48), ACCENT)
            img = Image.blend(img, ov, a * 0.92)
            lt = t - (total - 0.35)
            if lt > 0:
                img = Image.blend(img, hook0, min(1.0, lt / 0.35))
        return img

    ff = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-i",
            str(work / "mix.wav"),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-af",
            "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-shortest",
            str(out),
        ],
        stdin=subprocess.PIPE,
    )
    for k in range(int(total * FPS)):
        ff.stdin.write(frame(k / FPS).tobytes())
    ff.stdin.close()
    if ff.wait():
        sys.exit("ffmpeg failed")
    print(f"{out} {total:.1f}s {len(sched)} strokes")


if __name__ == "__main__":
    main()
