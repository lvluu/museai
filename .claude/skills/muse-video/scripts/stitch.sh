#!/usr/bin/env bash
# Usage: stitch.sh out.mp4 clip1.mp4 clip2.mp4 [...]
# Joins clips made with CONTINUE_FROM. Each later clip starts on the previous
# clip's last frame, so its first frame is dropped to avoid a frozen duplicate.
# muse can return one clip of a chain at 720p, so every clip is scaled to the
# first clip's size, and each clip's audio is normalised to the same loudness
# (clips of one chain have come back up to 8 dB apart).
set -euo pipefail
out=$1; shift
read -r W H < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$1" | tr , ' ')
args=() chain="" n=0
for clip in "$@"; do
  args+=(-i "$clip")
  trim=""; [ $n -eq 0 ] || trim="trim=start_frame=1,"
  chain+="[$n:v]${trim}setpts=PTS-STARTPTS,scale=$W:$H:flags=lanczos,setsar=1[v$n];"
  chain+="[$n:a]asetpts=PTS-STARTPTS,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a$n];"
  n=$((n + 1))
done
for ((i = 0; i < n; i++)); do chain+="[v$i][a$i]"; done
chain+="concat=n=$n:v=1:a=1[v][a]"
ffmpeg -v error -y "${args[@]}" -filter_complex "$chain" -map "[v]" -map "[a]" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$out"
echo "WROTE $out"
