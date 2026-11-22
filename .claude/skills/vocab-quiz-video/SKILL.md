---
name: vocab-quiz-video
description: Make a vertical vocabulary quiz video (TikTok / YouTube Shorts) for any language and level - muse.ai renders one scene clip per word (6 prompts, each checked and redone alone), then a local script builds the video - hook "Can you get 6/6?", 6 words over scenery from the language's country, fast ~36 s cut with the first word at 1.5 s, 2-1 circle countdown with ticks, reveal chime, the answer with gender-colored article and IPA said once by a fixed edge-tts voice with a listen-and-repeat pause, a recap, one score CTA and a next-episode teaser. Use when the user asks for a vocabulary / word quiz / flashcard video in German, Spanish, French, Japanese, Chinese or another language, names a level (A1, A2, B1, HSK 2, N5, ...) and a topic, or wants a new episode of the vocab quiz series.
---

# vocab-quiz-video

muse.ai makes only the pictures: one prompt per word, one clip each. Claude looks at every clip and redoes only the bad ones. Then `scripts/build.py` builds the finished video on this machine: text cards (Pillow), countdown, ticks and chime, voices (edge-tts), timing, loudness (ffmpeg). The video has no background music; the user adds music on TikTok.

Why not one prompt per video (used until 2026-11-18): muse.ai built the whole video itself, and the result was weak. Objects were unclear in several clips (ep16: a floating sheet for "paper", the teacher covering the blackboard), IPA and labels were tiny, the TTS voice changed per video and could not be checked, and one bad clip meant rendering everything again.

Paths below are relative to this folder (`.claude/skills/vocab-quiz-video/`).

Needs: the museai server running (`python -m museai`, used by `../muse-video/scripts/muse-video`), `uv`, `ffmpeg`, network for edge-tts.

## Files

| File | Role |
|---|---|
| `clip-template.md` | The muse prompt for one word's scene clip, with `{PLACEHOLDERS}` |
| `languages/<language>.md` | Language playbook: front-matter keys (country, TTS voice, article colors, ...) + word-list rules and lessons |
| `languages/german.md` | **Reference playbook** (tested end to end). Copy its shape for a new language |
| `languages/_new-language.md` | Empty playbook to copy, with the meaning of every key |
| `series.md` | Series plan, design system, pre-post checklist, analytics log |
| `log.md` | Your own log of made episodes and words used. Git-ignored; copy `log.template.md` on first use |
| `scripts/fill_prompt.py` | Words file + language file → `clip1.txt` ... `clip6.txt` + `episode.json` in the episode folder |
| `scripts/build.py` | Episode folder with `clip1.mp4` ... `clip6.mp4` → finished MP4 |
| `scripts/check_video.sh` | Format, ticks + chime, speech-to-text of every answer, frame sheet |

## Episode format (same in every language, done by build.py)

- 1080x1920, 30 fps, 36.0 s, -14 LUFS, no background music.
- 0-1.5 s hook over clip 1: card "{TOPIC}" / "{LANGUAGE} {LEVEL}:" / "Can you get 6/6?". English narrator (`en-US-AndrewNeural`) at 0.1 s: "Can you get six out of six?"
- 6 words × 5.0 s, `n/6` top-left, clip keeps moving. Card in the upper third (center at 30 % height), so the object below it stays visible:
  - 0-2.0 s: English word; circle countdown 2-1 under the card, the ring empties each second, a tick at 0.0 and 1.0 s.
  - 2.0-2.2 s: reveal, fade + scale 92→100 %, one soft chime (means "here is the answer").
  - 2.2-5.0 s: answer (article in its gender color, always written) + IPA. Voice (`tts_voice`, -10 % rate) once at 2.3 s; when it ends, a gold "Listen & repeat" label and silence.
- 4.5 s end over clip 1 again (loops into the opening): 0-2 s recap of all 6 answers, then "What was your score?" / "0–6" / "Comment below" / "Next: {LANGUAGE} {NEXT_LEVEL} {NEXT_TOPIC}". Narrator at 2.1 s: "What was your score? Comment zero to six!" One ask only.
- A voice line that does not fit its part is spoken faster, never cut.

Change the format in `build.py` (constants at the top), not per episode.

## Steps

