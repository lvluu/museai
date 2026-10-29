"""Assemble a zoominview reel: reaction clip A + reveal clip B as one continuous shot, an eased digital push-in
on the view, and the music placed so its drop/swell lands the moment the view opens.

Usage:
  python3 scripts/compose.py --plan plan.json --music track.m4a --out zoom-<slug>.mp4 a.mp4 b.mp4 [c.mp4] [--reveal 8.4]

- Join: each clip was rendered from the previous one's last frame, so its first frame is dropped and the cut sits inside the
  swing/whip/hand motion; nothing else is blended.
- --reveal = seconds into the reel when the view is fully open (default plan.reveal_time). Check the contact
  sheet and pass the real time: the music drop and the zoom start follow it.
- --zoom 1.15 = extra digital push-in from the reveal to the end, smoothstep-eased, rendered on a 2x
  supersampled frame so it stays sub-pixel smooth. 1 = none (muse's own push-in only).
- Music: the drop from <music>.beats.json goes to --reveal: a late reveal cuts up to 0.6 s off clip A's head
  (more would cut the gasp; re-shape the music instead), an early one trims the music head with a fade-in; fade-out at the end; the clips' own wind/ambience stays underneath at --ambience.
- A reel longer than the track loops the track's body (from the drop to 1 s before its end) with
  1 s crossfades, so a short reference track still covers a long reel.
- Output keeps the clips' frame rate (muse: 24 fps) so every frame shows once (24 -> 30 judders).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def probe(path, entries, stream=None):
    cmd = ["ffprobe", "-v", "error", "-show_entries", entries, "-of", "csv=p=0"]
    if stream:
        cmd[3:3] = ["-select_streams", stream]
    return subprocess.run(cmd + [path], capture_output=True, text=True, check=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+", help="a.mp4 b.mp4 [c.mp4]: each rendered from the previous one's last frame")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--music", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reveal", type=float)
    ap.add_argument("--drop", type=float, help="music time of the drop/swell; default from <music>.beats.json")
    ap.add_argument("--zoom", type=float, default=1.15)
    ap.add_argument("--zoom-at", type=float, help="reel second the digital push-in starts (default: the reveal; with a pull-back clip, the start of the last clip)")
    ap.add_argument("--ambience", type=float, default=0.18, help="clip sound volume under the music (0 = off)")
    ap.add_argument("--grade", type=float, default=1.0, help="0 = none; 1 = light phone-style punch")
    ap.add_argument("--size", default="1080x1920")
    a = ap.parse_args()
    plan = json.loads(Path(a.plan).read_text())
    w, h = map(int, a.size.split("x"))
    if len(a.clips) < 2:
        ap.error("need at least two clips")
    num, _, den = probe(a.clips[0], "stream=r_frame_rate", "v:0").partition("/")
    fps = float(num) / float(den or 1)
    lens = [float(probe(c, "format=duration")) for c in a.clips]
    len_a = lens[0]
    frame = 1 / fps
    length = sum(lens) - frame * (len(lens) - 1)
    reveal = a.reveal if a.reveal is not None else min(plan["reveal_time"], length - 2)
    drop = a.drop
    if drop is None:
        beats = json.loads(Path(a.music).with_suffix(".beats.json").read_text())
        drop = beats.get("drop") or 0.0
    music_len = float(probe(a.music, "format=duration"))
    xf = 1.0  # crossfade between loops of the track body
    body = (drop, music_len - 1.0)
    # a reel must not open in silence: when the music's drop comes before the reveal, cut the head of clip A
    # (muse's start settle), at most 0.6 s: more cut the wide-eyed gasp, the hook (Madeira, 1.5 s cut)
    head = max(0.0, min(reveal - drop, 0.6))
    if reveal - drop > 0.6:
        print(f"warning: music drop {drop:.2f}s is {reveal - drop:.2f}s before the reveal; re-shape the track "
              "(scripts/music re-runs music.py --raw at the song's tempo) or pass a later --drop", file=sys.stderr)
    length -= head
    reveal -= head
    shift = reveal - drop  # music time t plays at reel time t + shift
    loops = 0
    while music_len + loops * (body[1] - body[0] - xf) + shift < length and body[1] - body[0] > 2 * xf:
        loops += 1
    music_total = music_len + loops * (body[1] - body[0] - xf)
    total = min(length, music_total + shift)

    # 2x supersample, then zoompan with z(t) eased from 1 at --zoom-at to --zoom at the end
    zoom_at = a.zoom_at - head if a.zoom_at is not None else reveal
    t = f"(in/{fps:.4f})"
    p = f"clip(({t}-{zoom_at:.3f})/{max(0.1, total - zoom_at):.3f},0,1)"
    z = f"1+{a.zoom - 1:.4f}*({p}*{p}*(3-2*{p}))"
    sat, con = 1 + 0.06 * a.grade, 1 + 0.03 * a.grade
    norm = f"scale={2 * w}:{2 * h}:force_original_aspect_ratio=increase:flags=lanczos,crop={2 * w}:{2 * h},setsar=1,fps={fps:.4f}"
    n = len(a.clips)
    chains = [f"[0:v]trim=start={head:.3f},setpts=PTS-STARTPTS,{norm}[v0]"]
    chains += [f"[{i}:v]trim=start_frame=1,setpts=PTS-STARTPTS,{norm}[v{i}]" for i in range(1, n)]
    chains.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vj]")
    chains += [f"[vj]zoompan=z='{z}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={w}x{h}:fps={fps:.4f},"
              f"eq=saturation={sat:.2f}:contrast={con:.2f},trim=duration={total:.3f},format=yuv420p[v]"]
    if loops:
        # head of the track up to the end of its body, then the body again `loops` times, crossfaded
        parts = [f"[{n}:a]aresample=48000,asplit={loops + 1}" + "".join(f"[s{i}]" for i in range(loops + 1))]
        parts.append(f"[s0]atrim=0:{body[1]:.3f},asetpts=PTS-STARTPTS[l0]")
        for i in range(1, loops + 1):
            parts.append(f"[s{i}]atrim={body[0]:.3f}:{body[1]:.3f},asetpts=PTS-STARTPTS[b{i}]")
            parts.append(f"[l{i - 1}][b{i}]acrossfade=d={xf}:c1=tri:c2=tri[l{i}]")
        chains += parts
        music = f"[l{loops}]"
    else:
        music = f"[{n}:a]aresample=48000,"
    music += f"adelay={shift * 1000:.0f}:all=1," if shift > 0 else f"atrim=start={-shift:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.4,"
    music += f"apad,atrim=0:{total:.3f},afade=t=out:st={max(0, total - 1.0):.3f}:d=1.0[m]"
    chains.append(music)
    has_audio = [bool(probe(c, "stream=index", "a")) for c in a.clips]
    if a.ambience > 0 and all(has_audio):
        chains.append(f"[0:a]atrim=start={head:.3f},asetpts=PTS-STARTPTS,aresample=48000[a0]")
        chains += [f"[{i}:a]aresample=48000,atrim=start={frame:.4f},asetpts=PTS-STARTPTS[a{i}]" for i in range(1, n)]
        chains += ["".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,volume={a.ambience},atrim=0:{total:.3f}[amb]",
                   "[m][amb]amix=inputs=2:duration=first:normalize=0,afftdn=nr=40:nf=-40:tn=0,loudnorm=I=-14:TP=-1.5[out]"]
    else:
        chains.append("[m]afftdn=nr=40:nf=-40:tn=0,loudnorm=I=-14:TP=-1.5[out]")
    cmd = ["ffmpeg", "-v", "error", "-y", *(x for c in a.clips for x in ("-i", c)), "-i", a.music, "-filter_complex", ";".join(chains),
           "-map", "[v]", "-map", "[out]", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-r", f"{fps:.4f}",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{total:.3f}", a.out]
    subprocess.run(cmd, check=True)
    print(json.dumps({"out": a.out, "length": round(float(probe(a.out, "format=duration")), 2), "fps": fps,
                      "head_cut": round(head, 3), "join": round(len_a - head, 3), "reveal": reveal, "music_drop": drop, "music_shift": round(shift, 3),
                      "zoom": a.zoom, "zoom_at": round(zoom_at, 3), "music_loops": loops}, indent=1))


if __name__ == "__main__":
    main()
