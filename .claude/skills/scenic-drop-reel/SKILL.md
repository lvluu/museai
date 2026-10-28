---
name: scenic-drop-reel
description: Make a short vertical travel reel of any country, region, city or single place from one of 20 templates picked at random - countdown drops, pin-and-flow, numbered top lists, coordinates intros, POV arrivals, golden-hour dissolves, FPV ramps, day-in-a-place and more - with aerial shots rendered through muse (muse-video), cut on the beat of an AI track generated for that template (catchy, with sung lyrics when ACE-Step is installed), and assembled with ffmpeg. Use when the user asks for a "travel reel", "drop reel", "countdown reel", "scenic reel", "beat-cut travel video", "video like the Switzerland/Italy one", or a destination montage of a place.
---

# scenic-drop-reel

Paths are relative to this folder (`.claude/skills/scenic-drop-reel/`). Rendering rules, server, retries and delivery come from `../muse-video/SKILL.md` (travel mode); this skill adds the reel formats.

## Templates (`templates.json`)
20 templates; each fixes intro (countdown, pin pill 📍, big word, POV line, black title card, coordinates typewriter, plain title, none), beat pattern per shot, transitions, camera moves, light, grade, on-screen text and music (BPM, tags, lyrics with `{place}`). `python3 scripts/pick.py --list` shows them with the scopes/settings they fit. Country-only templates (`countdown-drop`, `top-numbered`, …) are skipped for a single place.

**Use a random one for every new request** unless the user names a template or style. `pick.py` chooses among those that fit and skips the last 5 used (`~/.config/scenic-drop-reel/history.json`).

### Why the cuts feel smooth (measured on the Switzerland reference, keep for every template)
1. *Slow, even motion*: picture change per frame (ffmpeg `signalstats` YDIF) stays 3-9 and flat inside a shot. No speed-up, output at muse's native 24 fps (every frame once, no 24→30 judder); `compose.py` picks each shot's steadiest window near the template's `target` (`@auto`).
2. *Same composition*: subject centred, horizon in the upper third in every shot → the eye does not jump at the cut.
3. *Same light and grade* across shots (template `light` / `grade`; `day-in` changes light on purpose, morning → night).
4. Transitions follow the camera: a `whip` slides the way the outgoing shot moves, `rise` follows an upward move, `zoom` follows a push-in. Every cut or transition is centred on a beat.

## Steps
1. **Pick**: `python3 scripts/pick.py --place "Positano" --scope place --setting coast --country italy > plan.json`
   - `--scope` = what the user named (country | region | city | place); `--setting` coast island mountain lake city oldtown nature desert snow; `--country` picks the local instruments for `local-flavour`; `--id` forces a template.
   - The plan lists per shot: beats, render `duration`, camera `move`, `light`, transition; plus `seconds`, `intro`, `text`, `music`, `fast`.
   - **Length is random**, not a fixed 14-15 s: each reel draws a length suited to the template's pace (slow holds 12-30 s and may hold each shot 6-8 beats, mid 10-24 s, one-beat bursts 8-18 s, capped by 12 shots and 26 s without ACE-Step); the shot count follows. A template's `"length": [min, max]` overrides the range; `--length 20` or `--n 6` forces it when the user asks.
2. **Plan the shots** (`len(plan.shots)`): real, recognisable subjects of the place, each a different subject type, alternating wide/close, best view last. For a single place, shoot it from different angles/details (`one-place-angles`). For `number`/`label`/`time` text templates also write the per-shot labels.
3. **Render all shots at once**, each in its own background call:
   ```bash
   DURATION=<shot.duration> LIGHT="<shot.light>" scripts/shot "PLACE: Positano, Amalfi Coast, Italy: pastel houses stacked down the cliff to the beach. DRONE: <shot.move>, village centred." ~/Movies/museai/reel-<slug>/s1.mp4
   ```
   Add `FAST=1` when `plan.fast` is true (FPV templates). 9:16, `shot.duration` s (6-10, long enough for a held window), `prompt/drone.txt` with `{LIGHT}`/`{PACE}` filled in. Wait with `pgrep -f "bash scripts/shot"`. Upstream 502/503 → retry later.
