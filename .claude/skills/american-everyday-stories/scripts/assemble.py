#!/usr/bin/env python3
"""Cut the rendered shots into one graded film, then lay the music bed under it.

  python3 scripts/assemble.py cut WORK episode.json film.mp4   # clips/<prefix>-<ID>.mp4 -> graded film + cut.json
  python3 scripts/assemble.py mix film.mp4 music.m4a out.mp4   # music bed ducked under speech

cut: each shot is trimmed to WORK/trims.json {"S03": [start, end]} (default: its first `seconds`
     from 0), scaled to 1920x1080, 24 fps, graded with GRADE (default: the reference look, see
     references/look.md; GRADE=none skips it), joined with hard cuts. Audio is kept untouched
     (no retiming: lip sync holds) and only levelled. cut.json records each shot's offset in the
     film and its trim start, so align.py can map the planned cues onto the film.
mix: the music is looped/trimmed to the film, faded in 1.5 s / out 3 s, sits at MUSIC_DB
     (default -20 dB under dialogue) and ducks a further ~10 dB while anyone speaks
     (sidechaincompress keyed on the dialogue). Loudness -16 LUFS, stereo 48 kHz."""
import json
import os
import subprocess
import sys
from pathlib import Path

# Warm 1980s negative print, measured from the reference (references/look.md): yellow-red shift
# (U ~118, V ~143), moderate saturation, lifted blacks, rolled-off whites, soft halation, fine grain.
LOOK = ("curves=r='0/0.055 0.25/0.27 0.5/0.535 0.75/0.79 1/0.97'"
        ":g='0/0.045 0.25/0.245 0.5/0.505 0.75/0.75 1/0.95'"
        ":b='0/0.07 0.25/0.235 0.5/0.455 0.75/0.68 1/0.87',"
        "eq=saturation=0.93:contrast=0.96,"
        "split[base][glow];[glow]curves=all='0/0 0.72/0 1/0.6',gblur=sigma=14[h];"
        "[base][h]blend=all_mode=screen:all_opacity=0.22,"
        "noise=c0s=5:c0f=t+u:c1s=2:c1f=t+u:c2s=2:c2f=t+u")


def run(args):
    subprocess.run(args, check=True)


def probe_dur(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(path)], capture_output=True, text=True, check=True).stdout)


def has_audio(path):
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip())


def cut(work, ep_path, out):
    work, ep = Path(work), json.loads(Path(ep_path).read_text())
    tag = f"aes-ep{ep['episode']:02}"
    trims = json.loads((work / "trims.json").read_text()) if (work / "trims.json").exists() else {}
    grade = os.environ.get("GRADE", LOOK)
    tmp = work / "cut"
    tmp.mkdir(exist_ok=True)
    parts, plan, off = [], [], 0.0
    for shot in ep["shots"]:
        sid = shot["id"]
        src = work / "clips" / f"{tag}-{sid}.mp4"
        if not src.exists():
            sys.exit(f"missing {src}: render it (render.sh) or drop the shot from the episode")
        a, b = trims.get(sid, [0, min(shot["seconds"], probe_dur(src))])
        vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24,setsar=1"
        fc = f"[0:v]{vf}" + ("" if grade == "none" else f",{grade}") + ",format=yuv420p[v]"
        ins = ["-ss", f"{a}", "-t", f"{b - a}", "-i", str(src)]
        if has_audio(src):
            maps = ["-map", "0:a", "-af", "aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-18:TP=-2:LRA=7,aresample=48000"]  # loudnorm outputs 192 kHz
        else:  # a silent shot still needs a track so the concat keeps audio in sync
            ins += ["-f", "lavfi", "-t", f"{b - a}", "-i", "anullsrc=r=48000:cl=stereo"]
            maps = ["-map", "1:a"]
        part = tmp / f"{sid}.mp4"
        run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fc, "-map", "[v]", *maps,
             "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(part)])
        plan.append({"id": sid, "film_start": round(off, 3), "trim_start": a, "seconds": round(b - a, 3)})
        off += probe_dur(part)
        parts.append(part)
    (tmp / "list.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    (work / "cut.json").write_text(json.dumps(plan, indent=1))
    print(f"WROTE {out} ({off:.1f} s, {len(parts)} shots, {len(parts) - 1} planned cuts) and {work / 'cut.json'}")


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
    {"cut": cut, "mix": mix}.get(cmd, lambda *_: sys.exit(__doc__))(*args)
