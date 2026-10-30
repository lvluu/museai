# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["librosa", "soundfile", "numpy", "scipy"]
# ///
"""Find the catchy parts of a song and cut the video's soundtrack from them.

Usage:
  uv run --no-project scripts/music_sections.py add song.webm --id shangri-la-ref [--tags "..."]
      copy a track into the library (~/.local/share/museai/music/chinese-scenery/) and analyse it
  uv run --no-project scripts/music_sections.py show <id|file>
      print the section map (bars, loudness, repetition, catchy score, role)
  uv run --no-project scripts/music_sections.py cut <id|file> --seconds 45-60 --out track.m4a [--start 128]
      cut the best window: it opens on a loud, repeated section (the hook, music already going at
      frame 0), keeps the song's own soft part in the middle when there is one (tea / street moments)
      and, when the window reaches the song's end, ends on the song's real outro instead of a fade.
      Writes track.m4a and track.beats.json ({"bpm", "beats", "drop", "sections"}) in window time.

Catchy score per section = loudness + repetition (a chorus comes back) + onset punch, each z-scored.
A section's role: "hook" (top catchy, loud), "build", "soft" (>= 5 dB under the song's median), "outro".
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import librosa
import numpy as np

LIB = Path.home() / ".local/share/museai/music/chinese-scenery"
SR = 22050


def resolve(src):
    p = Path(src).expanduser()
    if p.exists():
        return p
    hits = sorted(LIB.glob(f"{src}.*"))
    hits = [h for h in hits if h.suffix not in (".json",)]
    if not hits:
        sys.exit(f"no track {src} (library: {LIB})")
    return hits[0]


def analyse(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    y, sr = np.frombuffer(raw, np.float32).copy(), SR
    dur = len(y) / sr
    tempo, bf = librosa.beat.beat_track(y=y, sr=sr)
    beats = librosa.frames_to_time(bf, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    # bars of 4 beats are the unit: sections start and cuts land on them
    bars = beats[::4]
    rms = librosa.feature.rms(y=y)[0]
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    t = librosa.times_like(rms, sr=sr)
    edges = np.append(bars, dur)
    bar_db, bar_on, bar_ch = [], [], []
    for a, b in zip(edges[:-1], edges[1:], strict=True):
        m = (t >= a) & (t < b)
        bar_db.append(20 * np.log10(rms[m].mean() + 1e-9) if m.any() else -80)
        bar_on.append(onset[m].mean() if m.any() else 0)
        c = chroma[:, m].mean(axis=1) if m.any() else np.zeros(12)
        bar_ch.append(c / (np.linalg.norm(c) + 1e-9))
    bar_db, bar_on, bar_ch = np.array(bar_db), np.array(bar_on), np.array(bar_ch)
    # sections: split where loudness jumps >= 4 dB between bars or every 8 bars of steady level
    cuts = [0]
    for i in range(1, len(bars)):
        if abs(bar_db[i] - bar_db[i - 1]) >= 4 or i - cuts[-1] >= 8:
            cuts.append(i)
    cuts.append(len(bars))
    secs = []
    for a, b in zip(cuts[:-1], cuts[1:], strict=True):
        if b <= a:
            continue
        secs.append(
            {
                "start": round(float(bars[a]), 3),
                "end": round(float(edges[b]), 3),
                "bars": b - a,
                "db": round(float(bar_db[a:b].mean()), 1),
                "onset": round(float(bar_on[a:b].mean()), 2),
                "chroma": bar_ch[a:b].mean(axis=0),
            }
        )
    med = float(np.median(bar_db))
    for s in secs:
        sims = [float(np.dot(s["chroma"], o["chroma"])) for o in secs if o is not s]
        s["repeat"] = round(sum(x > 0.97 for x in sims) + max(sims, default=0), 2)

    def z(key):
        v = np.array([s[key] for s in secs], float)
        return (v - v.mean()) / (v.std() + 1e-9)

    score = z("db") + z("repeat") + 0.5 * z("onset")
    for s, sc in zip(secs, score, strict=True):
        s["score"] = round(float(sc), 2)
        s["role"] = "soft" if s["db"] <= med - 5 else "build"
        del s["chroma"]
    top = sorted(secs, key=lambda s: -s["score"])[: max(2, len(secs) // 4)]
    for s in top:
        if s["role"] != "soft":
            s["role"] = "hook"
    if secs and secs[-1]["db"] <= med - 5:
        secs[-1]["role"] = "outro"
    return {
        "file": str(path),
        "seconds": round(dur, 3),
        "bpm": round(bpm, 2),
        "median_db": round(med, 1),
        "beats": [round(float(b), 3) for b in beats],
        "sections": secs,
    }


def load(src):
    path = resolve(src)
    meta = path.with_suffix(".json")
    if meta.exists():
        return json.loads(meta.read_text())
    return analyse(path)


def best_start(a, seconds):
    """Hook-first window of `seconds` = (min, max): starts on a loud section (hook or build within
    3 dB of the median) or on the one-bar pickup right before one (the swell under the reveal).
    Prefers top catchy sections, one soft section past the first third (room for intimate shots)
    and windows that reach the song's real ending. Returns (start, length)."""
    lo, hi = seconds
    secs, med = a["sections"], a["median_db"]
    loud = [s for s in secs if s["role"] == "hook" or (s["role"] == "build" and s["db"] >= med - 3)]
    starts = {s["start"]: 0.0 for s in loud}
    for i, s in enumerate(secs[:-1]):
        if s["bars"] == 1 and s["role"] == "soft" and secs[i + 1] in loud:
            starts[s["start"]] = 0.5  # pickup bar: swell into the hook
    best, best_v = None, -1e9
    for st, bonus in starts.items():
        to_end = a["seconds"] - st
        length = to_end if lo <= to_end <= hi + 0.5 else hi
        if st + length > a["seconds"] + 0.5:
            continue
        inside = [x for x in secs if st <= x["start"] < st + length]
        # the last fifth is the ending: a real outro is meant to calm down, it does not count against it
        body = [x for x in inside if x["start"] < st + 0.8 * length and x["role"] != "soft"]
        v = bonus + np.mean([x["score"] for x in body] or [0])
        v += 1.0 if any(x["role"] == "soft" and x["start"] > st + length / 3 for x in inside) else 0
        v += 1.5 if length == to_end else 0
        if v > best_v:
            best, best_v = (st, length), v
    if best is None:
        sys.exit(f"no loud section leaves {lo} s of song: use a shorter --seconds or --start")
    return best


