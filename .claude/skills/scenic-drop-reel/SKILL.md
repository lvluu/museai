---
name: scenic-drop-reel
description: Make an 11.6 s vertical scenery reel in the "COUNTRY 🇨🇭 3-2-1" style - black countdown card over a rising track, then on the beat drop 7 sunny aerial drone shots of real landmarks hard-cut every 1.2 s (2 beats at 100 BPM) to the bundled music. Shots render through muse (muse-video), the reel is assembled with ffmpeg. Use when the user asks for a "drop reel", "countdown reel", "scenic reel", "beat-cut travel reel", "video like the Switzerland one", or a fast destination montage of a country/region/city with this music.
---

# scenic-drop-reel

Reference: a Switzerland reel (720x1280, 11.63 s). Paths are relative to this folder (`.claude/skills/scenic-drop-reel/`). Rendering rules, server, retries and delivery come from `../muse-video/SKILL.md` (travel mode); this skill only adds the format.

## Format (fixed by the music, `assets/drop-100bpm.m4a`)
| time | picture | music |
|---|---|---|
| 0 - 3.233 s | black card, bold white serif `TITLE 🇨🇭` at 28 % height, countdown `3` (0-1 s), `2` (1-2 s), `1` (2 s-drop) below it | swelling riser, fading |
| 3.233 s | **beat drop** → hard cut to shot 1 | full beat starts |
| +1.2 s each | hard cut to next shot (7 shots, ends 11.633 s) | cut lands on every 2nd beat |

- Cuts: plain hard cuts on the beat. No crossfades, whip pans, zoom transitions or text after the card.
- Movement inside each shot: one smooth, steady drone move already under way (slow push-in, lateral glide, orbit or rise), landmark large and centred. Variety comes from the cut, not from camera tricks.
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
   - `clip@start`: second where its 1.2 s window starts (default 1.5 s, past muse's start settle).
   - `--speed 1.3` if the drone moves look sluggish in 1.2 s (reference moves are clearly visible within one shot).
   - `--title` in caps, local name the audience knows (`SWITZERLAND`, `VIETNAM`, `BALI`); `--flag` any emoji with a bitmap in Apple Color Emoji (flags work).
   - Prints the cut times and the window used per shot.
5. **Verify**: grab a frame from each shot (`3.8 + 1.2*k` s) and the card at 0.5 s; every shot sunny, sharp, no text, landmark recognisable; length 11.63 s; cuts at 3.233, 4.433 … 10.433 (`ffmpeg -vf "select='gt(scene,0.1)',metadata=print"`).
6. **Deliver** with `../muse-video/scripts/deliver.sh` (preview first, `FINAL=1` after the user accepts; one file on the Desktop).

## Music
`assets/drop-100bpm.m4a` is the audio of the user's reference reel (11.0 s; the last shot runs 0.6 s past it with a short fade). It is someone else's track: fine for personal use, may be muted or claimed on Instagram/TikTok - say so when the user wants to post. Another track: `--music file --intro <drop time> --shot <60/BPM*2>`; shot count follows from the track length.

## Maintaining this skill
Same rules as `../muse-video/SKILL.md` "Maintaining this skill": record lessons proven by a render (prompt wording that held the drone move, shots muse cannot do), branch → PR → merge on autopilot.
