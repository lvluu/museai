#!/usr/bin/env python3
"""Pull a chosen still into the memoriescore close-up bands before it seeds the render.

usage: python3 scripts/still_match.py <in.png> <out.png>
Muse stills come out with hot skin highlights (p90 ~175) and a razor-sharp picture; the same roll-off curve as
the film grade (finish.py), a touch of blur and a soft halation bring them to skin p90 ~140, a soft glow.
Check with still_check.py afterwards.
"""
import subprocess
import sys

CHAIN = (
    "format=gbrp,curves=all='0/0 0.12/0.12 0.35/0.34 0.6/0.51 0.8/0.60 1/0.72',"
    "colorbalance=rm=0.04:gm=-0.02:bm=0.05:rh=0.03:gh=-0.01:bh=0.04,split[a][b];[b]gblur=sigma=30[g];[a][g]blend=all_mode=screen:all_opacity=0.12,format=rgb24,gblur=sigma=1.2"
)

src, dst = sys.argv[1:3]
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", CHAIN, dst], check=True)
print(dst)