4. **Music** (in parallel with the renders):
   ```bash
   uv run --no-project scripts/music.py --plan plan.json --out ~/Movies/museai/reel-<slug>/track.m4a
   ```
   Writes `track.m4a` exactly as long as the reel and `track.beats.json` (beat grid, drop). Card intros (countdown, black-title, coords) get a filtered riser that drops on shot 1.
5. **Check each shot** as in muse-video travel mode (`python3 ../muse-video/scripts/qa.py sN.mp4 --travel 0 sheetN.jpg`; judge only `smooth` and the sheet). Re-render only a shot with no clean window, a fake landmark or wrong weather.
6. **Compose**:
   ```bash
   uv run --no-project --python 3.12 --with pillow --with fonttools python scripts/compose.py \
     --plan plan.json --place "Positano" [--flag 🇮🇹] [--labels "A|B|…"] [--coords "40.63° N  14.48° E"] \
     --music track.m4a --out reel.mp4 s1.mp4 s2.mp4@2.0 s3.mp4 …
   ```
   `--plan` cuts each shot on its planned beats (the template's pattern only when no plan is passed). `clip@2.0` forces a window start; default `@auto`. Warning `moves fast even at its calmest` → re-render slower. Prints cut times, transitions and the windows used. Without a beat file pass `--bpm` (and `--drop`).
7. **Verify**: contact sheet (`ffmpeg -i reel.mp4 -vf "fps=2,scale=180:-1,tile=8x4" -frames:v 1 sheet.png`): intro text readable, every shot sunny/sharp/no muse text, transitions on beats, reel length ≈ music length.
8. **Deliver** with `../muse-video/scripts/deliver.sh` (preview first, `FINAL=1` after the user accepts; one file on the Desktop). Always pass a posting caption with `CAPTION_FILE=caption.txt`: a hook naming the place and the reel length, one line listing the places shown, a short call to action, then 3-6 hashtags. Without it, the reel lands on the dashboard's "Ready to post" queue with an empty caption (reel-it and reel-switzerland, 2026-10-28).

## Music engines
- **ace** (default when installed): ACE-Step sings the template's lyrics (Apache-2.0, ok for commercial posts). Install once (~8 GB, needs the user's OK):
  ```bash
  git clone --depth 1 https://github.com/ace-step/ACE-Step ~/.local/share/ace-step/repo
  uv venv --python 3.11 ~/.local/share/ace-step/venv
  uv pip install --python ~/.local/share/ace-step/venv/bin/python -e ~/.local/share/ace-step/repo
  ```
  `scripts/ace_song.py` runs inside that venv; weights (~7.7 GB) download on first use - set `HF_HUB_DISABLE_XET=1` if the big files sit at 0 B (2026-10-28: Xet hung, plain HTTP took 6 min). A 40 s song renders in ~2 min on an M1 Pro (model load 23 s). ACE ignores the BPM tag (asked 88, got 79), music.py stretches it. Listen to the cut before composing: the slice is picked for groove + voice-band harmonics, but only the ear can tell the hook is in it.
- **musicgen** (fallback, instrumental): MusicGen medium, ~10 min per track on Apple silicon, first run ~8 GB. Weights CC-BY-NC 4.0: personal posts only - say so when the user wants to monetise.
- `--raw x.raw.wav` re-shapes a saved render; `--seed` for another take. Check the spectrogram (`ffmpeg -i t.m4a -lavfi showspectrumpic=s=1200x300 s.png`): quiet riser, clean beat at the drop.
- `assets/music-default.m4a` (+ `.beats.json`, 100 BPM, drop 3.233 s) is the Italy track, for quick tests. The reference reel's own audio stays out of the repo; a user-supplied track goes in with `--music file --bpm N --drop T`.

## Maintaining this skill
Same rules as `../muse-video/SKILL.md` "Maintaining this skill": record lessons proven by a render (prompt wording that held a camera move, transitions that looked wrong, shots muse cannot do); add or tune templates in `templates.json`, not in single reels.
