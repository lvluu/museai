#!/usr/bin/env bash
# Usage: FINAL=1 deliver.sh final.mp4 work_dir [prefix]
# Only once the user has accepted the 1080p preview (shown from the work folder, never copied to
# the Desktop): writes the ONE deliverable, the 4K UHD video (upscale.sh, Real-ESRGAN, ~1 h for 15 s;
# UHD=0 keeps the rendered size), to ~/Desktop (DEST=dir to change) and checks it. Then it deletes
# every other resource made for the video: earlier Desktop copies whose name starts with prefix,
# the work folder (raw clips, takes, sheets, mouth strips, frame grabs, cues, words, prompts), the
# ~/Movies/museai renders starting with prefix, and the server's identical copies in data/media/.
# prefix defaults to the work folder's name (e.g. ep10). Deleted = moved to the Trash.
set -euo pipefail
final=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
work=$(cd "$2" && pwd)
prefix=${3:-$(basename "$work")}
dest=${DEST:-$HOME/Desktop}

# never trash a home, repo or system folder by a wrong argument
case "$work" in
  /|"$HOME"|"$HOME"/Desktop|"$HOME"/Movies|"$HOME"/Movies/museai|"$HOME"/Work|"$HOME"/Documents|"$dest")
    echo "refusing to trash $work" >&2; exit 1 ;;
esac
[ -e "$work/.git" ] || [ -e "$work/pyproject.toml" ] && { echo "refusing to trash a repo: $work" >&2; exit 1; }
[ ${#prefix} -ge 3 ] || { echo "prefix '$prefix' too short" >&2; exit 1; }

mkdir -p "$dest"
out="$dest/$(basename "$final")"
[ "${FINAL:-0}" = 1 ] || { echo "preview: show $final from the work folder; nothing goes to the Desktop before FINAL=1" >&2; exit 1; }
if [ "${UHD:-1}" = 0 ]; then
  cp "$final" "$out"
  cmp -s "$final" "$out" || { echo "copy differs: $out" >&2; exit 1; }
else
  "$(dirname "$0")/upscale.sh" "$final" "$out"
  frames() { ffprobe -v error -count_packets -select_streams v:0 -show_entries stream=nb_read_packets -of csv=p=0 "$1"; }
  [ "$(frames "$final")" = "$(frames "$out")" ] || { echo "frame count differs: $out" >&2; exit 1; }
fi
ffprobe -v error -show_entries format=duration -of csv=p=0 "$out" >/dev/null || { echo "copy unreadable: $out" >&2; exit 1; }
echo "DELIVERED $out"

shopt -s nullglob
junk=("$work")
# "$prefix"[-_.]* so ep1 never takes ep10.mp4 along
for f in "$dest/$prefix"[-_.]*; do [ "$f" = "$out" ] || junk+=("$f"); done
renders=("$HOME/Movies/museai/$prefix"*)
junk+=(${renders[@]+"${renders[@]}"})
media="$(cd "$(dirname "$0")/../../../.." && pwd)/data/media"
for m in "$media"/vid_*.mp4; do
  for f in ${renders[@]+"${renders[@]}"} "$work"/*.mp4 "$work"/*/*.mp4; do
    [ "$(stat -f%z "$m")" = "$(stat -f%z "$f")" ] && cmp -s "$m" "$f" && { junk+=("$m"); break; }
  done
done
for f in "${junk[@]}"; do echo "delete $f"; done
trash "${junk[@]}"
echo "LEFT ONLY $out"
