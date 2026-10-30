---
name: chinese-scenery-style
description: Make a cinematic, photoreal vertical travel story of any place in China (Shangri-La, Guilin, Zhangjiajie, Jiuzhai, Suzhou, Beijing, Xinjiang, Yunnan, ...) - the recurring traveller in a muted red jacket journeys through 3-4 real locations of the place, opening on a spectacular wow shot with the hook "This is China. Welcome to <place>.", wide unhurried scenery, small lived-in details (tea, carved doors, streets), and a final lingering panorama, all cut on the bars of a catchy song - the user's reference track cut at its catchiest window by music analysis, or an AI song (ACE-Step) in the region's Chinese style (Tibetan plateau, karst, Jiangnan, imperial, Silk Road, south, city). Use for every video request about a place in China ("make a video of Guilin", "Shangri-La travel video", "build China scenery", "video like the Shangri-La one", a photo of a Chinese place), unless the user asks for a beat-cut drone montage (scenic-drop-reel) or a person's reaction reveal (zoominview). Takes the shared brief (muse-video "Format skills"); files are named scenic-china-<slug>.
---

# chinese-scenery-style

Paths are relative to this folder (`.claude/skills/chinese-scenery-style/`). Server, retries, shot history, QA and delivery come from `../muse-video/SKILL.md` ("Format skills" shared steps, "Travel videos" lessons); the AI music engine is `../muse-video/scripts/music.py`; the traveller is the recurring character of `../zoominview/` ("The character"). Work folder `~/Movies/museai/scenic-china-<slug>/`, final `scenic-china-<slug>.mp4` (the `scenic` prefix routes it to the Travel channel).

## The style (what every China video keeps)
Reference: the user's Shangri-La brief (2026-10-30), `stories/shangri-la.json`.
1. **Hook in the first 3 s**: shot 1 is the most spectacular view of the place from frame 0 (no logo, no fade from black), the traveller close in the foreground, the camera revealing the landscape smoothly; the music's swell plays under it. Elegant text over it: `This is China.` / `Welcome to <place>.` (`styles.json` `hook_text`; a story may set its own `hook_text`, still true of the place). No other text in the video.
2. **A journey, not a montage**: 3-4 real locations of the place in a natural order, each introduced by a wide establishing shot, then the traveller in it, then one meaningful detail. Location changes and time passing are 0.6 s dissolves; shots inside a location are hard cuts on the downbeat. The day moves forward (day → golden → dusk → blue hour) and ends on her looking out, then a lingering wide view that gives the place the last moment.
3. **The traveller**: the recurring woman (face reference `../zoominview/assets/character/face.jpg`), muted red outdoor jacket, cream knit sweater, dark trousers, walking shoes, the same in every shot. Mostly from behind, side-on or medium-wide; never a face close-up; relaxed real walking, no posing, nodding, waving or talking. A shot of her hands names five fingers.
4. **Camera and pace**: mostly wide / medium-wide, one slow restrained move per shot (tracking, gentle pan, slow push-in, glide back), real-time motion. No orbiting, repeated drone shots, rapid montage, abrupt zooms. Every shot lasts whole bars of the song (1 bar ≈ 2 s at 120 BPM): views 3 bars, people 2, details 1.
5. **Real China**: real landmarks, architecture, terrain and vegetation; one season and weather for the whole story (`season` in the story); religious places from visitor paths, no staged rituals or worshippers up close; no readable signs, logos or watermarks (`prompt/china.txt`).
6. **Sound**: the song on top, catchy from the first second, soft during intimate moments, building to the final panorama; the clips' own location sound under it (breeze, water, footsteps, town). No narration, no dialogue.

## Music
Library: `~/.local/share/museai/music/chinese-scenery/` (outside the repo: audio stays out of git). `scripts/music_sections.py list` shows it.
- **A track the user gives** (file or video): `uv run --no-project scripts/music_sections.py add <file> --id <id> --tags "<genre, instruments, mood>"`, then add it to the region's `music` list in `styles.json` as `{"id": ..., "track": "<id>"}`. It prints the section map: bars, loudness, catchy score (loudness + repetition + punch) and role (hook / build / soft / outro).
- **Cut the window**: `music_sections.py cut <id> --seconds 40-60 --out <work>/track.m4a`. It opens on the one-bar pickup before a loud hook (the swell under the reveal) or on the hook itself, prefers a soft part past the first third (tea / street moments) and windows that run into the song's real ending instead of a fade. `--start S` forces it; read `show` and pick by ear when the story needs another arc. The window length decides the video length (story-driven: 40-60 s for 3-4 locations).
- **No track yet, or the user wants new music**: generate one in the region's style (`styles.json` `regions.<region>.music`: Tibetan plateau, karst, Jiangnan water town, imperial, Silk Road, south, city; sung Chinese lyrics with `{place_zh}` or instrumental):
  ```bash
  uv run --no-project ../muse-video/scripts/music.py --style "<tags>" --bpm <bpm> --body-beats 128 \
    [--lyrics "<lyrics with {place_zh} filled in>"] --out <work>/song.m4a
  uv run --no-project scripts/music_sections.py add <work>/song.m4a --id <region>-<slug> --tags "<tags>"
  ```
  then cut it like a user track. ACE-Step sings (installed); MusicGen (fallback) is instrumental only. Rotate: do not reuse the same generated song for two places.
