---
name: scenic-drop-reel
description: Make a short vertical travel reel of any country, region, city or single place from one of 20 templates picked at random - countdown drops, pin-and-flow, numbered top lists, coordinates intros, POV arrivals, golden-hour dissolves, FPV ramps, day-in-a-place and more - with aerial shots rendered through muse (muse-video), cut on the beat of an AI track generated for that template (catchy, with sung lyrics when ACE-Step is installed), and assembled with ffmpeg. Use when the user asks for a "travel reel", "drop reel", "countdown reel", "scenic reel", "beat-cut travel video", "video like the Switzerland/Italy one", or a destination montage of a place. Default for every travel or place video request (e.g. "generate for <place>", a place photo), unless the user asks for one continuous documentary shot.
---

# scenic-drop-reel

Paths are relative to this folder (`.claude/skills/scenic-drop-reel/`). Rendering rules, server, retries and delivery come from `../muse-video/SKILL.md` (travel mode); this skill adds the reel formats.

## Templates (`templates.json`)
20 templates; each fixes intro (countdown, pin pill 📍, big word, POV line, black title card, coordinates typewriter, plain title, none), beat pattern per shot, transitions, camera moves, light, grade, on-screen text and music (BPM, tags, lyrics with `{place}`). `python3 scripts/pick.py --list` shows them with the scopes/settings they fit. Country-only templates (`countdown-drop`, `top-numbered`, …) are skipped for a single place.

**Scenery styles** (`templates.json` `sceneries`, user rule 2026-10-28: same music and moves on every reel got boring): `--setting` picks one of that landscape's music styles (snow → icy nordic folk, coast → ukulele pop, city → city pop, …; the template keeps its lyrics, FPV and `local-flavour` keep their own music) and alternates the template's signature move/transition with the setting's own (snow: glides, rises, orbits with dissolves and dips; city: whips and flashes). Always pass the right `--setting`; add a style there, not in one reel, when a place needs a new sound.

**Use a random one for every new request** unless the user names a template or style. `pick.py` chooses among those that fit and skips the last 5 used (`~/.config/scenic-drop-reel/history.json`).

### Hook + calm pace (user rules, 2026-10-28)
- **The first 2 s decide whether viewers stay** (user rule 2026-10-29): shot 1 is the wow view (the iconic landmark, wildlife, the most dramatic light) from frame 0. Card intros (countdown, black-title, coords) no longer open on black: `compose.py` lays them over shot 1 on a dark scrim, for at most 4 beats (`pick.py` `HOOK_BEATS`). The music slice starts on the sung hook with the beat already going (`music.py` scores the first 3 s for voice + punch). Never open on a quiet establishing shot or a slow riser with nothing to look at.
- **Bold hook text gives the view context**: pass `--title` with a curiosity line (≤ ~40 characters) instead of the bare place name on `title`, `bigword`, `pov` and `black-title` templates: "The most surreal beach on Earth", "Wait until you see this water…", "Is this the bluest ice on Earth?". It must be true of the place. Never a format label ("Golden Hour reel", "Top 5 in X" alone, "15 seconds in …").
- **10-18 s and a seamless loop**: short reels get watched to the end and replayed. `pick.py` keeps every plan at 10-18 s (`MAX_REEL_S`, holds ≤ 4 s) and ends it with a reprise shot (`"reprise": 1`, nothing to render): `compose.py` replays clip 1's frames just before the hook's window, so the last frame flows straight into the first and the music ends on a beat with only a declick. Render shot 1 at its planned `duration` (it holds the reprise too); `warning: … too short for a seamless loop` → render shot 1 longer.
- **Never dizzy**: slow, level drone moves (`prompt/drone.txt`), no shot held under 1.6 s (2.4 s when the music is under 100 BPM; `pick.py` doubles the beat pattern), whips/zooms 0.4-0.5 s (`compose.py` `XF`). Svalbard Zoom Tunnel at 0.97 s per shot with 0.3 s zooms felt too fast to the user.
- **Pace follows view and music**: wide panoramas and detailed scenes hold longer than a simple subject; calm songs hold longer than dance tracks. Use `@start` / `--length` to give a big view more time when the plan is too even.
- **Singer sounds human**: `music.py` asks ACE for one natural lead singer in balance with the band (no duets, no negated words like "no autotune", which pulled the voice robotic), `ace_song.py` runs 100 steps at guidance 10 (15 gave a strained voice), and the mix is loudnorm'd to -14 LUFS without the old tanh drive, which made the voice harsh and loud over the band.

