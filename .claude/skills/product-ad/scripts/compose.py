"""Build a vertical product ad from an ad plan: beat-cut shots of the real product photos (and muse hero
clips), big text cards on the beat, the music bed, -14 LUFS, 1080x1920 30 fps.

Usage:
  uv run --no-project --python 3.12 --with pillow python scripts/compose.py ad.json out.mp4

ad.json (paths relative to the file):
  {"music": "track.m4a", "bpm": 100,           # bpm: from track.beats.json when present
   "hook_shots": 4,
   "shots": [{"src": "photos/4.jpg", "sec": 0.5, "mode": "crop|fit", "cx": 0.5, "zoom": [1.25, 1.0]},
             {"src": "hero/blue.mp4", "sec": 3, "ss": 0.3}],   # or "beats": n
   "texts": [{"shot": 0, "to": 4, "delay": 0, "text": "Line one\\nLINE TWO", "pos": "top|mid|low|<y px>",
              "style": "hook|pill|cta|tag"}]}       # or "beat"/"beats" instead of shot/to/delay
crop = 9:16 strip of the photo around cx (vertical products); fit = whole photo on a blurred copy of
itself (wide products). zoom = start/end scale over the shot (a 1.25 -> 1.0 punch on hook cuts).
A text runs from the start of shot `shot` (+ `delay` beats) to the end of shot `to` - 1, over several cuts.
shot `sec` snaps to whole beats of the real track; showcase shots (after hook_shots) last >= MIN_SHOW. Safe zone: nothing below
y=1500 or right of x=940 (TikTok / Reels / Shorts buttons and caption).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"  # covers Vietnamese diacritics
FACE = {"heavy": 0, "bold": 0, "demi": 2}  # Avenir Next Heavy (8) has no Vietnamese glyphs
STYLES = {  # font index, size, text colour, pill colour (None = outlined text, no pill)
    "hook": ("heavy", 96, (255, 255, 255), None),
    "pill": ("bold", 64, (255, 255, 255), (236, 72, 140)),
    "tag": ("demi", 52, (60, 40, 50), (255, 255, 255)),
    "cta": ("heavy", 78, (255, 255, 255), (236, 72, 140)),
}
MIN_SHOW = 0.85  # s a showcase shot stays on screen; hook cuts may be ~0.5 s
POS = {"top": 300, "mid": 860, "low": 1250}  # top edge of the text block


def font(face, size):
    try:
        return ImageFont.truetype(AVENIR, size, index=FACE[face])
    except OSError:
        return ImageFont.truetype(AVENIR, size, index=0)


def text_png(t, path):
    face, size, ink, pill = STYLES[t.get("style", "pill")]
    f = font(face, size)
    lines = t["text"].split("\n")
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pos = t.get("pos", "top")
    y = POS[pos] if isinstance(pos, str) else int(pos)
    gap = int(size * 0.32)
    for line in lines:
        x0, y0, x1, y1 = d.textbbox((0, 0), line, font=f)
        tw, th = x1 - x0, y1 - y0
        # keep clear of the right-hand button column: centre in 0..940
        x = (940 - tw) // 2 + 40 if tw < 860 else (W - tw) // 2
        if pill:
            px, py = int(size * 0.45), int(size * 0.28)
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).rounded_rectangle((x - px, y - py + 8, x + tw + px, y + th + py + 8),
                                                     radius=(th + 2 * py) // 2, fill=(0, 0, 0, 70))
            img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
            d.rounded_rectangle((x - px, y - py, x + tw + px, y + th + py), radius=(th + 2 * py) // 2, fill=pill)
            d.text((x - x0, y - y0), line, font=f, fill=ink)
        else:
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).text((x - x0, y - y0 + 6), line, font=f, fill=(0, 0, 0, 150))
            img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
            d.text((x - x0, y - y0), line, font=f, fill=ink, stroke_width=max(4, size // 14), stroke_fill=(214, 51, 122))
        y += th + gap + (2 * int(size * 0.28) if pill else 0)
    img.save(path)


def shot(s, base, dur, out):
    src = (base / s["src"]).resolve()
    n = round(dur * FPS)
    z0, z1 = s.get("zoom", [1.0, 1.08])
    # zoom eased over the shot: zoompan on an oversized frame so the motion stays smooth (no 1-px stepping)
    zexpr = f"{z0}+({z1}-{z0})*(1-cos(PI*on/{max(n - 1, 1)}))/2"
    zp = f"zoompan=z='{zexpr}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={W}x{H}:fps={FPS}"
    if src.suffix.lower() in (".mp4", ".mov"):
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
              f"scale={2 * W}:{2 * H},{zp.replace('d=1', 'd=1')}")
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(s.get("ss", 0)), "-i", str(src), "-t", f"{dur:.3f}",
               "-vf", vf, "-an", "-frames:v", str(n)]
    elif s.get("mode", "crop") == "crop":
        cx = s.get("cx", 0.5)
        vf = (f"crop=ih*9/16:ih:max(0\\,min(iw-ih*9/16\\,iw*{cx}-ih*9/32)):0,scale={2 * W}:{2 * H}:flags=lanczos,"
              f"{zp}")
        cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(src), "-vf", vf, "-frames:v", str(n)]
    else:  # fit: whole photo on a blurred, darkened copy of itself
        fc = (f"[0]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"gblur=sigma=40,eq=brightness=0.04:saturation=1.1[bg];[b]scale={W - 120}:-2:flags=lanczos[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2+100,scale={2 * W}:{2 * H},{zp}")
        cmd = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(src), "-filter_complex", fc, "-frames:v", str(n)]
    subprocess.run(cmd + ["-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "14", "-preset", "fast", str(out)], check=True)


def main():
    plan_path = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]).resolve()
    base = plan_path.parent
    plan = json.loads(plan_path.read_text())
    music = (base / plan["music"]).resolve()
    beats_file = music.with_suffix(".beats.json")
    bpm = plan.get("bpm") or json.loads(beats_file.read_text())["bpm"]
    beat = 60 / bpm
    tmp = Path(tempfile.mkdtemp(prefix="product-ad-"))
    # shots give "sec"; snap to whole beats of the real track (ACE picks its own tempo: asked 100, played 131,
    # and 1-beat shots flashed by in 0.46 s). Only the hook may cut faster than MIN_SHOW.
    hook = plan.get("hook_shots", 4)
    for i, s in enumerate(plan["shots"]):
        if "beats" not in s:
            s["beats"] = max(1, round(s["sec"] / beat))
        if i >= hook and s["beats"] * beat < MIN_SHOW:
            s["beats"] = int(-(-MIN_SHOW // beat))
            print(f"shot {i} lengthened to {s['beats']} beats ({s['beats'] * beat:.2f}s): showcase shots need >= {MIN_SHOW}s")
    starts = [0]
    for s in plan["shots"]:
        starts.append(starts[-1] + s["beats"])
    parts = []
    for i, s in enumerate(plan["shots"]):
        p = tmp / f"s{i:02d}.mp4"
        shot(s, base, s["beats"] * beat, p)
        parts.append(p)
    (tmp / "list.txt").write_text("".join(f"file '{p}'\n" for p in parts))
    body = tmp / "body.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
                    "-c", "copy", str(body)], check=True)
    total = sum(s["beats"] for s in plan["shots"]) * beat

    inputs, chains, last = ["-i", str(body), "-i", str(music)], [], "[0:v]"
    for k, t in enumerate(plan.get("texts", [])):
        png = tmp / f"t{k:02d}.png"
        text_png(t, png)
        if "shot" in t:  # from the start of shot `shot` (+ `delay` beats) to the end of shot `to` - 1
            b0 = starts[t["shot"]] + t.get("delay", 0)
            t["beat"], t["beats"] = b0, starts[t.get("to", t["shot"] + 1)] - b0
        st, d = t["beat"] * beat, t["beats"] * beat
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", str(png)]
        idx = k + 2
        # pop in: grows from 85 % with a fade over 0.15 s, fades out over the last 0.1 s
        chains.append(f"[{idx}:v]format=rgba,fade=in:st=0:d=0.15:alpha=1,fade=out:st={d - 0.1:.3f}:d=0.1:alpha=1,"
                      f"scale=w='{W}*min(1,0.85+t)':h=-1:eval=frame,setpts=PTS+{st:.3f}/TB[t{k}]")
        chains.append(f"{last}[t{k}]overlay=x=(W-w)/2:y=(H-h)/2:eof_action=pass:enable='between(t,{st:.3f},{st + d:.3f})'[v{k}]")
        last = f"[v{k}]"
    chains.append(f"[1:a]atrim=0:{total:.3f},afade=t=out:st={total - 0.25:.3f}:d=0.25,loudnorm=I=-14:TP=-1.5:LRA=9[a]")
    fc = ";".join(chains)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", last, "-map", "[a]",
                    "-t", f"{total:.3f}", "-r", str(FPS), "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
    print(f"{out} {total:.2f}s {len(parts)} shots @ {bpm:.1f} BPM")


if __name__ == "__main__":
    main()
