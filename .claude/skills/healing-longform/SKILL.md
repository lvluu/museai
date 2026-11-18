---
name: healing-longform
description: Make a ~5 minute horizontal 16:9 (1920x1080) healing video through museai - one girl's slow day of gardening and cooking told in 4-6 chapters (morning in the garden, the harvest, cooking, rain, dusk), a small meaningful and quietly funny everyday story in sparse first-person voice-over with subtitles, 4-8 s locked-off shots with one gentle motion each, chapter title cards, real garden and kitchen sound, a calm piano bed. Story seeds with a history so no story, place or dish repeats; stills render first (images have no daily limit) and clips fill in when muse's 24-hour video quota allows. Use for "long healing video", "5 minute healing video", "healing day video", "gardening and cooking video", "horizontal healing video", "YouTube healing video", "slow living vlog", or the next one of these.
---

# healing-longform

Paths are relative to this folder (`.claude/skills/healing-longform/`). Server, render queue and delivery come from `../muse-video/SKILL.md`; voice, music, grade and subtitle helpers from `../healing-video/` (Story mode, `scripts/story169.py`); the continuity rules from `../healing-story/SKILL.md`; the girl's face card from `../character-bank/`. Name everything `healing-<slug>`; the work folder is `~/Movies/museai/healing-<slug>/`.

Run `scripts/longform.py` and `../healing-video/scripts/cover.py` with a Python that has Pillow (the project `.venv` may not have it; any venv with `pip install pillow` works).

## What it is

A whole slow day in five minutes. Nothing big happens: she picks what is ripe, cooks it, the weather turns, and one small thread runs through the day (a neighbour, a letter, a recipe, a bet) that closes gently at dusk or the next morning. The viewer should breathe slower by the second chapter and smile once or twice.

## Brainstorm (what makes five minutes work)

**Structure: a day in chapters.** Five chapters of ~55-60 s, each opening on a cream serif title card over a wide breathing shot ("i. morning", "the wall"). Chapters give a long video a shape a viewer can rest in. Proven shapes:
- *The gift and the answer* (lf-001): something is given in ch. i, she makes something back from the garden, leaves it, gets a reply the next morning.
- *The family recipe*: a handwritten recipe found in ch. i, garden harvest for it, a failure, a second try that works, a call home at dusk.
- *The stubborn plant*: one thing in the garden won't grow or ripen; the day is everything else she does while waiting; it comes good (or a bird eats it) at the end.
- *The too-much harvest*: too many courgettes/plums; the day is using them; the village answers.
- *Weather as a chapter*: rain at noon turns the garden chapter into a kitchen chapter; rain is the best mid-film rest.

**Narration.** First person, past-tense-free, plain spoken American English, 1-3 short sentences a line, 18-22 lines in five minutes (about one in every two shots). Kokoro af_heart at speed 0.88 (`../place-story/scripts/vo.py`). Every line shows something the picture does not: the thread, a memory, a dry joke. Never narrate the recipe or the action on screen. The humour is understated and self-aware ("We negotiated. He kept the basket.", "The good side faces out. That's called presentation."). One sentence of meaning at the end, said simply, then a two-word close. Subtitles at the bottom in the healing-video Story-mode style.

**Breathing shots.** One beat in three has no voice: a wide of the garden, rain on the glass, the cat asleep, steam over a pot. They hold 8 s and carry the film's calm; never cut them to save time.

**Shot rhythm.** Beats run 7-11 s (lead 1.4 s + voice + 2.6 s gap; voiceless beats 8 s; 34 beats come to ~5 min), joined by 1.0 s dissolves. Each clip is 10 s of muse footage, so the slow rhythm comes from long-held shots, not from cutting fast. One action per shot. Alternate scale: wide (place) - medium (her at work, from behind or the side) - close (hands, food, the cat) - wide. Stills animate as a slow 1.00 to 1.05 push-in.

**Camera.** Locked off, always (`CAMERA` sentence in every clip brief): muse's camera moves read as fake in long form. The motion is in the frame: her hands, steam, rain, leaves, the cat's ear.

**Sound.** The clips' own close-miked sound is the bed (a still borrows the sound of the nearest clip of the same place), real rain under every beat whose `time` contains "rain", a calm piano from ACE-Step ducked under the voice, final -16 LUFS, a 3 s fade-out. No birdsong library exists here, so the garden's birds come from the clips.

**Music.** One track for the whole film, generated at full length: `../healing-video/scripts/music "<season> piano lullaby, tender, unhurried" music.m4a 310 <seed>`; the calm gate rejects tracks that swell (exit 3: next seed). Seasonal words: "late autumn piano lullaby", "warm summer afternoon piano", "soft winter piano, sparse", "spring morning piano and soft strings".

**16:9 framing.** The horizontal frame wants places: the whole garden with a neighbour's chimney behind, the kitchen table by the window. Keep her off-centre (thirds), seen from behind or the side; close-ups top-down or side-on. Never a face to camera.

## Story file (`story.json`)

