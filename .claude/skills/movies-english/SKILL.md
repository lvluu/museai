---
name: movies-english
description: Make "Movies English" reels - 15-30 s vertical AI rom-com short movies that look exactly like the memoriescore.studio reels (warm 1990s Kodak-film picture with deep blacks and rich colour, 1990s supermodel cast Viv & Jamie, Sienna & Theo, Maya & Lucas, 10-20 quick shots with inserts and big close-ups, constant motion, physical comedy, a reaction button ending with a meaning of its own, tiny white English subtitles). A story, never a lesson: no card unless the script lists `words`. Holds a library of 1000 ready scripts, the cast bible, the build/render/finish pipeline through museai/muse-video, and the social growth plan. Use for "movies english", "english through movies", "learn English reel", "make video ME-0042", "next movies english video", "rom-com English lesson", or videos in the style of the memoriescore.studio / EmmaRobins / Aspen ski / Christmas pyjama reference reels.
---

# Movies English

Paths are relative to this folder (`.claude/skills/movies-english/`). Rendering, server, retries and
delivery reuse `../muse-video/` (read its SKILL.md: Server, Generate one clip, Deliver). This skill keeps
only what is specific to the format.

| file | what it holds |
|---|---|
| `references/reference-study.md` | the reference reels measured (memoriescore.studio x10, the target; the three IG reels): cuts, shots, picture, faces, subtitles, sound |
| `references/script-format.md` | the script JSON shape and the writing rules |
| `references/growth.md` | platforms, posting plan, engagement and monetisation |
| `series/cast.json` | the six recurring characters: identity (face), wardrobe sets, voice, comic engine |
| `prompt/look.txt` | the memoriescore look (warm 1990s film, deep blacks, rich colour, slow push/drift camera, constant motion, 90s supermodel faces), appended to every shot prompt |
| `library/batch_NN.json` | 1000 scripts, `ME-0001`..`ME-1000` (00: 1, 01: 99, 02-10: 100 each) |
| `scripts/check.py` | library lint: counts, unique ids and phrases, phrase in a line, line length, timing |
| `scripts/build.py` | `ME-NNNN WORK` → still requests, shot prompts, `render.sh` |
| `scripts/stills.sh` | renders every still (two takes each) through `/v1/images/generations` |
| `scripts/finish.py` | Whisper trims, grade (`GRADE=film` default / `airy`), hard cuts at 720x1280/24 fps, tiny white subtitles, "new words" end card |
| `posted.json` | ids already delivered (next video = the lowest id not in it, unless the user names one) |

## Make one video
`WORK=~/Movies/museai/me-NNNN`.
1. `python3 scripts/build.py ME-NNNN $WORK`, then `scripts/stills.sh $WORK` (background, 5-15 min).
2. Look at each still pair next to the reference faces (reference-study.md "Picture"); copy the better
   take to `$WORK/stills/<name>.png`. Reject a face that looks older than 23, contour or heavy brows,
   plastic or airbrushed skin, a flat grey or washed-out picture, a famous-looking face, wrong wardrobe,
   text in the frame, a speaker facing away. Want: warm golden film light, deep blacks, big 90s hair. Close-ups of one
   person share one still per episode: that is what keeps the face the same across cuts.
3. `$WORK/render.sh` in the background: the shots render one at a time (`render-queue`), one muse call each, through
   `../muse-video/scripts/muse-video` (quality block appended). Check each clip with
   `../muse-video/scripts/check_clip.sh`; re-render a failing shot once with `RETAKE=1`.
4. `uv run --no-project --python 3.12 --with faster-whisper --with 'av<14' --with pillow python scripts/finish.py $WORK $WORK/final.mp4`
   (optional `HANDLE="@yourpage"` watermark; no music unless asked). `MISHEARD` → re-render that shot.
5. Put frames next to the references (reference-study.md memoriescore table): warm film picture with
   deep blacks and rich colour, 1.7 s average shot, faces as young and glamorous, subtitle tiny and
   white at ~74 %, no card unless `words` is set (then correct Vietnamese diacritics). Preview with `SendUserFile` (render).
6. On the user's OK: captions per platform (`../social-captions/`, Vietnamese, `cta_vi` as the
   question), thumbnails (`../thumbnail/`), `FINAL=1 ../muse-video/scripts/deliver.sh`, add the id to
   `posted.json`.

## Reference cast (the exact people of a reference reel)
When the user asks for the exact reference people, use frames of that reel instead of stills:
1. Pull clean frames (no subtitle on them; `delogo` over the handle) of each person, one per framing,
   into `~/Movies/museai/refcast/<reel>/`. Never commit them: they are someone else's footage.
2. Copy the library script to `$WORK/episode.json`, set its `setting` to the reel's own place, add
   `look_as` (`{"VIV": "the young woman in the cream boucle jacket"}`: how to spot each person in the
   frame), and give every shot a `first` frame. Muse keeps the face only in that frame's own scene; it
   refused the same girl in a new setting, so the story must stay in the reel's place.
3. `python3 scripts/build.py $WORK/episode.json $WORK` (no stills), then steps 3-5 above.
4. Tell the user once that publishing someone else's face and footage risks takedowns.

## Writing more scripts
Follow `references/script-format.md` and the rhythm in `references/reference-study.md`; new ids continue
after the last batch; `python3 scripts/check.py` must pass (no phrase reused). Keep the comedy visual and
the words few: 10-20 shots, most 1-2.5 s, 2-4 `insert` shots of hands and objects, a striking first
frame mid-action, a reaction close-up button at the end, extras and animals in the world. Story first: the payoff means something about the two people; `words` only if a card is wanted.

## Maintaining this skill
Same flow as muse-video "Maintaining this skill". Encode a lesson from a render or a user correction
as a check in `check.py` / `finish.py` or a line in `look.txt` / cast.json, not as more prose.
