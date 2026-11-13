---
name: healing-story
description: Make a 16:9 narrated healing story video (~3-4 min) through museai where a first-person voice tells a real, meaningful life story (a friendship, a family moment) while the picture shows calm home cooking and baking actions that echo each line, never narrating the recipe. Seasonal looks live in prompt/<season>.txt (christmas first: a snowy city apartment, a small tree, a best friend called Mia). Use for "healing story", "Christmas story video", "story while cooking", "tell a story over cooking", "best friend story", "meaningful story video", or the next episode of these.
---

# healing-story

Paths are relative to this folder (`.claude/skills/healing-story/`). Server, render queue, voice, music, compose, QA and delivery come from `../healing-video/SKILL.md` (Story mode) and `../muse-video/SKILL.md`; this skill changes what the story says and what the shots show. Name everything `healing-<slug>`; the work folder is `~/Movies/museai/healing-<slug>/`.

## The format (user 2026-11-12)
The user found Story mode videos that narrate the recipe less meaningful: "don't need to say anything related to cooking, just show cooking actions, but tell the real story".
- **The voice tells a life story, not the recipe.** First person, one real-feeling story with one turn and one lesson (a stranger who became a best friend, a parent's small habit, a letter never sent). At most two lines mention the food, and only as part of the story ("She's the reason I'm baking tonight", "Gingerbread, a little burnt, the way she likes it").
- **The picture shows calm cooking and home actions that RHYME with each line** (the line and the shot mean the same thing without saying it):
  | line | shot |
  |---|---|
  | alone in a new city | one egg cracked into a big empty bowl |
  | "she just kept showing up" | two mugs set down side by side |
  | she moved away | hands taping a moving box |
  | the friendship grows | two pairs of hands kneading one dough |
  | the first knock (hook) | the friend at the door, face visible, a plate in her hands, smiling as it opens; the last beats: she stands at a new door (bookend) |
  Memories are cutaways in the same home (a stairwell, a window, a doorway); the present day is her baking for the person in the story, so the cooking leads to the ending (the friend arrives, two mugs).
- **Story arc** (~35 beats, 400-600 words, 3-4 min): hook (a confession or promise, the first sentence) → present-day frame in one line ("she lands in two hours, so let me tell you how we met") → the lonely before → the small moment that changed it → the friendship in three quick images → a quiet loss or distance → the present day → the lesson as an action the viewer can take ("If you know someone who's alone this Christmas, knock") → a two-word close ("Merry Christmas.").
- **English**: natural, casual, native spoken English: short sentences, contractions, everyday words, a little humour ("a fridge with one jar of mustard"), 1-2 sentences per beat. Dialogue goes into the voice-over as reported speech ("And she said, hey, are you doing anything tonight?"). No poetic words.
- **Restrained emotion**: the voice may say "I cried"; the picture never shows it. Sad beats are calm shots from behind, hands still, eyes on the thing. Big moments (meeting, reunion) are hands or two people side by side from behind.

## Shots
`scripts/shot "<brief>" sN.mp4` appends `prompt/$SEASON.txt` (default `christmas`): the plain real look, the girl's fixed look (same as healing-video), the friend's fixed look, faces shown naturally, one light source, close-miked sound. It refuses bait words (cosy, glow, candle, fairy lights, bokeh, glitter, crying, tears, knife, knuckles, door handle; `BRIEF_OK=1` overrides) and renders 16:9 at 6 s.
- One shot per beat; each brief names who (the girl / Mia / both / hands), what the hands do, the light ("bright soft daylight from a snowy window", or "Evening." first for dusk shots), and the sound of the action.
- **Same faces in every shot (user 2026-11-13, third cut: "Mia's face is not consistent across all scenes")**: text alone gives a new face per shot. Every shot with a face starts from a still made with the character bank (`../character-bank`, cards `MIA` and `ELLIE`, the girl): `python3 ../character-bank/scripts/bank.py scene v3/ "<the first moment of the shot>" MIA ELLIE --size 1920x1080 --n 1 --look prompt/christmas.txt`, then the clip from that still: `IMAGE=<still>.png scripts/shot "<the action>" sN.mp4`. Shots of hands or of a person from behind stay text-only.
- **Human behaviour, not AI batch action (third cut)**: "two people laughing look awkward, mid laughs also awkward", "action should be real like human behaviour". Each shot is one ordinary action at real-life speed with a small pause; one person acts and the other reacts a moment later; warm small smiles and a short chuckle at most, never both laughing open-mouthed. A first meeting is told in its real order: the friend knocks (whole person, beat 1), the girl walks to the door and opens it, the friend at the door says her line, the reaction.
- **People act like people (user 2026-11-12, second cut)**: "two girls should talk to each other and laugh freely, show Mia's face", "many scenes look awkward, not like human". Moments between people are medium shots with both faces visible: talking across a counter, one passing the other something. Name the feeling and the small natural gesture ("Mia says something short with a grin; Ellie smiles a moment later"). Nobody looks into the lens. A task alone stays "seen from the side, eyes on X". Never shoot a person only from behind for a whole shot when the line is about them.
- **Doors, knocks and sharp tools look fake in close-up** (that cut: a disembodied fist knocking, a hand pressing a handle, a door swinging by itself, a knife passed handle first). Show the whole person at the door in a medium shot (standing in the stairwell with the plate, the door already open), never a hand on a handle or a knocking fist. Never hand over or hold up a knife; give the hands something soft (a bowl of potatoes, an apron, a mug).
- Food keeps its colour in every shot (orange carrot soup, dark-edged gingerbread). The decor stays small: name "the small tree's warm-white string lights" or "a small simple wreath", never a list of decorations.
- Hook shot (beat 1) starts mid-action with a sound you can see (a cutter in dough, a pour) or a person already in the moment (the friend smiling at the open door).

## Steps
1. **Story**: write `story.json` (`{"title", "season", "lesson", "beats": [{"vo", "shot"}]}`) in the work folder; keep a copy in `stories/<slug>.json` (the bank of told stories: never retell one; `ls stories/`). Show the user the title, hook and lesson; render after a yes unless they asked to just make it.
2. **Voice** (background, ~2 min): `uv run --no-project --python 3.11 --with "kokoro>=0.9" --with soundfile --with "misaki[en]" python ../place-story/scripts/vo.py story.json --speed 0.92` → `vo/bN.wav`.
3. **Shots**: one jobs line per beat with a retry, `../muse-video/scripts/render-queue -j 3 jobs.txt` in ONE background call:
   ```bash
   for t in 1 2 3 4; do scripts/shot '<brief>' ~/Movies/museai/healing-<slug>/sN.mp4; [ -f ~/Movies/museai/healing-<slug>/sN.mp4 ] && break; sleep 45; done
   ```
4. **Music**: `../healing-video/scripts/music "<season> piano lullaby, tender" p1.m4a <story seconds + 10> <seed>`; it must pass the calm gate (exit 3 → next seed). Christmas: "winter christmas piano lullaby, tender, warm"; no bells or jingles.
5. **QA**: contact sheet of all clips (`ffmpeg -i sN.mp4 -vf "fps=1,scale=320:-1,tile=6x1"`); re-render any shot with a face to camera, a stiff pose or frozen smile, a person who doesn't move like a person, crying, warped hands, a changed hair/sweater/scarf, wrong food colour, or decor clutter.
6. **Compose**: `python3 ../healing-video/scripts/story169.py story.json --music p1.m4a --out healing-<slug>.mp4` (small bottom subtitles, dissolves, ducked piano, -16 LUFS).
7. **Deliver**: 16:9 + 9:16 covers from a raw clip (never the composed video: subtitles burn in), title centred on the frame, style rotated from the cover history (`--style auto`, see healing-video step 7):
   ```bash
   python3 ../healing-video/scripts/cover.py --size 16:9 --at sN.mp4@auto --eyebrow "<season story>" --title "<hook>" --out thumbs/healing-<slug>_16x9.jpg
   python3 ../healing-video/scripts/cover.py --at sN.mp4@auto --eyebrow "<season story>" --title "<hook>" --out thumbs/healing-<slug>_9x16.jpg
   ```
   captions via `../social-captions` (no `#Shorts`), record with `../healing-video/scripts/ideas.py record custom ...`, then `FINAL=1 THUMB_DIR=thumbs CAPTIONS_FILE=captions.json ../muse-video/scripts/deliver.sh healing-<slug>.mp4 <work dir> healing-<slug>` (it trashes the work folder: record first).

## Seasons
`prompt/<season>.txt` holds the full shot rules for one season and its cast. To add one (spring, Lunar New Year, autumn), copy `christmas.txt`, change the place, light, decor and sound lines, keep the girl's paragraph word for word, and run with `SEASON=<name>`.