- Shangri-La (2026-10-30): the user's song (`shangri-la-ref`, 123 BPM, 182 s): window 126.71-182.29 s = pickup swell → loud chorus (lake, grassland, monastery) → soft bar at 35 s (teahouse) → big build at 41 s (dusk view) → the song's real ending under the final panorama.

## Steps
0. **Earlier shots**: `python3 ../shot-history/scripts/shots.py check --place "<place>" --country China` (shared step 1); `ALREADY SHOT` → new locations / angles, ask before rendering.
1. **Story** (`stories/<slug>.json`, copy `shangri-la.json`): `place`, `place_zh`, `where` (place, prefecture, province, altitude), `region` (a `styles.json` region), `music` (a region music id), `season` (one coherent season, the real vegetation, water level, sky), and `shots` in order, each with `bars` (last shot `0` = rest of the track), `person` (`none` `back` `walk` `side` `hands`), `light` (`day` `golden` `dusk` `blue-hour` `mist` `overcast`), `view` (the real landmark and what is really there, named), `action`, `move`, `ambience`, `in` (`dissolve` for a new location or time passing). Follow the style above: wow hook, 3-4 locations, establishing → traveller → detail, intimate shots on the song's soft part, final look-out + lingering wide.
2. **Music**: cut the window (above) into the work folder.
3. **Plan**: `python3 scripts/plan.py stories/<slug>.json --work ~/Movies/museai/scenic-china-<slug>` → `plan.json` (each shot's start/end on the song's bars, render length) and `shot<N>.txt` prompts (place, shot, traveller with face reference, `prompt/china.txt`, the travel block without its music line). It fails when a shot gets under 1.6 s: fewer bars or a longer window.
4. **Render** all shots at once (background): `scripts/render ~/Movies/museai/scenic-china-<slug>/plan.json [N ...]`. Upstream 502/503 or a failed submit → re-run the failed numbers later.
5. **Check each shot** (shared step 5): `python3 ../muse-video/scripts/qa.py shotN.mp4 --travel 0 sheetN.jpg` plus the sheet: the real landmark (golden roofs, real street, real lake), the same jacket and face, five-finger hands, no text, no invented buildings, the planned light. Re-render only failing shots (`render plan.json 3 7`).
6. **Compose**: `uv run --no-project scripts/compose.py ~/Movies/museai/scenic-china-<slug>/plan.json [--at N=S]` → `scenic-china-<slug>.mp4`, then `qa.py <final> --travel <cuts>` and a contact sheet (`ffmpeg -i <final> -vf "fps=1,scale=180:-1,tile=8x7" -frames:v 1 sheet.png`): frame 0 shows the view with the readable hook text, every cut on a downbeat, the last view lingers.
7. **Deliver** (shared step 7): thumbnail (`../thumbnail/`, style `travel`, the hook shot or the final panorama, `--title "<PLACE>"`, `--sub "China 🇨🇳"`), captions (`../social-captions/`, first line a hook such as "This is China 🇨🇳 Welcome to Shangri-La"), shot-history record (`--skill chinese-scenery-style --template <region>`) before `FINAL=1`.

## Lessons (Shangri-La, 2026-10-30)
- `qa.py` `motion` TIME-LAPSE on tracking / pans / push-ins is the planned move: judge from the sheet. Clip `sound` FAIL does not matter (the song replaces it).
- A `hands` shot drifts to her face (a duplicate of the window seat) unless the story locks it: "tight close-up, top edge of the frame stays below her chest, face, hair and shoulders never appear", move "locked, does not move, tilt or pull back".
- `internal_error` / failed submit on a few shots of a parallel batch: re-run only those numbers; they pass on the second try.
- muse adds a backpack and draws golden grass as barley; name "no backpack" / "wild meadow grass" in the story when it matters.

## Maintaining this skill
Record lessons proven by a render here (prompt wording that held the jacket or a landmark, shots muse cannot do); add regions, music styles and tracks in `styles.json`, story patterns in `stories/`, never only in one video's prompts. Same PR flow as `../muse-video/SKILL.md` "Maintaining this skill".
