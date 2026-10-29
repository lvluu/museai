#!/usr/bin/env python3
"""Cut a scenery episode from its rendered segments and soundtrack.

Usage:
  python3 scripts/compose.py plan.json [--music track.m4a] [--out scenic-<slug>.mp4] [--at 2=1.0]

Per segment: skips muse's settle-in (0.5 s, 0 for a photo segment whose first frame is the hook;
--at N=S forces segment N to start at S s), keeps the planned length, scales/crops to 1080x1920
(or 1920x1080) at 24 fps. Segments join with a 0.5 s dissolve, each inner cut moved onto the nearest
beat of track.beats.json (within 0.6 s) so the picture changes with the music. Audio: the music on
top, the clips' own natural ambience under it (denoised: muse clips carry a -50 dB hiss floor, -14 dB), music fades out over the last 1.2 s so the
replay loops; loudness -14 LUFS.
"""

import argparse
import json
import subprocess
from pathlib import Path

XF = 0.5
SNAP = 0.6


def probe(path, entry):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", entry, "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--music")
    ap.add_argument("--out")
    ap.add_argument(
        "--at", action="append", default=[], help="N=seconds: start of segment N's window"
    )
    a = ap.parse_args()
    plan_path = Path(a.plan).resolve()
    work = plan_path.parent
    p = json.loads(plan_path.read_text())
    music = Path(a.music) if a.music else work / "track.m4a"
    out = Path(a.out) if a.out else work / f"{p['name']}.mp4"
    w, h = (1080, 1920) if p["aspect"] == "9:16" else (1920, 1080)
    forced = {int(k): float(v) for k, v in (x.split("=") for x in a.at)}

    segs = p["segments"]
    cuts = [s["end"] for s in segs[:-1]]
    beats_file = music.with_suffix(".beats.json")
    if beats_file.exists() and cuts:
        beats = json.loads(beats_file.read_text())["beats"]
        cuts = [
            min((b for b in beats if abs(b - c) <= SNAP), key=lambda b: abs(b - c), default=c)
            for c in cuts
        ]
    bounds = [0, *cuts, p["seconds"]]
    lengths = [bounds[i + 1] - bounds[i] for i in range(len(segs))]

    inputs, vf, af = [], [], []
    for i, (s, ln) in enumerate(zip(segs, lengths, strict=True)):
        clip = work / f"seg{s['n']}.mp4"
        start = forced.get(s["n"], 0.0 if s.get("photo") else 0.5)
        # dissolves are centred on the cuts: inner segments overlap both neighbours by XF/2
        keep = ln + XF / 2 * ((i > 0) + (i < len(segs) - 1))
        dur = float(probe(clip, "format=duration"))
        if start + keep > dur:
            start = max(0.0, dur - keep)
            print(f"seg{s['n']}: only {dur:.1f} s, window moved to {start:.2f} s")
        inputs += ["-ss", f"{start:.3f}", "-t", f"{keep:.3f}", "-i", str(clip)]
        vf.append(
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=24,"
            f"setsar=1,format=yuv420p,settb=AVTB,setpts=PTS-STARTPTS[v{i}]"
        )
        has_audio = bool(probe(clip, "stream=codec_type").count("audio"))
        src = f"[{i}:a]" if has_audio else f"anullsrc=r=48000:cl=stereo,atrim=0:{keep:.3f},"
        af.append(f"{src}aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]")
        print(
            f"seg{s['n']}: {start:.2f}-{start + keep:.2f} s of {clip.name} -> {bounds[i]:.2f}-{bounds[i + 1]:.2f} s"
        )

    chain, achain = "[v0]", "[a0]"
    for i in range(1, len(segs)):
        off = bounds[i] - XF / 2
        vf.append(f"{chain}[v{i}]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{i}]")
        af.append(f"{achain}[a{i}]acrossfade=d={XF}[y{i}]")
        chain, achain = f"[x{i}]", f"[y{i}]"
    total = p["seconds"]
    m = len(segs)
    inputs += ["-i", str(music)]
    af.append(f"{achain}afftdn=nr=40:nf=-40:tn=0,lowpass=f=9000,volume=-14dB,atrim=0:{total}[amb]")
    af.append(
        f"[{m}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total},asetpts=PTS-STARTPTS,"
        f"afftdn=nr=40:nf=-40:tn=0,afade=t=out:st={total - 1.2:.2f}:d=1.2[mus]"
    )
    af.append("[mus][amb]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    vf.append(f"{chain}trim=0:{total},setpts=PTS-STARTPTS[vout]")
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        *inputs,
        "-filter_complex",
        ";".join(vf + af),
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "16",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        "-t",
        str(total),
        str(out),
    ]
    subprocess.run(cmd, check=True)
    print(
        f"OUT {out} ({float(probe(out, 'format=duration')):.2f} s, cuts at {[round(c, 2) for c in cuts]})"
    )


if __name__ == "__main__":
    main()