### Why the cuts feel smooth (measured on the Switzerland reference, keep for every template)
1. *Slow, even motion*: picture change per frame (ffmpeg `signalstats` YDIF) stays 3-9 and flat inside a shot. No speed-up, output at muse's native 24 fps (every frame once, no 24→30 judder); `compose.py` picks each shot's steadiest window near the template's `target` (`@auto`).
2. *Same composition*: subject centred, horizon in the upper third in every shot → the eye does not jump at the cut.
3. *Same light and grade* across shots (template `light` / `grade`; `day-in` changes light on purpose, morning → night).
4. Transitions follow the camera: a `whip` slides the way the outgoing shot moves, `rise` follows an upward move, `zoom` follows a push-in. Every cut or transition is centred on a beat.

## Steps
0. **Earlier shots**: `python3 ../shot-history/scripts/shots.py check --place "Positano" --country Italy`. `ALREADY SHOT` → follow `../shot-history/SKILL.md` (new views, notify the user before rendering).
1. **Pick**: `python3 scripts/pick.py --place "Positano" --scope place --setting coast --country italy > plan.json`
   - `--scope` = what the user named (country | region | city | place); `--setting` coast island mountain lake city oldtown nature desert snow; `--country` picks the local instruments for `local-flavour`; `--id` forces a template.
   - The plan lists per shot: beats, render `duration`, camera `move`, `light`, transition; plus `seconds`, `intro`, `text`, `music`, `fast`.
   - **Length is random** within 10-18 s: slow holds 12-18 s, mid and one-beat bursts 10-16/18 s; the shot count follows (at least 3 rendered shots + the reprise). A template's `"length": [min, max]` overrides the range; `--length 20` or `--n 6` forces it only when the user asks.
2. **Plan the shots** (`len(plan.shots)`): real, recognisable subjects of the place, each a different subject type, alternating wide/close, the most striking, instantly recognisable view FIRST (the hook), the second-best before the reprise. Write the hook text now (`--title`, see above). For a single place, shoot it from different angles/details (`one-place-angles`). For `number`/`label`/`time` text templates also write the per-shot labels.
3. **Render all shots at once**, each in its own background call:
   ```bash
   DURATION=<shot.duration> LIGHT="<shot.light>" scripts/shot "PLACE: Positano, Amalfi Coast, Italy: pastel houses stacked down the cliff to the beach. DRONE: <shot.move>, village centred." ~/Movies/museai/reel-<slug>/s1.mp4
   ```
   Add `FAST=1` when `plan.fast` is true (FPV templates). 9:16, `shot.duration` s (6-10, long enough for a held window), `prompt/drone.txt` with `{LIGHT}`/`{PACE}` filled in. Wait with `pgrep -f "bash scripts/shot"`. Upstream 502/503 → retry later.
4. **Music** (in parallel with the renders):
   ```bash
   uv run --no-project scripts/music.py --plan plan.json --out ~/Movies/museai/reel-<slug>/track.m4a
   ```
   Writes `track.m4a` exactly as long as the reel and `track.beats.json` (beat grid, drop). Card intros (countdown, black-title, coords) get a short filtered riser under the card on shot 1 that drops as the card clears.
5. **Check each shot** as in muse-video travel mode (`python3 ../muse-video/scripts/qa.py sN.mp4 --travel 0 sheetN.jpg`; judge only `smooth` and the sheet). Re-render only a shot with no clean window, a fake landmark or wrong weather.
   muse paints green forests and meadows on any mountain or fjord: Svalbard reel (2026-10-28) got pine forest on the peaks shot and around the Seed Vault. For treeless places (Arctic, Iceland highlands, deserts) write it into every brief: "NO trees, NO forest, NO bushes, NO green meadows anywhere; only bare rock, scree, snow, ice and brownish tundra" - the re-render held it.
   muse can return a shot with no audio track (Reynisfjara reel s2, 2026-10-28); the reel's music replaces clip audio, so qa.py reports `sound`/`noise` as `skip no audio stream` for it instead of failing.