1. **Pick the episode.** Language, level, topic, next level and topic. Check `series.md`: the teaser must name an episode that will really be made. If the language has no file in `languages/`, create one first (see "New language").
2. **Pick the 6 words** and write `work/vocab/<language>-<level>-<topic>/words.txt` (repo root; one folder per episode), one per line in quiz order: `English | answer | pronunciation | scene`.
   - From the official list in the language file's `word_list` for this level, on the topic; nouns, singular, in the language file's `answer_form` and `pronunciation` format. Follow its `word_notes`.
   - One common answer per English word. No word whose meaning the scene cannot make clear.
   - Not in `log.md` → "Vocabulary" for this language (`fill_prompt.py` refuses repeats).
   - **scene**: one concrete shot where only this object can be meant, large and alone, without text on it. Good: `a single sheet of white paper lying flat on a wooden school desk, close-up`. Bad: `a library` for "dictionary" (any book), `a teacher at the blackboard` (she covers it).
3. **Fill the prompts:**
   ```bash
   W=work/vocab/german-a1-school
   python3 .claude/skills/vocab-quiz-video/scripts/fill_prompt.py --lang german --level A1 --topic School \
     --next-level A1 --next-topic Animals --episode 16 --words $W/words.txt --out $W
   ```
4. **Render the 6 clips** in the background, all at once (each ~5-15 min):
   ```bash
   for i in 1 2 3 4 5 6; do
     QUALITY=0 SIZE=9:16 DURATION=10 NO_OPEN=1 OUT_NAME=clip$i.mp4 \
       .claude/skills/muse-video/scripts/muse-video -f $W/clip$i.txt $W > $W/clip$i.log 2>&1 &
   done; wait
   ```
   `QUALITY=0`: the muse-video quality block is about people and lip sync; `clip-template.md` has its own rules.
5. **Check every clip** before the build. Make a sheet (3 frames per clip) and look at it:
   ```bash
   for i in 1 2 3 4 5 6; do ffmpeg -v error -y -i $W/clip$i.mp4 -vf "fps=0.4,scale=240:-1,tile=3x1" -frames:v 1 $W/sheet$i.png; done
   ```
   A clip passes if the object is clear and large in the lower two thirds in all frames, nothing covers it, there is no readable text, no morphing, and it looks like the country. Clip 1 also carries the hook and end card, so it should be the most beautiful one. For a failed clip: sharpen its scene line in `words.txt`, fill again, render only that clip with `RETAKE=1`. After 2 failed retakes, swap the word.
6. **Build:**
   ```bash
   uv run -q --no-project --python 3.12 --with edge-tts --with pillow \
     python .claude/skills/vocab-quiz-video/scripts/build.py $W videos/ep16-german-a1-school.mp4
   ```
   About 1 min. `SHEET=1` also writes a 1-frame-per-second sheet next to the MP4.
7. **Check:** `bash .claude/skills/vocab-quiz-video/scripts/check_video.sh videos/ep16-german-a1-school.mp4 de`. Expect ticks + chime at `[0.0, 1.0, 2.0]` for every word and each answer heard right. Look at the sheet.
8. **Report** to the user: file path, the 6 words, retakes, check results, and what still needs their ears/eyes (`series.md` → "Before posting").
9. **Log it.** If `log.md` does not exist, copy `log.template.md`. One row in "Content", six rows in "Vocabulary".
10. **Update `series.md`** (episode row + status) and, if something new was learned, the language file's "Lessons".

## New language

1. Copy `languages/_new-language.md` to `languages/<language>.md` and fill every front-matter key (`german.md` is the worked example). Required by the scripts: `language`, `lang_code`, `country`, `tts_voice`; `article_colors` for languages with gendered articles; `font_bold`/`font_regular` for scripts Noto Sans does not cover (CJK, Arabic).
2. Use the official word list for the level (DELE/Instituto Cervantes for Spanish, DELF/CEFR for French, HSK for Chinese, JLPT for Japanese, Goethe-Institut for German).
3. Pick the pronunciation aid learners use (IPA, pinyin with tone marks, romaji, ...).
4. Make one episode and fix the file from what the checks show.

## Gotchas

- edge-tts now and then answers `NoAudioReceived`; `build.py` retries 5 times.
- `check_video.sh` defaults to the 36 s layout. Old one-prompt episodes 1-14 (50 s): `HOOK=3 WORD=7 VOICE1=3.5 VOICE2=5.2`.
- Clips shorter than 6.5 s: word 1 starts clip 1 from 0 instead of continuing the hook; any clip shorter than 5 s freezes on its last frame. Ask for 10 s clips.
- Speech-to-text on a short clip can mishear a correct word; if one word fails, listen before changing anything.
