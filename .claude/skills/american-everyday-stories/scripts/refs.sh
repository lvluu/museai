#!/usr/bin/env bash
# Usage: scripts/refs.sh KEY OUT_DIR -> OUT_DIR/KEY_1.png, KEY_2.png (two waist-up candidates)
# Sends `episode.py still KEY` to museai's /v1/images/generations; the API key is read here and
# never printed. Run the six characters in parallel (one background call each): ~5-15 min.
set -euo pipefail
key=$1 out=$2
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$out"
API=$(cat "${MUSEAI_HOME:-$HOME/Work/museai}/data/api_key")
body=$(python3 "$here/episode.py" still "$key" "$out")
for i in 1 2 3; do
  if curl -sf -X POST "${MUSEAI_BASE:-http://127.0.0.1:18610}/v1/images/generations" \
      -H "Authorization: Bearer $API" -H "Content-Type: application/json" -d "$body" > "$out/$key.json"; then
    break
  fi
  echo "$key: submit $i failed, retrying" >&2; sleep 30
done
python3 - "$out" "$key" <<'EOF'
import base64, json, sys
out, key = sys.argv[1:]
for i, x in enumerate(json.load(open(f"{out}/{key}.json"))["data"], 1):
    open(f"{out}/{key}_{i}.png", "wb").write(base64.b64decode(x["b64_json"]))
    print(f"{out}/{key}_{i}.png")
EOF
rm "$out/$key.json"
