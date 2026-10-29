"""color_match.py in.mp4 out.mp4 [REF_SECONDS=2] [SMOOTH=3]
Removes slow colour drift across a CONTINUE_FROM chain: muse darkens/greens each continued clip a
little, so clip 15 sat ~30 % darker in red than clip 1. Per-frame mean RGB is smoothed over SMOOTH
seconds and every frame gets per-channel gains back to the mean of the first REF_SECONDS. Smoothing
keeps gestures and blinks from pumping the grade. Audio is copied, frames are not retimed.
"""
import json
import os
import subprocess
import sys

import numpy as np

src, dst = sys.argv[1], sys.argv[2]
ref_s = float(os.environ.get("REF_SECONDS", 2))
smooth_s = float(os.environ.get("SMOOTH", 3))
info = json.loads(subprocess.check_output(
    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
     "stream=width,height,r_frame_rate", "-of", "json", src]))["streams"][0]
w, h = info["width"], info["height"]
num, den = map(int, info["r_frame_rate"].split("/"))
fps = num / den


def read(path, size):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={size[0]}:{size[1]}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = size[0] * size[1] * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(size[1], size[0], 3)
    p.wait()


means = np.array([f.reshape(-1, 3).mean(0) for f in read(src, (w // 8, h // 8))])
k = max(1, int(smooth_s * fps))
pad = np.pad(means, ((k // 2, k - 1 - k // 2), (0, 0)), mode="edge")
sm = np.stack([np.convolve(pad[:, c], np.ones(k) / k, mode="valid") for c in range(3)], 1)
ref = means[: max(1, int(ref_s * fps))].mean(0)
gains = ref / np.maximum(sm, 1)
print(f"frames {len(means)}  gain range R {gains[:,0].min():.2f}-{gains[:,0].max():.2f} "
      f"G {gains[:,1].min():.2f}-{gains[:,1].max():.2f} B {gains[:,2].min():.2f}-{gains[:,2].max():.2f}")
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                        "-r", info["r_frame_rate"], "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?",
                        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "-c:a", "copy", dst], stdin=subprocess.PIPE)
for i, f in enumerate(read(src, (w, h))):
    g = gains[min(i, len(gains) - 1)]
    enc.stdin.write(np.clip(f.astype(np.float32) * g, 0, 255).astype(np.uint8).tobytes())
enc.stdin.close()
enc.wait()
print(dst)