6. **Compose**:
   ```bash
   uv run --no-project --python 3.12 --with pillow --with fonttools python scripts/compose.py \
     --plan plan.json --place "Positano" [--title "Is this the prettiest cliff town?"] [--flag 🇮🇹] \
     [--labels "A|B|…"] [--coords "40.63° N  14.48° E"] --music track.m4a --out reel-<slug>.mp4 s1.mp4 s2.mp4@2.0 s3.mp4 …
   ```
   One clip per rendered shot; the reprise needs none. `--plan` cuts each shot on its planned beats (the template's pattern only when no plan is passed). `clip@2.0` forces a window start; default `@auto` (for shot 1 it picks a window long enough for the reprise in front of it). Warning `moves fast even at its calmest` → re-render slower. Prints cut times, transitions and the windows used. Without a beat file pass `--bpm` (and `--drop`).
7. **Verify**: contact sheet (`ffmpeg -i reel.mp4 -vf "fps=2,scale=180:-1,tile=8x4" -frames:v 1 sheet.png`): frame 0 already shows the view with readable hook text, every shot sunny/sharp/no muse text, transitions on beats, reel length ≈ music length (10-18 s), last frame continues into the first (`ffmpeg -sseof -0.05 -i reel.mp4 -frames:v 1 last.png` vs the first frame).
8. **Deliver** with `../muse-video/scripts/deliver.sh` (preview first, `FINAL=1` after the user accepts; one video on the Desktop, with its thumbnails: make them with `../thumbnail/SKILL.md`, `--title "<PLACE>"`, and pass `THUMB_DIR=`). Always pass per-platform posting captions with `CAPTIONS_FILE=captions.json`, written with `../social-captions/SKILL.md` (one caption per platform, each checked by its `captions.py`). Every hook is a scroll-stopping first line (curiosity, surprise or a bold claim: "This beach looks fake… but it's real", "Nobody told me Italy looked like this", "POV: you finally made it to …"; never the reel length or "X in N seconds", which reads like a label); the YouTube title is a scannable curiosity question or claim under 50 characters ("Is this the bluest ice on Earth? 🧊"), never a format label like "Golden Hour reel", then a line naming the place and listing the places shown, the platform's call to action and its hashtag count. Without it, the reel lands on the dashboard's "Ready to post" queue with an empty caption (reel-it and reel-switzerland, 2026-10-28). Compose to `reel-<slug>.mp4`, not `reel.mp4`: deliver.sh keeps the file name, and Ilulissat landed on the Desktop as a bare `reel.mp4` (2026-10-29). Before `FINAL=1` (it trashes the work folder), record the delivered shots with `../shot-history/scripts/shots.py record` so the next request for this place gets new views.

## Music engines
- **ace** (default when installed): ACE-Step sings the template's lyrics (Apache-2.0, ok for commercial posts). Install once (~8 GB, needs the user's OK):
  ```bash
  git clone --depth 1 https://github.com/ace-step/ACE-Step ~/.local/share/ace-step/repo
  uv venv --python 3.11 ~/.local/share/ace-step/venv
  uv pip install --python ~/.local/share/ace-step/venv/bin/python -e ~/.local/share/ace-step/repo
  ```
  `scripts/ace_song.py` runs inside that venv; weights (~7.7 GB) download on first use - set `HF_HUB_DISABLE_XET=1` if the big files sit at 0 B (2026-10-28: Xet hung, plain HTTP took 6 min). A 40 s song renders in ~2 min on an M1 Pro (model load 23 s). ACE ignores the BPM tag (asked 88, got 79). music.py never time-stretches an ACE song: the phase-vocoder stretch (Kirkjufell reel, 134→108 BPM) made the singer sound pitched and robotic, and the user wants a normal voice. The song keeps its own tempo (half/double-time nearest the template's BPM) and `track.beats.json` follows it, so compose.py cuts on the song's real beats; the reel runs a little shorter or longer than `plan.seconds`. The tags also ask for a natural unprocessed voice, no autotune. MusicGen (instrumental) is still stretched to the template BPM. Listen to the cut before composing: the slice is picked for groove + voice-band harmonics, but only the ear can tell the hook is in it.
- One ACE render per machine: `music.py` holds `~/.local/share/ace-step/render.lock` while ACE runs, so a second reel (another session) waits instead of sharing the GPU (two at once: model load 40 → 285 s, 100+ s per step). Never `pkill` ACE: the process may belong to another session.
- **musicgen** (fallback, instrumental): MusicGen medium, ~10 min per track on Apple silicon, first run ~8 GB. Weights CC-BY-NC 4.0: personal posts only - say so when the user wants to monetise.
- `--raw x.raw.wav` re-shapes a saved render; `--seed` for another take. Check the spectrogram (`ffmpeg -i t.m4a -lavfi showspectrumpic=s=1200x300 s.png`): quiet riser, clean beat at the drop.
- `assets/music-default.m4a` (+ `.beats.json`, 100 BPM, drop 3.233 s) is the Italy track, for quick tests. The reference reel's own audio stays out of the repo; a user-supplied track goes in with `--music file --bpm N --drop T`.

## Maintaining this skill
Same rules as `../muse-video/SKILL.md` "Maintaining this skill": record lessons proven by a render (prompt wording that held a camera move, transitions that looked wrong, shots muse cannot do); add or tune templates in `templates.json`, not in single reels.
