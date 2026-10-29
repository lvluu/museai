---
name: zoominview
description: Make a short vertical "wow reveal" reel of a place through museai - a real-looking traveller films a selfie, is genuinely overwhelmed by what they see (silent gasp, hand to the face), the camera transitions to the view (phone swing + tilt-up, whip pan, hand off the lens, over the shoulder, over the crest, through the window), then slowly zooms into the beautiful view, with music that swells the moment the view opens - the reference reel's own track or an AI track (felt piano, epic orchestral, dreamy pads, tropical chill, acoustic, synth glow, guzheng, nordic choir) chosen to suit the place. Use for "zoominview", "zoom in view", "reaction reveal", "surprised person then the view", "video like the Madeira cliff one", or "zoominview <place>".
---

# zoominview

Paths are relative to this folder (`.claude/skills/zoominview/`). Server, retries, QA and delivery come from `../muse-video/SKILL.md`; the music engine is `../scenic-drop-reel/scripts/music.py`.

## The format (measured on the reference reel, 13.8 s, 9:16, one continuous shot, no cut)
| time | what | why it works |
|---|---|---|
| 0-4.5 s | selfie, front camera, golden light, wind in hair; the person stares past the camera off to ONE SIDE; behind them only sky and a grassy hilltop (the view is never behind them); mouth open, hand on forehead | the face is the hook: viewers stay to see what they see |
| 4.5-9 s | one continuous handheld pan the way the eyes look: the face slides out the opposite edge, the camera sweeps over the scrub on the hillside, along the cliff edge, and the view opens beyond it; music swells at ~7 s | the camera goes exactly where they stared: the payoff lands on the music |
| 9-13.8 s | level, slow push-in on the view | lets the eye settle on the beauty |

`swing-tilt` (~15 s): clip A = reaction + pan, clip B = one long optical zoom in on `--focus`. No pull-back: the camera only moves to the view, then zooms in.

Reference music: the reel uses "Runaway" (the user supplies the full song; play it straight through, never loop a short excerpt). `assets/wow-ref.m4a` (13.8 s excerpt from the user's reel): mellow ambient, ~57 BPM, quiet under the reaction, dip 5-6.5 s, swell from 7.0 s. Audio files are gitignored: it stays local, personal posts only.

## Steps
1. **Plan**. Write `--view`: what is really there, the real landmarks, terrain, water, vegetation (name treeless terrain, see muse-video lessons). Pick `--setting` (coast island mountain canyon lake city oldtown nature desert snow) and `--light` (sunset sunrise golden day blue-hour night; default to sunset/golden: the reference look).
   ```bash
   python3 scripts/plan.py --place "Ponta de São Lourenço, Madeira, Portugal" --setting coast --light sunset \
     --country portugal --view "jagged red volcanic cliffs and sea stacks dropping into the deep blue Atlantic, white surf, green headlands to the horizon, sun low over the sea" > plan.json
   ```
   It picks a reveal (`styles.json` `reveals`) and a music style (`music`) that fit the setting, light and country, skipping the last 3 of each used (`~/.config/zoominview/history.json`), and a random traveller (`--person` to set one). Use `--reveal` / `--music` only when the user names one; `--list` shows all.
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
   python3 scripts/compose.py --plan plan.json --music track.m4a --out reel.mp4 a.mp4 b.mp4 [c.mp4] --reveal <reel second the view is open> [--zoom-at <start of C>]
   ```
   Drops B's duplicated first frame at the join, cuts the head of A so the music drop lands exactly on `--reveal` (≥ 3.5 s reaction kept), eased digital push-in from the reveal (or `--zoom-at`) to the end, loops the track body when the reel is longer than the track (`--zoom 1.15`; 1.25 for a far view, 1 when muse's own push-in is enough), light grade, wind ambience under the music, denoise (afftdn, as stitch.sh; the looped reference track alone sat at -65 dB hiss), -14 LUFS.
6. **Verify**: `python3 ../muse-video/scripts/qa.py reel.mp4 --travel 0 sheet.jpg` (judge `smooth` + sheet; `motion` TIME-LAPSE flags the pan and the zooms, check frames instead) and watch the join: no jump, face/clothes identical up to the transition, music swell on the reveal.
7. **Deliver** with `../muse-video/scripts/deliver.sh` (preview, `FINAL=1` after OK), `THUMB_DIR=` (thumbnails from `../thumbnail/SKILL.md` with `--split`: the gasp on top, the view below) and a `CAPTION_FILE`: hook line ("I wasn't ready for this view…", "POV: you reach the top of …"), place line, call to action, 3-6 hashtags.

## Choosing transition + music (what plan.py encodes)
- Cliffs, coast, canyons → `swing-tilt` (the reference); peaks, dunes, snow ridges → `crest-rise` / `over-shoulder`; city skyline, old towns, hotel views → `window-open` / `whip-pan`; anything → `hand-reveal`, `whip-pan`.
- Sunset/golden → `wow-ref` or `piano-swell`; huge scale (canyon, glacier, desert) → `epic-rise`; snow, mist, blue hour → `dream-pads`; beach, island by day → `tropic-chill`; villages, vineyards → `acoustic-glow`; night city → `city-glow`; East/South-East Asia → `east-strings`; Nordic → `nordic-choir`.
- Add a new reveal or music style to `styles.json`, never only into one reel's prompt.

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

## Maintaining this skill
Record lessons proven by a render here (prompt wording that held the transition, reveals muse cannot do, music styles that clashed), following `../muse-video/SKILL.md` "Maintaining this skill".
