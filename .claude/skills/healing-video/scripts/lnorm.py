"""Two-pass (linear) loudness normalisation: one fixed gain for the whole file. Single-pass ffmpeg
loudnorm rides the gain up and down (it starts near silent and pumps on every level change), which
made hv-0001's sound feel late and laggy.

Usage: python3 scripts/lnorm.py in.wav out.m4a [-16] [extra -af filters to run first]
"""
import json
import re
import subprocess
import sys


def measure(src, pre, target):
    af = ",".join(filter(None, [pre, f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json"]))
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af", af, "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return json.loads(re.findall(r"\{[^{}]+\}", err)[-1])


def body_start(src, skip=2.0, win=0.25):
    """First second at or after `skip` where the track is within 4 dB of its usual level, so a
    video never opens on a quiet intro that then jumps up."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-af",
                          f"asetnsamples={int(44100 * win)},astats=metadata=1:reset=1,"
                          "ametadata=print:key=lavfi.astats.Overall.RMS_level", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    rms = [float(v) for v in re.findall(r"RMS_level=(-?[\d.]+|-inf)", err) if v != "-inf"]
    usual = sorted(rms)[len(rms) // 2]
    first = int(skip / win)
    for k in range(first, len(rms)):
        if rms[k] >= usual - 4:
            return round(k * win, 2)
    return skip


def main():
    if sys.argv[1] == "--body-start":
        print(body_start(sys.argv[2]))
        return
    src, out = sys.argv[1], sys.argv[2]
    target = sys.argv[3] if len(sys.argv) > 3 else "-16"
    pre = sys.argv[4] if len(sys.argv) > 4 else ""
    m = measure(src, pre, target)
    ln = (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    af = ",".join(filter(None, [pre, ln, "aresample=44100"]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-c:a", "aac", "-b:a", "192k", out], check=True)


if __name__ == "__main__":
    main()
