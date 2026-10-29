---
name: zoominview
description: Make a short vertical "wow reveal" reel of a place through museai - a real-looking traveller films a selfie, reacts to what they see (a hook picked per scenery: silent gasp, calm speechless awe, disbelieving laugh, sunglasses off, breathless arrival, wind gust, goosebumps, cold dawn), the camera moves the way their eyes look onto the view (pan along the cliff edge, pan onto a river/road leading line, tilt up at something towering, whip pan, hand off the lens, over the shoulder, over the crest, through the window), stops, then gently zooms in, with music that swells the moment the view opens - one of the two reference tracks or an AI track (felt piano, epic orchestral, dreamy pads, tropical chill, acoustic, synth glow, guzheng, nordic choir, gamelan, mediterranean guitar, oud, andean flute, lofi) chosen to suit the place - plus a caption hook line. Use for "zoominview", "zoom in view", "reaction reveal", "surprised person then the view", "video like the Madeira cliff one", "video like the Swiss valley one", or "zoominview <place>". Use instead of scenic-drop-reel (the default place reel) when the user wants a person's reaction and one continuous reveal rather than a beat-cut montage. Takes the shared brief (muse-video "Format skills"); files are named zoom-<slug>.
---

# zoominview

Paths are relative to this folder (`.claude/skills/zoominview/`). Server, retries, the brief, shot history, QA and delivery come from `../muse-video/SKILL.md` ("Format skills" shared steps); the music engine is `../muse-video/scripts/music.py` ("Music"). Name everything `zoom-<slug>`.

## The format (measured on the reference reel, 13.8 s, 9:16, one continuous shot, no cut)
| time | what | why it works |
|---|---|---|
| 0-4.5 s | selfie, front camera, golden light, wind in hair; the person stares past the camera off to ONE SIDE; behind them only sky and a grassy hilltop (the view is never behind them); mouth open, hand on forehead | the face is the hook: viewers stay to see what they see |
| 4.5-9 s | one continuous handheld pan the way the eyes look: the face slides out the opposite edge, the camera sweeps over the scrub on the hillside, along the cliff edge, and the view opens beyond it; music swells at ~7 s | the camera goes exactly where they stared: the payoff lands on the music |
| 9-13.8 s | level, slow push-in on the view | lets the eye settle on the beauty |

`swing-tilt` (~15 s): clip A = reaction + pan, clip B = one long optical zoom in on `--focus`. No pull-back: the camera only moves to the view, then zooms in.

Reference reel 2 (Swiss valley, 16.3 s, `glide-in` + `still-awe`, measured at 4 fps): 0-3 s calm speechless stare off to the LEFT, hand resting on top of the curly hair, forest slope and meadow behind (no gasp); 3-5 s one fast handheld pan LEFT past a tree and the meadow, up across the sky, then down onto a glacier river; 5.5-11 s the camera glides FORWARD low along the river at one calm constant speed toward a huge rocky peak; 11-12.5 s it eases to a wide view of the peak and its glacier with pines and the river in front; 12.5-16.3 s slow push-in, the peak ends filling the upper half. Music = the reel's own track (`assets/alps-ref.m4a`, whole 16.3 s, no loop): soft pulse, dip 6.5-8.8 s, big hit at 9.0 s mid-glide, swells at 11, 13 and 15.5 s. `glide-in` copies it with three clips: A 6 s (stare + pan, ends still on the line), B glides at one steady speed and eases to a stop at ~6 s (`render` keeps 6.2 s), C continues from B's last frame as a slow push-in with the water flowing (`render` keeps 4 s). Compose with `--reveal 9.0 --zoom 1.0` (C is the push-in; no digital zoom on top): the hit lands 3 s into the glide like the reference, and 6 + 6.2 + 4 = 16.2 s fits the 16.3 s track without a loop. `plan.json` `compose.cut` holds the trim points; `render` keeps the full takes as `b_full.mp4` / `c_full.mp4`.