def cut(a, start, seconds, out):
    src = a["file"]
    end = min(start + seconds, a["seconds"])
    to_end = end >= a["seconds"] - 0.5
    fade = "" if to_end else f",afade=t=out:st={seconds - 1.5:.3f}:d=1.5"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", src,
         "-af", f"aresample=48000,afade=t=in:d=0.02{fade},loudnorm=I=-14:TP=-1.5:LRA=11",
         "-ac", "2", "-c:a", "aac", "-b:a", "192k", str(out)],
        check=True,
    )
    beats = [round(b - start, 3) for b in a["beats"] if start <= b < end]
    secs = [
        {**s, "start": round(max(s["start"], start) - start, 3), "end": round(min(s["end"], end) - start, 3)}
        for s in a["sections"]
        if s["end"] > start and s["start"] < end
    ]
    Path(out).with_suffix(".beats.json").write_text(
        json.dumps({"bpm": a["bpm"], "beats": beats, "drop": beats[0] if beats else 0, "sections": secs,
                    "source": src, "start": start, "seconds": round(end - start, 3)})
    )
    print(f"OUT {out}: {start:.2f}-{end:.2f} s of {Path(src).name} ({end - start:.1f} s, "
          f"{'song ending' if to_end else 'fade out'}, {len(beats)} beats)")


def show(a):
    print(f"{Path(a['file']).name}: {a['seconds']} s, {a['bpm']} BPM, median {a['median_db']} dB")
    for s in a["sections"]:
        print(f"  {s['start']:7.2f}-{s['end']:7.2f}  {s['bars']:2d} bars  {s['db']:6.1f} dB  "
              f"rep {s['repeat']:4.2f}  score {s['score']:5.2f}  {s['role']}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("src")
    p.add_argument("--id", required=True)
    p.add_argument("--tags", default="", help="genre / instruments / mood, for picking it later")
    p = sub.add_parser("show")
    p.add_argument("src")
    p = sub.add_parser("cut")
    p.add_argument("src")
    p.add_argument("--seconds", required=True, help="N or MIN-MAX (a range lets the window end on the song's real ending)")
    p.add_argument("--start", type=float)
    p.add_argument("--out", required=True)
    sub.add_parser("list")
    a = ap.parse_args()
    if a.cmd == "list":
        for m in sorted(LIB.glob("*.json")):
            d = json.loads(m.read_text())
            print(f"{m.stem:24s} {d['seconds']:6.1f} s {d['bpm']:6.1f} BPM  {d.get('tags', '')}")
        return
    if a.cmd == "add":
        LIB.mkdir(parents=True, exist_ok=True)
        dst = LIB / f"{a.id}.m4a"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(Path(a.src).expanduser()), "-vn",
                        "-c:a", "aac", "-b:a", "256k", str(dst)], check=True)
        d = analyse(dst)
        d["tags"] = a.tags
        dst.with_suffix(".json").write_text(json.dumps(d))
        show(d)
        return
    d = load(a.src)
    if a.cmd == "show":
        show(d)
        return
    lo, _, hi = a.seconds.partition("-")
    rng = (float(lo), float(hi or lo))
    if a.start is not None:
        start, length = a.start, rng[1]
    else:
        start, length = best_start(d, rng)
    cut(d, start, length, Path(a.out).expanduser().resolve())


if __name__ == "__main__":
    main()
