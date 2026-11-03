#!/usr/bin/env bash
# Usage: scripts/stills.sh WORK [name ...]  -> WORK/stills/<name>_1.png, <name>_2.png per still JSON
# Sends each WORK/stills/<name>.json to museai /v1/images/generations in parallel; the API key is read
# here and never printed. Pick a take per still and copy it to WORK/stills/<name>.png (render.sh uses it).
set -uo pipefail
work=$1; shift
API=$(cat "${MUSEAI_HOME:-$HOME/Work/museai}/data/api_key")
names=("$@"); [ ${#names[@]} -gt 0 ] || names=($(cd "$work/stills" && ls *.json | sed 's/\.json$//'))
for n in "${names[@]}"; do
  (
    for i in 1 2 3; do
      curl -sf -m 900 -X POST "${MUSEAI_BASE:-http://127.0.0.1:18610}/v1/images/generations" \
        -H "Authorization: Bearer $API" -H "Content-Type: application/json" \
        -d @"$work/stills/$n.json" > "$work/stills/$n.res" && break
      echo "$n: submit $i failed, retrying" >&2; sleep 30
    done
    python3 - "$work/stills" "$n" <<'EOF'
import base64, json, sys
d, n = sys.argv[1:]
for i, x in enumerate(json.load(open(f"{d}/{n}.res"))["data"], 1):
    open(f"{d}/{n}_{i}.png", "wb").write(base64.b64decode(x["b64_json"]))
    print(f"{d}/{n}_{i}.png")
EOF
    rm -f "$work/stills/$n.res"
  ) &
done
wait