## Not one fixed recipe
Each reel combines a **hook** (the reaction that stops the scroll), a **reveal** (the camera move), a **music** style and a **caption hook** line, each chosen to fit the scenery, light and country, and rotated so consecutive reels differ. The references show the quality bar, not the only look. What every combination keeps (the user's rules): the face stays up and uncovered, eyes on the view; the camera goes exactly where the eyes look; the move ends still on a WIDE, FAR view seen from where the person stands; then one gentle ~1.5x zoom in that stops and holds; never a zoom-out or pull-back.

| scenery | hooks that fit | reveals that fit | music |
|---|---|---|---|
| sea cliffs, coast | gasp, wind-hit, glasses-off, breathless-arrival | swing-tilt, whip-pan, over-shoulder | wow-ref, piano-swell, tropic-chill, local |
| valleys, rivers, alpine meadows | still-awe, goosebumps, disbelief-laugh | glide-in (long, ~16 s), river-line, swing-tilt | alps-ref, piano-swell, dream-pads |
| peaks, waterfalls, temples, towers | breathless-arrival, still-awe, gasp | look-up, crest-rise | epic-rise, east-strings, andes-flute |
| snow, dawn | cold-morning, goosebumps | crest-rise, river-line | dream-pads, nordic-choir |
| desert, canyon | glasses-off, breathless-arrival | swing-tilt, crest-rise, look-up | epic-rise, desert-oud |
| city, old town | glasses-off, disbelief-laugh | window-open, river-line (street), look-up | city-glow, lofi-glow, acoustic-glow, med-guitar |
Add new hooks, reveals, music and caption lines to `styles.json`, never only into one reel's prompt.

Reference music: reel 1 uses "Runaway" (the user supplies the full song; play it straight through, never loop a short excerpt). `assets/wow-ref.m4a` (13.8 s excerpt from the user's reel): mellow ambient, ~57 BPM, quiet under the reaction, dip 5-6.5 s, swell from 7.0 s. Audio files are gitignored: it stays local, personal posts only.

## The character (one recurring girl)
Every reel stars the same woman (user rule, 2026-10-29), so viewers recognise her across posts. She is an **original AI face** (`assets/character/face.jpg`, generated by muse from a text-only prompt, styled after the user's reference: layered hair with wispy bangs, cream knit; no glasses, user rule): fictional, no real person's likeness, so no portrait or copyright claim on the face. Never use a real person's photo (the user's own, a model's, a celebrity's) as the character: muse copies a face it is given. `styles.json` `character` holds her fixed look (`text`: young white European woman ~23, fair skin, faint freckles, hazel-green eyes, chestnut-brown layered hair with bangs, no glasses, soft rose lips) and the photo path. `plan.py` uses her by default and adds `person_image`; `scripts/render` attaches the photo to clip A with a FACE REFERENCE line ("not the first frame, not the location", same face, freckles and bangs in every frame), B shows nobody. Hooks that clash with her look go in `skip_hooks`. `--person "..."` or `--person random` for someone else.
Other travel videos (muse-video travel mode, scenic-drop-reel shots with a person) use her too: pass `IMAGE=<this skill>/assets/character/face.jpg` and open the prompt with plan.py's `FACE_REF` text plus her `text`. To change her, generate a new face the same way (`/v1/images/generations`, n=4, head-and-shoulders, facing the camera, plain background, "original fictional person, not resembling any real person"), pick one, replace the file and the `text`, never one reel's prompt.

## Steps
0. **Earlier shots**: shared step 1 (`../shot-history/scripts/shots.py check`).
1. **Plan**. Write `--view`: what is really there, the real landmarks, terrain, water, vegetation (shared step 2: name treeless terrain). Pick `--setting` (coast island mountain canyon lake city oldtown nature desert snow) and `--light` (sunset sunrise golden day blue-hour night; default to sunset/golden: the reference look).
   ```bash
   python3 scripts/plan.py --place "Ponta de São Lourenço, Madeira, Portugal" --setting coast --light sunset \
     --country portugal --view "jagged red volcanic cliffs and sea stacks dropping into the deep blue Atlantic, white surf, green headlands to the horizon, sun low over the sea" > plan.json
   ```
   It picks a hook (`styles.json` `hooks`), a reveal (`reveals`) and a music style (`music`) that fit the setting, light and country, skipping the last 3 of each used (`~/.config/zoominview/history.json`), a caption hook line (`captions`, in `caption_hook`) and the recurring character (`--person` for someone else). Use `--hook` / `--reveal` / `--music` only when the user names one; `--list` shows all.
2. **Render** (one background call; B starts from A's last frame, so they run in order):
   ```bash
   scripts/render plan.json ~/Movies/museai/zoom-<slug>
   ```
   Renders A, B, then C when the reveal has one. `scripts/render plan.json DIR b` re-renders only B (A kept); `a`, `c` likewise.
3. **Music** (in parallel with step 2):
   ```bash
   scripts/music plan.json ~/Movies/museai/zoom-<slug>
   ```
   `wow-ref` copies the reference track. An AI style renders through ACE-Step (~2-3 min, instrumental unless the style has wordless "ooh" lyrics) as a riser over the reaction that drops on the reveal; `--seed 9` for another take.
4. **Check the clips**: contact sheets (`ffmpeg -i a.mp4 -vf "fps=2,scale=180:-1,tile=6x2" -frames:v 1 a.jpg`, same for b). A: real face (pores, natural hands, 5 fingers), real surprise, no talking, ends on the transition frame (ground / blur / palm / shoulder). B: starts on that frame, reveals the real place, no person after the reveal, no text. Find the second in B when the view is fully open.
5. **Compose**:
   ```bash
   python3 scripts/compose.py --plan plan.json --music track.m4a --out zoom-<slug>.mp4 a.mp4 b.mp4 [c.mp4] --reveal <reel second the view is open> [--zoom-at <start of C>]
   ```
   Drops B's duplicated first frame at the join, cuts the head of A so the music drop lands exactly on `--reveal` (≥ 3.5 s reaction kept), eased digital push-in from the reveal (or `--zoom-at`) to the end, loops the track body when the reel is longer than the track (`--zoom 1.15`; 1.25 for a far view, 1 when muse's own push-in is enough), light grade, wind ambience under the music, denoise (afftdn, as stitch.sh; the looped reference track alone sat at -65 dB hiss), -14 LUFS.
6. **Verify**: shared step 6 (`../muse-video/scripts/qa.py zoom-<slug>.mp4 --travel 0 sheet.jpg`) and watch the join: no jump, face/clothes identical up to the transition, music swell on the reveal.
7. **Deliver**: shared step 7. Thumbnails: `thumbnail` style `travel --split` on the reel (the gasp on top, the view below); captions open with the plan's `caption_hook` (or a better one for this place). The final is `zoom-<slug>.mp4`: `Kelingking Beach - zoominview.mp4` was put on the Chinese channel by the dashboard.

## Choosing hook + transition + music (what plan.py encodes)
- The table under "Not one fixed recipe" is the map; each item's `setting` / `light` / `country` in `styles.json` is the source of truth.
- A country with its own music (`country`: Indonesia/Malaysia → `gamelan-chill`, Mediterranean → `med-guitar`, Arab world → `desert-oud`, Andes → `andes-flute`, East Asia → `east-strings`, Nordic → `nordic-choir`) wins over the generic styles; `--music wow-ref` / `alps-ref` still forces a reference track.
- Add a new hook, reveal, music style or caption line to `styles.json`, never only into one reel's prompt.

## Realism rules (`prompt/reveal.txt`, appended to both clips)
Ordinary traveller (not a model), real skin, wind in hair, silent gasp (no words: muse's lip-sync drifts), handheld with only a natural sway, real-time nature, level horizon once the view shows, no text. Clip A shows only a sliver of sky so B's view is a surprise and A's background can't contradict it.

## Lessons
- The transition must follow the person's gaze (Madeira, 2026-10-29): a swing down to the rocks then a tilt up revealed the view in another direction than she stared, and read as wrong. `swing-tilt` now has her look off to the right and the phone turn right, the way her eyes look.
- A sideways pan off the face only showed the scenery behind her, not what she was staring at, and the user rejected it. Like the reference: the person stares off to one side, only sky and hilltop behind them, and one continuous pan goes the way the eyes look, over the hillside and cliff edge onto the view. muse gets this from the explicit LEFT/RIGHT wording in `swing-tilt`.
- B wanders when long: a 10 s B tilted down to the ground and back. B is 6 s and locked on the horizon.
- "Move backward / pull out" made muse turn inland and lose the view, and an unnamed zoom target drifted to a cliff wall while the light dimmed (Madeira). B is an optical zoom-out aimed at `--focus`, C zooms in on `--focus` with the light held.
- The user rejected a pull-back (zoom-out) between pan and zoom-in, and a looped 13.8 s excerpt of the song (Madeira v6): pan, then zoom in only; use the whole song so it runs on without repeating.
- Zoom in gently (~1.5x, focus fills about a third of the frame, landscape around it): a zoom until the sea stack filled the frame read as too much (Madeira v7), and "1.5x" alone still zoomed too close then back out: the zoom stops at ~5 s and holds still.
- muse cannot continue a motion from one frame: B started from A's mid-turn frame swung back the other way twice (Madeira). A's transition now eases out and holds still on the view for its last 0.7 s, and B only pushes in from that still frame.
- muse bowed the head / covered the face with "hand over the eyes": the prompts keep the head up and the eyes on the view.
- muse put a second tourist in clip B: `plan.py` opens B with the NOBODY rule.
- `whip-pan` ended clip A mid-blur, which muse cannot continue (Kelingking, 2026-10-29): every reveal's A now ends still (on the view or a still palm/shoulder/crest frame), and every B ends with the shared `zoom` text. muse's own B zoom already reaches ~1.5x, so compose with `--zoom 1`.
- The pan has to land along the person's line of sight on a wide, far view (Kelingking v1 ended close on the headland from the side and the user said the angle was wrong for a zoom): A's pan ends with the focus small and far in the centre, the view as the person sees it; describe the classic viewpoint in `--view` ("seen from the high clifftop far above and behind it").
- muse's B zoomed in and then back out over the last 2.5 s (Kelingking v2) even with "never zooms back out"; the `zoom` text now also says the last frame is framed exactly like the frame at 5 s. It still pulled out in 2 of 2 retakes (zoom in to ~2x by 6 s, out from 7 s): cut B at ~5 s (`ffmpeg -i b.mp4 -t 5 ... b5.mp4`), before it gets tighter than ~1.5x, and compose with that (Kelingking reel = 11 s).
- The face photo as a reference (Kelingking with the character, 2026-10-29): take 1 kept her hair and bangs but dropped the glasses and drifted from her face; take 2 with "She WEARS HER ... GLASSES IN EVERY FRAME" in FACE_REF held the glasses, bangs and cream top and read as her. muse did not open on the room photo (FACE_REF says it is not the first frame).
- The AI face (no glasses, 2026-10-29) held on the first take: hazel-green eyes, freckles, chestnut bangs and cream knit all carried into clip A. Name each visible feature in `text` and FACE_REF; muse drops what is not named.
- A clip asked to hold still turns into a still photo (Lauterbrunnen glide-in, 2026-10-29): B take 2 glided, eased out at 6.2 s, then every frame was identical for 4 s (frame diff 0.0, the river stopped flowing). B take 1 ("still for the last 3 s") never stopped and drifted sideways instead. So a long reel never relies on muse holding still: cut the clip where the move eases out (`compose.cut`), and get the next stretch from a new clip that keeps moving slowly (C push-in) so water and clouds stay alive. Check with a frame-diff per 0.25 s: 0.0 = frozen.
- muse's slow push-in clip (C) speeds up after ~4 s (frame diff 7 → 10): keep 4 s.
- qa.py's motion TIME-LAPSE FAIL fires on every forward glide and push-in (the river counts as drift); judge glide reels by the sheet, `smooth` (no freezes/jumps) and `noise`.
- The server returns the earlier clip for an identical request: `RETAKE=1 scripts/render plan.json DIR b` for a new take of the same prompt.

## Maintaining this skill
Record lessons proven by a render here (prompt wording that held the transition, reveals muse cannot do, music styles that clashed), following `../muse-video/SKILL.md` "Maintaining this skill".
