"""Healing music from Apple Loops: real, human-played piano / harp / strings / guitar parts that ship
with macOS and GarageBand (royalty-free in your own music and videos). ACE-Step's "soft piano" came
out as a static drone with no melody (hv-0001: "the music is not healing"); both reference reels are
melody-led (a piano or string line moving every ~0.3-0.8 s, warm, almost nothing above 2 kHz).

A family = loops with the same song name recorded to fit together (e.g. "Breathless Piano" +
"Breathless Harp"). Its parts are layered (the first part leads, the rest sit 6 dB under), looped with
cross-fades to the length, warmed (high cut, a little room) and set to one gain.

  python3 scripts/loops.py list
  python3 scripts/loops.py make out.m4a [--family Breathless] [--secs 24] [--seed 3]
  python3 scripts/loops.py fit ref.m4a ref.wav --secs 30      # loop any recording to a length
No --family: picked by --seed from FAMILIES (pass the idea number so neighbouring videos differ).
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOTS = [Path("/Library/Audio/Apple Loops/Apple"), Path("/Library/Application Support/GarageBand/Instrument Library")]
# calm, melodic families (checked: no drums, no holes; Sympathy, Full Moon, Find Strength, Slow Motion,
# Yearning dropped for 1-4 s of near silence); lead part first
FAMILIES = {
    "Breathless": ["Breathless Piano", "Breathless Harp"],
    "Longing": ["Longing Piano", "Longing Strings 01"],
    "Twilight": ["Twilight Piano"],
    "Distant Memories": ["Distant Memories Piano"],
    "Epoch": ["Epoch Ambient Piano"],
    "Honor": ["Honor Piano"],
    "Regrets": ["Regrets Piano"],
    "Early Days": ["Early Days Piano"],
    "Summers End": ["Summers End Acoustic Guitar"],
}
XF = 1.5
WARM = "highpass=f=60,lowpass=f=5000,aecho=0.8:0.6:45|90:0.18|0.10"  # warm, a little room


def find(name):
    for root in ROOTS:
        hit = next(root.rglob(f"{name}.caf"), None) if root.exists() else None
        if hit:
            return hit
    return None


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(p)], capture_output=True, text=True).stdout)


def make(family, out, secs):
    parts = [find(n) for n in FAMILIES[family]]
    parts = [p for p in parts if p]
    if not parts:
        sys.exit(f"no Apple Loops for {family} (install GarageBand's sound library)")
    seg = dur(parts[0])
    copies = 1 if seg >= secs else int((secs - XF) // (seg - XF)) + 1
    tmp = Path(tempfile.mkdtemp())
    args = ["ffmpeg", "-v", "error", "-y"]
    for p in parts:
        args += ["-i", str(p)]
    g = []
    for i in range(len(parts)):
        g.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,volume={0 if i == 0 else -6}dB[p{i}]")
    g.append("".join(f"[p{i}]" for i in range(len(parts))) +
             (f"amix=inputs={len(parts)}:normalize=0[layer]" if len(parts) > 1 else "anull[layer]"))
    if copies > 1:
        g.append(f"[layer]asplit={copies}" + "".join(f"[c{k}]" for k in range(copies)))
        prev = "c0"
        for k in range(1, copies):
            g.append(f"[{prev}][c{k}]acrossfade=d={XF}:c1=qsin:c2=qsin[l{k}]")
            prev = f"l{k}"
    else:
        prev = "layer"
    g.append(f"[{prev}]{WARM},atrim=duration={secs},afade=in:d=0.3,afade=out:st={secs - 3}:d=3[out]")
    args += ["-filter_complex", ";".join(g), "-map", "[out]", str(tmp / "m.wav")]
    subprocess.run(args, check=True)
    # a sparse loop leaves holes (Yearning: 4 s of near silence): reject any 1 s below -38 dB
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(tmp / "m.wav"), "-af",
                          f"atrim=0.5:{secs - 3},asetnsamples=44100,astats=metadata=1:reset=1,"
                          "ametadata=print:key=lavfi.astats.Overall.RMS_level", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    quiet = [v for v in re.findall(r"RMS_level=(-?[\d.]+|-inf)", err) if v == "-inf" or float(v) < -38]
    if quiet:
        sys.exit(f"{family}: {len(quiet)} s of near silence; pick another family")
    subprocess.run(["python3", str(Path(__file__).with_name("lnorm.py")), str(tmp / "m.wav"), out, "-18"], check=True)
    print(f"{out}: {family} ({', '.join(p.stem for p in parts)}) {secs} s")


def fit(src, out, secs):
    """Loop any recording with cross-fades to `secs` (a reference for `scripts/music` REF=)."""
    seg = dur(src)
    copies = 1 if seg >= secs else int((secs - XF) // (seg - XF)) + 1
    g = [f"[0:a]aresample=44100,aformat=channel_layouts=stereo,asplit={copies}" + "".join(f"[c{k}]" for k in range(copies))]
    prev = "c0"
    for k in range(1, copies):
        g.append(f"[{prev}][c{k}]acrossfade=d={XF}:c1=qsin:c2=qsin[l{k}]")
        prev = f"l{k}"
    g.append(f"[{prev}]atrim=duration={secs}[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", ";".join(g), "-map", "[out]",
                    "-ac", "2", str(out)], check=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    m = sub.add_parser("make")
    m.add_argument("out")
    m.add_argument("--family", choices=list(FAMILIES))
    m.add_argument("--secs", type=float, default=24)
    m.add_argument("--seed", type=int, default=0)
    f = sub.add_parser("fit")
    f.add_argument("src")
    f.add_argument("out")
    f.add_argument("--secs", type=float, default=30)
    a = ap.parse_args()
    if a.cmd == "fit":
        fit(a.src, a.out, a.secs)
        return
    if a.cmd == "list":
        for f, names in FAMILIES.items():
            found = [n for n in names if find(n)]
            print(f"{f:18} {', '.join(found) or 'MISSING'}")
        return
    make(a.family or list(FAMILIES)[a.seed % len(FAMILIES)], a.out, a.secs)


if __name__ == "__main__":
    main()