Copy the newest `stories/<slug>.json` as a template. Fields: `title`, `slug`, `story_id` (the seed id), `season`, `eyebrow` (the cover's small line), `places` (one description per place), `light` (one sentence per time of day; a time with "rain" gets the rain bed), `outfits` (her clothes per time; they change through the day), `refs` (`kind: place` or `prop`: rendered once with nobody in them, attached to every still of that place or with that prop), `chapters` (`[number, title]`), `beats`.

A beat: `ch`, `where`, `time`, `outfit`, `kind` (`clip` | `still`), `cast` (`["ELLIE"]` when she is in frame, `[]` for hands only or nobody), `props`, `chapter: true` on the beat that opens a chapter, `vo` (optional), `shot` (the frame), `move` (the one motion, clip beats only).

Writing the shots: follow `../healing-story/SKILL.md` continuity rules (containers named with their contents, sleeves named on hands-only shots, the whole family of an object in frame) and `../healing-video/SKILL.md` "Real look" (no bait words: `scripts/shot` rejects them). No knives on screen, no crying, no faces to camera. Recurring animals and objects get a `refs` entry.

## Steps

1. **Pick a story.** `python3 scripts/stories.py next --season now` gives a seed not told before whose place and dishes differ from the last 5 videos. Write `story.json` from it: 30-36 beats, 5 chapters, ~5 still beats (wide breathing shots and anything muse animates badly), the rest clips.
2. **Plan.** `python3 scripts/plan.py jobs story.json` writes `jobs-refs.txt`, `jobs-stills.txt`, `jobs-clips.txt`. `plan.py brief story.json N` shows what a beat sends.
3. **Voice and music**, in the background: `../place-story/scripts/vo.py` on the beats with `vo` into `vo/bN.wav`; the music command above into `music.m4a`.
4. **Render**, detached, one queue at a time per kind (max 2-3 jobs in parallel):
   ```bash
   Q=../muse-video/scripts/render-queue
   $Q -j 2 jobs-refs.txt && $Q -j 3 jobs-stills.txt && $Q -j 2 jobs-clips.txt
   ```
   Start it with `subprocess.Popen(..., start_new_session=True)` or `nohup` so it outlives the session. Every step skips what is on disk: re-run the same line after a crash or a quota stop.
5. **Check the stills before the clips.** Contact-sheet `stills/` and look: her braid over the left shoulder, the outfit of that time of day, no door frames or extra people, containers full. A bad still: delete `stills/sN.png`, fix the beat, re-run its job. A clip inherits everything wrong in its still.
6. **Clips and the 24-hour limit.** muse allows a limited number of videos per account per 24 h (images are not limited). When every account is at its limit (`/admin/accounts` shows `quota_hits`), stop: `plan.py status story.json` lists the missing clips; write that in the work folder and come back after the limit resets. Do not loop on retries. A cut can be composed at any time: a missing clip shows as its still pushed in.
7. **QA the clips**: `../muse-video/scripts/qa.py` on each, and look at a frame sheet. Trim a bad ending in compose rather than re-rendering; re-render (delete `sN.mp4`, re-run the job) only a broken shot (face to camera, morphing hands, a second person).
8. **Compose.** `longform.py story.json --music music.m4a --out healing-<slug>.mp4 --dry` prints the beat timeline and total length (aim 280-320 s; tune with more or fewer voiceless beats). Then without `--dry`. Segments are cached; `--fresh` rebuilds all.
9. **Cover and captions.** 16:9 and 9:16 covers from a raw clip or still: `../healing-video/scripts/cover.py --size 16:9 --at sN.mp4@auto --eyebrow "<eyebrow>" --title "<hook>" --out thumbs/healing-<slug>_16x9.jpg` (and `--size 9:16 ... _9x16.jpg`); the title is a calm lowercase 2-5 word hook not used on the last 10 covers. Captions through `../social-captions/` into `captions.json` (`captions.py check` must PASS; no `#Shorts` on a horizontal video).
10. **Record and deliver.** Copy `story.json` to `stories/<slug>.json` in this skill, `python3 scripts/stories.py record <id> --video <path>`, then `FINAL=1 THUMB_DIR=thumbs CAPTIONS_FILE=captions.json ../muse-video/scripts/deliver.sh healing-<slug>.mp4 <work dir> healing-<slug>` (it trashes the work folder: everything to keep is copied out first). The server files the delivery into `~/Desktop/Healing NN · <day> · healing-<slug>/`.

## Lessons

- A place reference on a close-up makes muse widen the frame to show the room: `plan.py` attaches place refs to wide and medium shots only.
- `prompt/look.txt` describes the girl, so muse drew her face into every shot, even "nobody" and hands-only beats. `plan.py framing()` adds who is in frame to each brief from `cast` and the shot text ("her hand(s)" = hands only, else nobody). Write "her hands" in a hands-only shot.
- The garden ref came back framed through a doorway; stills of that place may inherit a door frame. Check step 5.
- Clips are 10 s and most beats use 4-8 s of them: write the `move` so the motion happens in the first 6 s.
- Wide shots of a small subject (the cat in the basket, a robin on the wall, a mug on the table) came back as tiny details in the whole garden: start those shots with "Close-up" so `plan.py` drops the place reference.
- The first video took ~2.5 h of clip rendering (29 clips, 2 at a time, 4-10 min each) and hit the 24-hour limit on clip 27: 3 beats shipped as still push-ins, which read fine between clips.
