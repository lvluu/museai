#!/usr/bin/env bash
# Usage: deliver.sh final.mp4 work_dir [prefix]
# Copies the finished video to ~/Desktop (DEST=dir to change), checks the copy, then moves
# everything else made for it to the Trash: the work folder (raw clips, sheets, mouth strips,
# frame grabs, cues, words, prompts) and the ~/Movies/museai files whose name starts with
# prefix (default: the work folder's name, e.g. ep10). Trash, not rm: a mistake stays recoverable.
# The server's own copies in data/media/ are left alone (data/tasks.json points at them).
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
cp "$final" "$out"
cmp -s "$final" "$out" || { echo "copy differs: $out" >&2; exit 1; }
ffprobe -v error -show_entries format=duration -of csv=p=0 "$out" >/dev/null || { echo "copy unreadable: $out" >&2; exit 1; }
echo "DELIVERED $out"

junk=("$work")
shopt -s nullglob
for f in "$HOME/Movies/museai/$prefix"*; do junk+=("$f"); done
for f in "${junk[@]}"; do echo "trash $f"; done
trash "${junk[@]}"
