---
name: chinese-podcast
description: Make a 16:9 Mandarin "emotional radio" story video (情感电台 / 林晚电台 style) that people both listen to and learn Chinese from - a calm close-mic narrator tells one small deep story (the road home, mother's phone call, a cup of tea, a letter to your 18-year-old self) over slow cinematic stills, a soft piano / guzheng / lo-fi bed, a date card with the lunar date, and captions with tone-marked pinyin over every hanzi plus a Vietnamese line, new-word cards and a word recap at the end. 1000 script seeds (50 themes x 20 story frames) and banks of voices, music moods and visual looks, mixed at random so no two episodes look or sound alike; a history keeps seeds from repeating. Use for "chinese podcast video", "pinyin caption story", "情感电台", "林晚电台 style", "deep chinese story video", "learn chinese with a story", or "next chinese podcast".
---

# chinese-podcast

Paths are relative to this folder (`.claude/skills/chinese-podcast/`). Server, retries and QA come from `../muse-video/SKILL.md`.
Style source: `references/reference-reels.md` (5 reels the user picked), `references/reel-1456768899288979.md` (sunlit cottage, verdict-first, low calm female voice) and
`references/rangchieuwanxia.md` (that reel's whole page, 10 reels: home vlog and seasonal-window looks, six more story shapes). They are style references only: never download
or reuse their audio, never clone the speakers; the narrator is Mandarin edge-tts and the music is our own ACE track.

## Banks (`bank/`)
| file | what | count |
|---|---|---|
| `themes.json` | one quiet truth each (遇见, 放下, 家, 今天, 回忆, 亲人, 光鲜 …) with vi | 59 |
| `frames.json` | story shapes (一把伞, 回家的路, 妈妈的电话 …) + the looks that fit (f21 先说结论: verdict first, end on a question; f22-f27 from rangchieuwanxia: 什么是, 把自己养好, 还没去过的地方, 换个地方开花, 光鲜背后, 如果再一次) | 27 |
| `scripts.json` | seeds = theme x frame; `podcast.py bank` keeps existing ids and appends new pairs after a bank edit | 1593 |
| `voices.json` | Standard Mandarin narrators, slow rate, lower pitch (4 female incl. the brisker xiaoyi-diary, 2 male) | 6 |
| `music.json` | mood beds with full ACE instrument tags, all instrumental | 10 |
| `looks.json` | visual looks from the reels: street-cinema, zen-still, illustrated-home, morning-cycle, sunlit-cottage, vlog-diary, season-window; each lists its music | 7 |

`podcast.py next` picks an unused seed whose theme was not in the last 15 episodes and frame not in the last 5, then a
random look (from the frame), voice and music (from the look), never repeating the previous episode's choice.
A seed is a brief, not a script: write the script fresh each time from the seed's truth and shape.

## Writing the script (the part that makes it deep)
- One truth (the seed's `truth`), told through one concrete small story (the frame). No lecture, no list of advice.
- Shape: greeting with the date (line 0: 早上好 / 晚上好，今天是十一月二十四号。) → a question to "你" → the story in
  the first person with small physical details (the umbrella, the bowl of noodles, the light still on) → the turn
  (那一刻我才懂 / 后来才明白) → the truth in plain words → a gentle second-person close (所以，如果你累了…) → 晚安 / 早安.
- 20-28 lines, each one breath: 16 hanzi or fewer, HSK 2-4 words, short sentences, no chengyu pile-ups.
- `vi`: natural Vietnamese, not word for word. `shot`: one concrete image per line, people from behind or far away.
- 3-5 lines carry `word: {zh, py, vi}`: the useful word of that line (shown top right, then in the end recap).
- `py` on a line overrides pypinyin (space-separated syllables for the hanzi only) when `captions` prints a wrong
  reading; `say` overrides what the narrator reads; `pause` (s) overrides the gap after the line.

## Steps
Work folder `~/dev/museai-work/chinese-podcast/<epNNN-slug>/`. Python deps:
`UV="uv run --no-project --python 3.12 --with edge-tts --with pypinyin --with pillow --with lunardate python"`.
1. `python3 scripts/podcast.py new DIR` → write `title`, `title_vi`, `lines` into `DIR/episode.json`.
2. `$UV scripts/podcast.py voice DIR` → `vo/lNN.wav`. Listen to two lines; `pron.py` (muse-video) if a word sounds off.
3. `$UV scripts/podcast.py captions DIR` → `cap/`. It prints the pinyin per line: check polyphones (还, 长, 了, 着, 行, 得).
   Look at `cap/card.png`, one `cap/lNN.png` with two rows and one `cap/wNN.png`.
4. `python3 scripts/podcast.py stills DIR` → one muse still per line (`--only 3 7` redoes lines). A `stills/sNN.mp4`
   (a muse clip) replaces the still for that line. Look at a contact sheet; redo any still with text, faces to camera
   or a wrong look.
5. `python3 scripts/podcast.py music DIR` → `music.m4a` (ACE on Colab; length = film + 8 s).
6. `python3 scripts/podcast.py compose DIR` → `DIR/<slug>.mp4` on the Colab render queue (never ffmpeg on this Mac;
   `RENDER_LOCAL=1` only when asked). The runtime clones museai main: podcast.py changes must be merged first.
7. QA: `python3 ../muse-video/scripts/qa.py DIR/<slug>.mp4 --travel` + watch the first 20 s and one caption with
   a word card. Then `python3 scripts/podcast.py record DIR --video DIR/<slug>.mp4`.

## Film grammar (encoded in `compose`)
16:9 1920x1080 30 fps. Date card alone for 3.2 s, then one still per line with a slow alternating push-in / pull-out,
0.9 s dissolves, warm muted grade, grain, vignette. Caption fades in with the voice and out after it; gap 0.8 s
(1.3 s after 。？！). Word recap card 7 s at the end, 2.5 s fade to black. Music -6 dB, side-chain ducked under the
voice, mix loudnorm -16 LUFS.
