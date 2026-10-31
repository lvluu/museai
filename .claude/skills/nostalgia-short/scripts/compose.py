"""Compose a nostalgia short: the plan's shots in order, one EN + 中文 line per shot, warm film grade.

  uv run --no-project --python 3.12 --with pillow python scripts/compose.py plan.json WORK out.mp4 \
      [--music track.m4a] [--shot 2.3]

Clips come from WORK/clips/<id>.mp4, each from its "start" (default 1.0 s: muse's first second often
settles) for --shot seconds, hard cuts. The first line is the hook (bigger, upper middle); the others
sit at 70 % height, above the TikTok/Douyin/Reels caption and buttons. Grade (references/look of
american-everyday-stories): lifted blacks, warm mids, a little less saturation, moving film grain.
--music: the track under the clips' ambience (0.3), -14 LUFS. Without it: ambience only at -20 LUFS,
the export for adding a licensed song from the platform's in-app music library.
Encoded for upload (x264 tune grain, max 12 Mbit/s): the grain at crf 18 alone made a 30 s short 271 MB."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"
ZH = (
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb"
    ".asset/AssetData/PingFang.ttc"
)
W, H = 1080, 1920
GRADE = (
    "curves=all='0/0.06 0.5/0.52 1/0.96',colorbalance=rm=0.05:gm=0.01:bm=-0.06:rh=0.03:bh=-0.04,"
    "eq=saturation=0.88,noise=alls=7:allf=t"
)


def text_png(en, zh, hook, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fe = ImageFont.truetype(SERIF, 66 if hook else 54)
    fz = ImageFont.truetype(ZH, 52 if hook else 44, index=11)
    y = H * (0.38 if hook else 0.70)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds, dt = ImageDraw.Draw(shadow), ImageDraw.Draw(img)
    for f, t in ((fe, en), (fz, zh)):
        x = (W - f.getlength(t)) / 2
        ds.text((x + 2, y + 3), t, font=f, fill=(20, 12, 4, 200))
        dt.text((x, y), t, font=f, fill=(255, 246, 228, 255))
        y += f.size * 1.35
    Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)), img).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("work")
    ap.add_argument("out")
    ap.add_argument("--music")
    ap.add_argument("--shot", type=float, default=2.3)
    a = ap.parse_args()
    shots = json.loads(Path(a.plan).read_text())["shots"]
    clips = Path(a.work).expanduser() / "clips"
    n, d = len(shots), a.shot
    total = n * d
    tmp = Path(tempfile.mkdtemp())
    args, g = ["ffmpeg", "-v", "error", "-y"], []
    for s in shots:
        args += [
            "-ss",
            str(s.get("start", 1.0)),
            "-t",
            f"{d:.3f}",
            "-i",
            str(clips / f"{s['id']}.mp4"),
        ]
    for i, s in enumerate(shots):
        text_png(s["en"], s["zh"], i == 0, tmp / f"{i}.png")
        # a still PNG is one frame: loop it for the shot, or overlay=shortest cuts the shot to one frame
        args += ["-loop", "1", "-t", f"{d:.3f}", "-i", str(tmp / f"{i}.png")]
    if a.music:
        args += ["-i", a.music]
    for i in range(n):
        g.append(
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setsar=1,{GRADE},"
            f"trim=duration={d:.3f},setpts=PTS-STARTPTS[g{i}];"
            f"[{n + i}:v]format=rgba,fade=t=in:d=0.25:alpha=1[t{i}];[g{i}][t{i}]overlay=0:0:shortest=1[v{i}]"
        )
        g.append(
            f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,atrim=duration={d:.3f},asetpts=PTS-STARTPTS,"
            f"afade=in:d=0.06,afade=out:st={d - 0.06:.3f}:d=0.06[a{i}]"
        )
    g.append(
        "".join(f"[v{i}]" for i in range(n))
        + f"concat=n={n}:v=1:a=0,fade=t=out:st={total - 0.6:.3f}:d=0.6,format=yuv420p[vout]"
    )
    g.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[amb]")
    if a.music:
        g.append(
            f"[amb]volume=0.3[ambq];[{2 * n}:a]atrim=duration={total:.3f},afade=out:st={total - 1.5:.3f}:d=1.5[mus];"
            "[mus][ambq]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=7[aout]"
        )
    else:
        g.append("[amb]loudnorm=I=-20:TP=-2:LRA=9[aout]")
    args += [
        "-filter_complex",
        ";".join(g),
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-crf",
        "20",
        "-preset",
        "slow",
        "-tune",
        "grain",
        "-maxrate",
        "12M",
        "-bufsize",
        "24M",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        a.out,
    ]
    subprocess.run(args, check=True)
    frames = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v",
            "-count_packets",
            "-show_entries",
            "stream=nb_read_packets",
            "-of",
            "csv=p=0",
            a.out,
        ],
        capture_output=True,
        text=True,
    ).stdout
    mb = Path(a.out).stat().st_size / 1e6
    print(f"{a.out}: {n} shots x {d} s = {total:.1f} s, {frames.strip()} frames, {mb:.0f} MB")


if __name__ == "__main__":
    main()
