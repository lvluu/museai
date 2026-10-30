# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Cut the video from the plan's shots on the music's bars, with the hook text over the opening.

Usage:
  uv run --no-project scripts/compose.py plan.json [--music track.m4a] [--out <name>.mp4] [--at 3=1.2]

Per shot: skips muse's 0.5 s settle-in (--at N=S forces shot N's window start), keeps the planned
length, 1080x1920 at 24 fps. Joins: "cut" = hard cut on the downbeat, "dissolve" = 0.6 s dissolve
centred on it (a new location or time passing). A "cut" is a 0.2 s soft cut, not a single frame: two
moving shots joined frame to frame read as a jolt. The style's grade (styles.json "grade": lifted, light,
gentle contrast) goes over the whole video. The hook text (plan "hook_text", two lines: a small
line, then the big one) fades in at 0.15 s and out by 3.6 s, in the upper band clear of the subject
and of TikTok/Reels UI. Audio: the cut song on top, the clips' own location sound under it
(denoised, -15 dB) so breeze, water and footsteps blend in; -14 LUFS. The song already ends (real
outro or fade), so no extra fade except 0.3 s at the very end.
"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 24
XF = 0.6
CUT = 0.2
SETTLE = 0.5
FONT_BIG = ("/System/Library/Fonts/Supplemental/Didot.ttc", 2)
FONT_SMALL = ("/System/Library/Fonts/Supplemental/Didot.ttc", 1)
TEXT_IN, TEXT_OUT = 0.15, 3.6


def probe(path, entry):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entry, "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def font(spec, size):
    try:
        return ImageFont.truetype(spec[0], size, index=spec[1])
    except OSError:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", size)


def hook_png(text, path):
    """Two centred lines, white with a soft dark glow so they read on sky or water."""
    small, big = (text.split("\n", 1) + [""])[:2] if "\n" in text else ("", text)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fs, fb = font(FONT_SMALL, 64), font(FONT_BIG, 104)
    while d.textlength(big, font=fb) > W * 0.86 and fb.size > 60:
        fb = font(FONT_BIG, fb.size - 4)
    y = int(H * 0.17)
    rows = []
    if small:
        rows.append((small, fs, y))
        y += 92
    rows.append((big, fb, y))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    for s, f, yy in rows:
        x = (W - d.textlength(s, font=f)) / 2
        g.text((x, yy), s, font=f, fill=(0, 0, 0, 170))
        d.text((x, yy), s, font=f, fill=(255, 255, 255, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    Image.alpha_composite(glow, img).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--music")
    ap.add_argument("--out")
    ap.add_argument("--at", action="append", default=[], help="N=seconds: start of shot N's window")
    ap.add_argument("--no-text", action="store_true")
    a = ap.parse_args()
    plan_path = Path(a.plan).expanduser().resolve()
    work = plan_path.parent
    p = json.loads(plan_path.read_text())
    grade = json.loads((Path(__file__).resolve().parent.parent / "styles.json").read_text()).get("grade", "null")
    music = Path(a.music) if a.music else work / "track.m4a"
    out = Path(a.out) if a.out else work / f"{p['name']}.mp4"
    forced = {int(k): float(v) for k, v in (x.split("=") for x in a.at)}
    shots = p["shots"]
    total = p["seconds"]
    # each join overlaps both neighbours by half its length, centred on the bar
    joins = [XF if s["in"] == "dissolve" else CUT for s in shots[1:]]

    inputs, vf, af = [], [], []
    for i, s in enumerate(shots):
        clip = work / f"shot{s['n']}.mp4"
        pre = joins[i - 1] / 2 if i else 0
        post = joins[i] / 2 if i < len(joins) else 0
        keep = s["length"] + pre + post
        start = forced.get(s["n"], SETTLE)
        dur = float(probe(clip, "format=duration"))
        if start + keep > dur:
            start = max(0.0, dur - keep)
            print(f"shot{s['n']}: only {dur:.1f} s, window moved to {start:.2f} s")
        inputs += ["-ss", f"{start:.3f}", "-t", f"{keep:.3f}", "-i", str(clip)]
        vf.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
                  f"setsar=1,format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[v{i}]")
        has_audio = "audio" in probe(clip, "stream=codec_type")
        src = f"[{i}:a]" if has_audio else f"anullsrc=r=48000:cl=stereo,atrim=0:{keep:.3f},"
        af.append(f"{src}aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]")
        print(f"shot{s['n']:<2} {start:5.2f}-{start + keep:5.2f} s of {clip.name} -> {s['start']:6.2f}-{s['end']:6.2f}  {s['in']}")

    chain, achain = "[v0]", "[a0]"
    for i in range(1, len(shots)):
        d = joins[i - 1]
        off = shots[i]["start"] - d / 2
        vf.append(f"{chain}[v{i}]xfade=transition=fade:duration={d:.3f}:offset={off:.3f}[x{i}]")
        af.append(f"{achain}[a{i}]acrossfade=d={max(d, 0.05):.3f}[y{i}]")
        chain, achain = f"[x{i}]", f"[y{i}]"
    m = len(shots)
    inputs += ["-i", str(music)]
    if not a.no_text and p.get("hook_text"):
        png = Path(tempfile.mkdtemp()) / "hook.png"
        hook_png(p["hook_text"], png)
        inputs += ["-loop", "1", "-t", f"{TEXT_OUT:.2f}", "-i", str(png)]
        vf.append(f"[{m + 1}:v]format=rgba,fade=t=in:st={TEXT_IN}:d=0.5:alpha=1,"
                  f"fade=t=out:st={TEXT_OUT - 0.6:.2f}:d=0.6:alpha=1,setpts=PTS-STARTPTS[txt]")
        vf.append(f"{chain}[txt]overlay=0:0:eof_action=pass[vt]")
        chain = "[vt]"
    vf.append(f"{chain}trim=0:{total},setpts=PTS-STARTPTS,{grade},fade=t=out:st={total - 0.3:.2f}:d=0.3[vout]")
    af.append(f"{achain}afftdn=nr=40:nf=-40:tn=0,lowpass=f=9000,volume=-15dB,atrim=0:{total}[amb]")
    af.append(f"[{m}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total},asetpts=PTS-STARTPTS,"
              f"afade=t=out:st={total - 0.3:.2f}:d=0.3[mus]")
    af.append("[mus][amb]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(vf + af),
                    "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                    "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-t", f"{total:.3f}", str(out)], check=True)
    print(f"OUT {out} ({float(probe(out, 'format=duration')):.2f} s, {m} shots, "
          f"cuts at {[s['start'] for s in shots[1:]]})")


if __name__ == "__main__":
    main()
