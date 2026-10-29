---
name: shot-history
description: Remember every place shot rendered through museai (subject, camera move, light, template, video) and, when a place is requested again, tell the user what was already shot and propose different views so no reel repeats an earlier one. Use before planning any place/travel video (scenic-drop-reel, zoominview, muse-video travel mode; shared steps 1 and 7 of muse-video "Format skills"), after delivering one, and for "what have we shot of X", "shot history", "avoid duplicate views".
---

# shot-history

Registry: `~/.config/museai/shots.json`, one entry per delivered video. Script: `scripts/shots.py` (paths relative to this folder).

## Before planning shots (every place video)
```bash
python3 scripts/shots.py check --place "Ilulissat Icefjord" --country Greenland
```
- `NEW PLACE` (exit 0) → plan as usual.
- `ALREADY SHOT` (exit 1) → it lists each earlier video with its shots. Then:
  1. Plan a fresh shot list: other subjects of the place first (other landmarks, details, viewpoints), and where a subject must come back (the iconic hook), a different angle, move, light or season. Prefer a different template too (`pick.py` already skips the last 5).
  2. **Notify the user before rendering** (renders cost muse time): a short table "shot before → new view" plus the planned template/light, and one question with buttons: use the new views (recommended) / change them / repeat anyway. Human away → `webex ask` with the same options.
  3. Render only after the answer.
- A country request also runs `--country-wide` to see which places of that country were already used.
- Fuzzy match: names share a non-generic word ("Ilulissat" matches "Ilulissat Icefjord"; "Lake Bled" does not match "Lake Como"). Glance at near misses with `shots.py list` when the place goes by several names (Kangia / Ilulissat).

## After delivery (FINAL)
Write the shots actually used, in reel order, to a JSON file and record them **before** `deliver.sh` trashes the work folder:
```bash
cat > /tmp/shots.json <<'EOF'
[{"subject": "fin-shaped iceberg above brash ice", "move": "slow push-in", "light": "Arctic summer sun"}]
EOF
python3 scripts/shots.py record --place "Ilulissat Icefjord" --country Greenland \
  --skill scenic-drop-reel --template winter-wonder --video ~/Desktop/reel-ilulissat.mp4 --shots /tmp/shots.json
```
`subject` = what is in frame in a few words (the brief's subject, not the whole prompt). Record only delivered videos; a rejected preview is not a used view.
