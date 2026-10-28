---
name: scenic-drop-reel
description: Make an 11.6 s vertical scenery reel in the "COUNTRY 🇨🇭 3-2-1" style - black countdown card over a rising track, then on the beat drop 7 sunny aerial drone shots of real landmarks hard-cut every 1.2 s (2 beats at 100 BPM) to the bundled music. Shots render through muse (muse-video), the reel is assembled with ffmpeg. Use when the user asks for a "drop reel", "countdown reel", "scenic reel", "beat-cut travel reel", "video like the Switzerland one", or a fast destination montage of a country/region/city with this music.
---

# scenic-drop-reel

Reference: a Switzerland reel (720x1280, 11.63 s). Paths are relative to this folder (`.claude/skills/scenic-drop-reel/`). Rendering rules, server, retries and delivery come from `../muse-video/SKILL.md` (travel mode); this skill only adds the format.

## Format (fixed by the music: 100 BPM, drop at 3.233 s)
| time | picture | music |
|---|---|---|
| 0 - 3.233 s | black card, bold white serif `TITLE 🇨🇭` at 28 % height, countdown `3` (0-1 s), `2` (1-2 s), `1` (2 s-drop) below it | swelling riser, fading |
| 3.233 s | **beat drop** → hard cut to shot 1 | full beat starts |
| +1.2 s each | hard cut to next shot (7 shots, ends 11.633 s) | cut lands on every 2nd beat |

- Cuts: plain one-frame hard cuts on the beat. No crossfades, whip pans, zoom transitions or text after the card.
- **Why the reference's cuts feel smooth** (measured frame by frame): not an effect, but three matches across every cut:
  1. *Slow, even motion*: picture change per frame (ffmpeg `signalstats` YDIF) stays 3-9 at 30 fps and flat inside a shot. Ours at 1.25x speed-up was 12-13 → jerky. So: no speed-up, output at muse's native 24 fps (every frame shown once, no 24→30 duplication judder), `drone.txt` asks for a slow constant glide, and `reel.py` picks each shot's calmest, most even 1.2 s (`@auto`).
  2. *Same composition*: landmark dead centre, horizon in the upper third in every shot → the eye does not jump at the cut.
  3. *Same light and grade*: all sunny midday, one grade over all shots.
- Movement inside each shot: one slow, steady drone move already under way (push-in, lateral glide, orbit or rise). Variety comes from the cut, not from camera tricks.
- Look: bright sunny summer, deep blue sky, saturated greens and turquoise water, crisp detail. `reel.py` adds the punchy grade (saturation 1.22, contrast 1.06, light sharpen).

## Steps
1. **Plan 7 shots** for the place the user names: real, recognisable landmarks, each a different subject type and alternating wide/close, ending on the most iconic view. Switzerland reference order: Lauterbrunnen waterfall cliff → lakeside château on turquoise Lake Brienz → Thun Castle → hilltop church + castle → Oberhofen Castle on Lake Thun → villa on a green island (Iseltwald) → Lauterbrunnen valley with a train. Per shot write: landmark + what is really there, drone move, framing. Show the list to the user only if the place is ambiguous; otherwise go.
2. **Render all 7 shots at once**, each in its own background call (independent, so they share all free accounts):
   ```bash
   scripts/shot "PLACE: Thun Castle, Switzerland: white keep with four red-roofed corner turrets on a green hill above the old town, Lake Thun and snowy Bernese Alps behind. DRONE: slow push-in toward the keep at turret height, castle centred." ~/Movies/museai/reel-ch/s3.mp4
   ```
   9:16, 6 s, `STYLE=travel` + `prompt/drone.txt`. Work folder `~/Movies/museai/reel-<slug>/`, files `s1.mp4`..`s7.mp4`.
3. **Check each shot** (contact sheet + smooth): `motion` always fails TIME-LAPSE on a moving drone (Switzerland 2026-10-27: 4-15 % of width/s on good shots) and `noise` is moot (music replaced), so judge only `smooth` and the sheet; a late surge in `motion` (e.g. 5 → 30 %/s in the last 50 %) means the drone speeds up there, so take the window earlier. `python3 ../muse-video/scripts/qa.py sN.mp4 --travel 0 sheetN.jpg`. Only the 1.2 s window used matters: a shot that fails late (cut, camera turn, warp after 3 s) is fine if a clean 1.2 s is earlier - pick it with `@start`. Re-render only a shot with no clean 1.2 s window, a fake/warped landmark, or grey weather.
4. **Assemble**:
   ```bash
   uv run --no-project --python 3.12 --with pillow --with fonttools python scripts/reel.py \
     --title SWITZERLAND --flag 🇨🇭 --out reel-ch.mp4 s1.mp4 s2.mp4@2.0 s3.mp4 s4.mp4 s5.mp4 s6.mp4 s7.mp4
   ```
   - Each clip's window defaults to `@auto`: the 1.2 s whose motion is closest to `--target 7` YDIF/frame with the least variation and no jump. `clip@2.0` forces a start second. A warning `moves fast even at its calmest` → re-render that shot slower.
   - Output fps = clip fps (24); cuts sit on an absolute frame grid (`round(t*fps)`), so they stay on the beat without drift. Do not add `--speed`/`--fps 30` back: both made the Switzerland reel jerky.
   - `--title` in caps, local name the audience knows (`SWITZERLAND`, `VIETNAM`, `BALI`); `--flag` any emoji with a bitmap in Apple Color Emoji (flags work).
   - Prints the cut times and the window used per shot.
5. **Verify**: grab a frame from each shot (`3.8 + 1.2*k` s) and the card at 0.5 s; every shot sunny, sharp, no text, landmark recognisable; length 11.63 s; cuts at 3.233, 4.433 … 10.433 (`ffmpeg -vf "select='gt(scene,0.1)',metadata=print"`).
6. **Deliver** with `../muse-video/scripts/deliver.sh` (preview first, `FINAL=1` after the user accepts; one file on the Desktop).

## Music
Default: `assets/music-default.m4a`, an AI track made by `scripts/music.py` (first used for the Italy reel, 11.9 s). A new track per reel keeps feeds from repeating:
```bash
uv run --no-project scripts/music.py "uplifting summer deep house, bright plucks, warm bass, crisp claps" --out assets/music-<slug>.m4a
```
It renders with MusicGen (~10 min on Apple silicon, first run downloads ~8 GB), stretches to 100 BPM and builds the 3.233 s filtered riser + drop; check its spectrogram (`ffmpeg -i t.m4a -lavfi showspectrumpic=s=1200x300 s.png`): quiet riser, clean beat at 3.233 s. `--raw x.raw.wav` re-shapes a saved render without regenerating; `--seed` for another take. MusicGen weights are CC-BY-NC 4.0: personal posts fine, not paid/commercial use - say so when the user wants to monetise.

The original reference reel's audio is someone else's track and stays out of the repo; if the user supplies it, pass it with `--music file`. Any other track: `--music file --intro <drop time> --shot <120/BPM>`; shot count follows from the track length.

## Maintaining this skill
Same rules as `../muse-video/SKILL.md` "Maintaining this skill": record lessons proven by a render (prompt wording that held the drone move, shots muse cannot do), branch → PR → merge on autopilot.
