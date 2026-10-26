#!/usr/bin/env bash
# Usage: stitch.sh out.mp4 clip1.mp4 clip2.mp4 [...]
# Joins clips made with CONTINUE_FROM. Each later clip starts on the previous
# clip's last frame, so its first frame is dropped to avoid a frozen duplicate.
set -euo pipefail
out=$1; shift
args=() chain="" n=0
for clip in "$@"; do
  args+=(-i "$clip")
  if [ $n -eq 0 ]; then
    chain+="[0:v]setpts=PTS-STARTPTS[v0];[0:a]asetpts=PTS-STARTPTS[a0];"
  else
    chain+="[$n:v]trim=start_frame=1,setpts=PTS-STARTPTS[v$n];[$n:a]asetpts=PTS-STARTPTS[a$n];"
  fi
  n=$((n + 1))
done
for ((i = 0; i < n; i++)); do chain+="[v$i][a$i]"; done
chain+="concat=n=$n:v=1:a=1[v][a]"
ffmpeg -v error -y "${args[@]}" -filter_complex "$chain" -map "[v]" -map "[a]" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$out"
echo "WROTE $out"
