#!/usr/bin/env bash
# Usage: stitch.sh out.mp4 clip1.mp4 clip2.mp4 [...]
# Joins clips made with CONTINUE_FROM. Each later clip starts on the previous
# clip's last frame, so its first frame is dropped to avoid a frozen duplicate.
# muse can return one clip of a chain at 720p, so every clip is scaled to the
# first clip's size, and each clip's audio is normalised to the same loudness
# (clips of one chain have come back up to 8 dB apart). Each clip is denoised first:
# muse returned EP10 clips with a white hiss floor that loudnorm lifted into earshot;
# afftdn removes it without touching speech or music, and never retimes, so lip sync holds.
# XFADE=0.25 joins with a dissolve of that length instead of a hard join: continued clips
# start slightly reframed, which jumps at the seam (EP08: YDIF 6.6 and 18.9 vs ~1). Only
# when both sides of every seam are silent for XFADE s (trim to ~0.4 s after the last
# syllable first), so no two mouths blend.
# XFADE_AT=2,3: dissolve only those seams (1 = between clip 1 and 2), hard-join the rest; e.g. a
# seam ease_seams.py left with a RESIDUAL pose change (EP44: XFADE=0.12 on the silent A->B seam)
# while the intro cut stays a hard cut.
set -euo pipefail
out=$1; shift
read -r W H < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$1" | tr , ' ')
args=() chain="" n=0 lens=()
for clip in "$@"; do
  args+=(-i "$clip")
  # cut each clip's audio to exactly its kept video frames: the dropped first frame's audio,
  # and any audio running past the last frame, would push later clips' voices off their lips
  read -r fps nb < <(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=r_frame_rate,nb_read_packets -of csv=p=0 "$clip" | tr , ' ')
  skip=0; [ $n -eq 0 ] || skip=1
  read -r a0 a1 < <(python3 -c "from fractions import Fraction as F; f=F('$fps'); print(float($skip/f), float($nb/f))")
  trim=""; [ $skip -eq 0 ] || trim="trim=start_frame=1,"
  chain+="[$n:v]${trim}setpts=PTS-STARTPTS,scale=$W:$H:flags=lanczos,setsar=1[v$n];"
  chain+="[$n:a]afftdn=nr=40:nf=-40:tn=0,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,atrim=start=$a0:end=$a1,asetpts=PTS-STARTPTS,apad=whole_dur=$(python3 -c "print($a1-$a0)")[a$n];"
  lens+=("$(python3 -c "print($a1-$a0)")")
  n=$((n + 1))
done
if [ -n "${XFADE:-}" ]; then
  v="[v0]" a="[a0]" t=${lens[0]}
  for ((i = 1; i < n; i++)); do
    chain=${chain//"[v$i];"/",fps=$fps,settb=1/24[v$i];"}
    if [ -n "${XFADE_AT:-}" ] && [[ ",$XFADE_AT," != *",$i,"* ]]; then
      chain+="${v}${a}[v$i][a$i]concat=n=2:v=1:a=1[cv$i][xa$i];[cv$i]settb=1/24[xv$i];"
    else
      t=$(python3 -c "print($t-$XFADE)")
      chain+="${v}[v$i]xfade=transition=fade:duration=$XFADE:offset=$t[xv$i];${a}[a$i]acrossfade=d=$XFADE[xa$i];"
    fi
    v="[xv$i]" a="[xa$i]" t=$(python3 -c "print($t+${lens[$i]})")
  done
  chain=${chain//"[v0];"/",fps=$fps,settb=1/24[v0];"}
  chain+="${v}null[v];${a}anull[a]"
else
  for ((i = 0; i < n; i++)); do chain+="[v$i][a$i]"; done
  chain+="concat=n=$n:v=1:a=1[v][a]"
fi
ffmpeg -v error -y "${args[@]}" -filter_complex "$chain" -map "[v]" -map "[a]" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart "$out"
echo "WROTE $out"
