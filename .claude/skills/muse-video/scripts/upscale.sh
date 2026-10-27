#!/usr/bin/env bash
# Usage: upscale.sh in.mp4 out.mp4
# Makes the delivered video 4K UHD: 2160x3840 (9:16), 3840x2160 (16:9) or 2160x2160 (1:1).
# muse returns at most 1080p (1080x1920, 2026-10-27, 4K asked), so this scales with lanczos,
# adds a light unsharp to keep foliage, water and hair crisp, and re-encodes H.264 High at a
# 4K bitrate (CRF 16, plays in QuickTime, browsers and phones). Audio is copied untouched,
# frame count and timing do not change, so lip sync and captions stay where they were.
# A file already 4K is copied as it is.
set -euo pipefail
in=$1 out=$2
read -r w h < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$in" | tr x ' ')
if [ "$w" -gt "$h" ]; then W=3840 H=2160; elif [ "$w" -lt "$h" ]; then W=2160 H=3840; else W=2160 H=2160; fi
if [ "$w" -ge "$W" ] && [ "$h" -ge "$H" ]; then
  cp "$in" "$out"; echo "UHD $out already ${w}x${h}"; exit 0
fi
ffmpeg -v error -y -i "$in" \
  -vf "scale=${W}:${H}:flags=lanczos+accurate_rnd+full_chroma_int,unsharp=5:5:0.6:5:5:0.0,setsar=1" \
  -c:v libx264 -preset slow -crf 16 -profile:v high -level 5.1 -pix_fmt yuv420p \
  -c:a copy -movflags +faststart "$out"
read -r ow oh < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$out" | tr x ' ')
[ "$ow" = "$W" ] && [ "$oh" = "$H" ] || { echo "upscale gave ${ow}x${oh}, wanted ${W}x${H}" >&2; exit 1; }
echo "UHD $out ${w}x${h} -> ${W}x${H}"
