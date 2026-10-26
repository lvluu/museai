#!/usr/bin/env bash
# Usage: check_clip.sh clip.mp4 [previous_clip.mp4]
# Run on every clip before it is used as CONTINUE_FROM or stitched. Prints size,
# length, scene cuts, the transcript with speech start/end, and writes
# sheet_<clip>.jpg: the previous clip's last frame, then this clip at 2 fps.
# Re-render the clip if it shows: a cut the prompt did not ask for, a person not in
# the cast (they tend to walk in during the last second), spoken words not in the
# script (e.g. someone answering the ending question), the listener turning to the
# camera, or a seam jump between the first two tiles.
# SCRIPT=script.txt ("W: line" / "M: line" per spoken line) also runs speakers.py:
# voice pitch per line must fit the labelled speaker and the listener's lips must stay
# still (both automatic; WRONG VOICE = re-render, LISTENER MOUTH MOVES = reframe.py in the edit); it also writes mouths_<clip>.jpg.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
f=$1; b=$(basename "$f" .mp4); tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
ffprobe -v error -select_streams v:0 -show_entries stream=width,height:format=duration -of csv=p=0 "$f" | tr '\n' ' '; echo
echo "cuts: $(ffmpeg -hide_banner -i "$f" -vf "select='gt(scene,0.25)',showinfo" -f null - 2>&1 | grep -oE 'pts_time:[0-9.]+' | cut -d: -f2 | tr '\n' ' ')"
# VAD=0: with VAD on, Whisper drops the first line of a clip
VAD=0 WMODEL=${WMODEL:-medium} uv run --no-project --python 3.12 --with faster-whisper --with opencc-python-reimplemented python "$here/transcribe.py" "$f" "words_$b.json" 2>&1 | grep -E '^ +[0-9]' || true
if [ -n "${2:-}" ]; then ffmpeg -v error -y -sseof -0.05 -i "$2" -frames:v 1 -update 1 "$tmp/prev.png"
else ffmpeg -v error -y -i "$f" -frames:v 1 "$tmp/prev.png"; fi
ffmpeg -v error -y -i "$tmp/prev.png" -i "$f" -filter_complex \
  "[0]scale=216:384,setsar=1[p];[1]fps=2,scale=216:384,setsar=1[c];[p][c]concat=n=2:v=1:a=0,tile=11x2" \
  -frames:v 1 "sheet_$b.jpg"
echo "sheet: sheet_$b.jpg"
if [ -n "${SCRIPT:-}" ]; then
  uv run -q --no-project --python 3.12 --with mediapipe==0.10.14 --with opencv-python-headless --with librosa \
    python "$here/speakers.py" "$f" "$SCRIPT" "words_$b.json" "mouths_$b.jpg" 2>&1 | grep -vE 'WARNING|INFO|^W0000|^I0000' || true
fi
