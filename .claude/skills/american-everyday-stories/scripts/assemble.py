#!/usr/bin/env python3
"""Cut the rendered shots into one graded film, check its lip sync, then lay the music bed under it.

  python3 scripts/assemble.py cut WORK episode.json film.mp4   # clips/<prefix>-<ID>.mp4 -> graded film + cut.json
  uv run --no-project --python 3.12 --with numpy python scripts/assemble.py sync WORK film.mp4   # A/V gate
  python3 scripts/assemble.py mix film.mp4 music.m4a out.mp4   # music bed ducked under speech

cut: each shot is trimmed to WORK/trims.json {"S03": [start, end]} (audit.py writes it: a dialogue
     shot runs to its last word + 0.7 s; default: its first `seconds`), scaled to 1920x1080, cut to a
     WHOLE number of frames at 24 fps, graded toward the reference look (each shot's measured luma
     range and colour pulled toward references/look.md at STRENGTH, default 0.85, so shots match each
     other) and joined with XF-second dissolves (default 0.4, XF=0 for hard cuts).
     Lip sync: every shot's sound is placed at the exact film time of its picture (adelay + amix),
     never chained. Chained acrossfade/concat lose ~50 ms per join, so by mid-film the voice runs
     0.5 s+ ahead of the lips. cut.json records each shot's film start and trim start for align.py.
sync: decodes the film and every clip whole (no -ss seeking: it shifts audio by itself) and finds
     where each shot's picture (frame-normalised luma) and sound (8 kHz sample correlation) actually
     sit. Lips = sound - picture; more than 40 ms (one frame) on any shot is FAIL. Run it after every
     cut and before mix/finish; deliver nothing on FAIL.
mix: the music is looped/trimmed to the film, faded in 1.5 s / out 3 s, sits at MUSIC_DB
     (default -20 dB under dialogue) and ducks a further ~10 dB while anyone speaks
     (sidechaincompress keyed on the dialogue). Loudness -16 LUFS, stereo 48 kHz."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

FPS, SR = 24, 48000
# The reference film measured with signalstats at 1 fps (references/look.md): lifted blacks, soft
# whites, warm yellow-red mean, moderate saturation.
REF = dict(lo=66, hi=165, u=118.6, v=142.6, sat=22.0)


def run(args):
    subprocess.run(args, check=True)


def probe_dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(path)], capture_output=True, text=True, check=True).stdout)


def has_audio(path):
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip())


def stats(src, a, b):
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a}", "-t", f"{b - a}", "-i", str(src), "-vf",
                          "fps=2,scale=320:-1,signalstats,metadata=print:file=-", "-f", "null", "-"],
                         capture_output=True, text=True, check=True).stdout
    def g(k):
        return sum(map(float, re.findall(rf"{k}=([\d.]+)", out))) / len(re.findall(rf"{k}=", out))

    return dict(lo=g("YLOW"), hi=g("YHIGH"), u=g("UAVG"), v=g("VAVG"), sat=g("SATAVG"))


def grade(s, k):
    """Pull one shot's luma range, colour mean and saturation toward REF by k (0 = untouched)."""
    lo = s["lo"] + k * (REF["lo"] - s["lo"])
    hi = s["hi"] + k * (REF["hi"] - s["hi"])
    ga = (hi - lo) / max(s["hi"] - s["lo"], 1)
    gb = lo - ga * s["lo"]
    sat = 1 + k * (min(REF["sat"] / max(s["sat"], 1), 1.6) - 1)
    du, dv = k * (REF["u"] - s["u"]), k * (REF["v"] - s["v"])
    return (f"lutyuv=y='clip({ga:.4f}*val+{gb:.2f},16,235)'"
            f":u='clip(128+{sat:.3f}*(val-128)+{du:.2f},16,240)'"
            f":v='clip(128+{sat:.3f}*(val-128)+{dv:.2f},16,240)',eq=gamma=1.04")


def cut(work, ep_path, out):
    work, ep = Path(work), json.loads(Path(ep_path).read_text())
    tag = f"aes-ep{ep['episode']:02}"
    trims = json.loads((work / "trims.json").read_text()) if (work / "trims.json").exists() else {}
    k = float(os.environ.get("STRENGTH", 0.85))
    xf = round(float(os.environ.get("XF", 0.4)) * FPS) / FPS
    ins, fc, plan, durs = [], [], [], []
    for i, shot in enumerate(ep["shots"]):
        sid = shot["id"]
        src = work / "clips" / f"{tag}-{sid}.mp4"
        if not src.exists():
            sys.exit(f"missing {src}: render it (render.sh) or drop the shot from the episode")
        a, b = trims.get(sid, [0, min(shot["seconds"], probe_dur(src))])
        n = round((b - a) * FPS)
        d = n / FPS
        ins += ["-ss", f"{a}", "-t", f"{b - a + 1}", "-i", str(src)]
        fc.append(f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps={FPS},setsar=1,"
                  f"format=yuv420p,{grade(stats(src, a, b), k)},format=yuv420p,tpad=stop_mode=clone:stop=-1,"
                  f"trim=end_frame={n},setpts=PTS-STARTPTS,settb=1/24000[v{i}]")
        sound = (f"[{i}:a]aresample={SR},aformat=sample_fmts=fltp:channel_layouts=stereo,loudnorm=I=-18:TP=-2:LRA=7,"
                 f"aresample={SR}," if has_audio(src) else f"anullsrc=r={SR}:cl=stereo,")
        durs.append(d)
        plan.append({"id": sid, "trim_start": a, "seconds": round(d, 4), "_a": sound})
    off, vl = 0.0, "v0"
    plan[0]["film_start"] = 0.0
    for i in range(1, len(durs)):
        off += durs[i - 1] - xf
        plan[i]["film_start"] = round(off, 4)
        fc.append(f"[{vl}][v{i}]xfade=transition=fade:duration={xf:.5f}:offset={off:.5f}[vx{i}]" if xf else
                  f"[{vl}][v{i}]concat=n=2:v=1:a=0[vx{i}]")
        vl = f"vx{i}"
    total = off + durs[-1]
    for i, p in enumerate(plan):
        d, ms = durs[i], round(p["film_start"] * 1000)
        fin = f"afade=t=in:d={xf:.5f}:curve=tri," if i and xf else ""
        fout = f",afade=t=out:st={d - xf:.5f}:d={xf:.5f}:curve=tri" if i < len(plan) - 1 and xf else ""
        fc.append(f"{p.pop('_a')}asetpts=PTS-STARTPTS,apad,atrim=end_sample={round(d * SR)},{fin}"
                  f"asetpts=PTS-STARTPTS{fout},adelay={ms}|{ms}[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(len(plan))) +
              f"amix=inputs={len(plan)}:normalize=0:duration=longest,atrim=end={total:.4f}[am]")
    run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", f"[{vl}]", "-map", "[am]",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-ar", str(SR), "-movflags", "+faststart", out])
    (work / "cut.json").write_text(json.dumps(plan, indent=1))
    print(f"WROTE {out} ({total:.1f} s, {len(durs)} shots, {xf:.2f} s dissolves) and {work / 'cut.json'}")


def sync(work, film, tol=0.040):
    import numpy as np
    work = Path(work)
    tag = f"aes-ep{json.loads((work / 'episode.json').read_text())['episode']:02}"

    def frames(p):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vf", f"fps={FPS},scale=32:18,format=gray",
                              "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
        f = np.frombuffer(raw, np.uint8).reshape(-1, 576).astype(np.float32)
        f -= f.mean(1, keepdims=True)                   # the grade is affine on luma: compare shapes only
        return f / (f.std(1, keepdims=True) + 1e-3)

    def sound(p, sr=8000):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.float32)

    fv, fa, bad = frames(film), sound(film), 0
    for p in json.loads((work / "cut.json").read_text()):
        src = work / "clips" / f"{tag}-{p['id']}.mp4"
        t0, d, f0 = p["trim_start"] + 0.6, p["seconds"] - 1.2, p["film_start"] + 0.6   # clear of the dissolves
        if d < 1:
            continue
        cv, ca = frames(src), sound(src)
        i, j = round(t0 * FPS), round(f0 * FPS)
        n = min(round(d * FPS), len(cv) - i)
        errs = {lag: float(np.abs(fv[j + lag:j + lag + n] - cv[i:i + n]).mean())
                for lag in range(-12, 13) if j + lag >= 0 and j + lag + n <= len(fv)}
        vl = min(errs, key=errs.get)
        e = sorted(errs.values())
        flat = e[1] - e[0] < 0.02 * e[0]                # nothing moves: the picture lag is not measurable
        s, kk = round(t0 * 8000), round(f0 * 8000)
        ref = ca[s:s + round(d * 8000)]
        m = len(ref)
        al = None
        if ref.std() > 1e-4:
            lags = [lag for lag in range(-4000, 4001, 8) if kk + lag >= 0 and kk + lag + m <= len(fa)]
            al = lags[int(np.argmax([np.dot(ref, fa[kk + lag:kk + lag + m]) for lag in lags]))] / 8000
        off = None if al is None or flat else al - vl / FPS
        ok = off is None or abs(off) <= tol
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {p['id']} at {p['film_start']:7.2f}s  picture "
              f"{'static' if flat else f'{vl / FPS:+.3f}s'}  sound {'none' if al is None else f'{al:+.3f}s'}"
              f"  lips {'n/a' if off is None else f'{off * 1000:+.0f} ms'}")
    print(f"SYNC {'FAIL' if bad else 'PASS'}: {bad} shots with the voice more than {tol * 1000:.0f} ms off the lips")
    sys.exit(1 if bad else 0)


def mix(film, music, out):
    dur = probe_dur(film)
    db = float(os.environ.get("MUSIC_DB", -20))
    fc = (f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{dur:.2f},asetpts=PTS-STARTPTS,aresample=48000,"
          f"aformat=channel_layouts=stereo,volume={db}dB,afade=t=in:d=1.5,afade=t=out:st={max(0, dur - 3):.2f}:d=3[m];"
          "[0:a]aresample=48000,aformat=channel_layouts=stereo,asplit[d][key];"
          "[m][key]sidechaincompress=threshold=0.02:ratio=6:attack=30:release=600:makeup=1[duck];"
          "[d][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9[a]")
    run(["ffmpeg", "-v", "error", "-y", "-i", film, "-i", music, "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])
    print(f"WROTE {out}: music at {db} dB, ducked under speech")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:] or ["-h"]
    {"cut": cut, "sync": sync, "mix": mix}.get(cmd, lambda *_: sys.exit(__doc__))(*args)
