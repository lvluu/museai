---
name: place-story
description: Make a 45-60 s vertical travel story of one real place that teaches while it shows - a hook question on the wow view, then 8 or so beats, each a muse shot of a real landmark with a documentary fact card (history, records, legends, film locations, "why is it like this?"), the hook's answer revealed mid-video, soft dissolves, a calm instrumental bed in the country's own instruments, and a save/follow card at the end. Use when the user wants a travel video that is longer, tells the history or interesting facts of a place, "shows information about the place", "facts about X", "story of X", "did you know X", "history of X video", or wants viewers to stay longer than a 10-18 s reel. Takes the shared brief (muse-video "Format skills"); files are named story-<slug>.
---

# place-story

Paths are relative to this folder (`.claude/skills/place-story/`). Rendering, server, the brief, music engine, shot history, QA and delivery come from `../muse-video/SKILL.md` ("Format skills" shared steps, "Music"); shots render through `../scenic-drop-reel/scripts/shot` (aerial and gimbal rules in its `prompt/drone.txt`). This skill adds the story script and the fact-card composer. Name everything `story-<slug>`.

## Why it holds viewers (keep for every story)
- **Hook = an open question on the wow view**, readable from frame 0, answered later (Angkor: "Why does the world's biggest temple face west? 🤔" → answered in fact 4 of 8, kicker "the answer"). The viewer stays to get the answer. It must be true and answerable from the facts.
- **Hook text never covers the landmark**: it sits at the top of the safe zone over sky; when the landmark fills the top (Angkor towers, 2026-11-09), set `"pos": "low"` on the hook beat to put it over the water or foreground.
- **A visible count** in each kicker ("Fact 3 of 8") so viewers know how much is left; put the answer around the middle and the most surprising fact last but one.
- **One fact per shot, the shot shows the fact**: the card about carvings sits on the carvings, the moat fact on the moat. A fact with no matching shot does not go in.
- **End card**: one last emotional fact + a `cta` pill ("Save it for your trip ✈️"); saves and follows count more than likes.

## Facts must be true
Every beat carries `src` (where the fact comes from: UNESCO, Britannica, Guinness, a paper). Use well-documented numbers and say "about", "nearly", "many scholars think" where sources differ. Never invent records, dates or legends; leave a fact out rather than guess.

## Steps
0. **Earlier shots**: shared step 1 (`../shot-history/scripts/shots.py check`).
1. **Script** `story.json` in the work folder `~/Movies/museai/story-<slug>/` (shape in `scripts/compose.py`'s docstring): `place`, `sub` (country + flag), `beats` = 1 hook + 7-9 facts + 1 end. Titles ≤ 6 words, bodies ≤ 25 words; `compose.py` gives each beat its reading time (1.6 s + 2.6 words/s, 4.5-8 s, hook 3.8 s), so the story lands at 45-60 s.
2. **Shots**: one per beat, each a different real subject (wide aerial ↔ close gimbal detail alternating), the same light family for all but a sunset finale. 8 s each (`DURATION=8`: the longest beat needs 8.7 s with its dissolve, the clip is slowed at most ~10 %). Jobs in `jobs.txt`, ONE `../muse-video/scripts/render-queue jobs.txt` call. Write absolute output paths (a `~` in the jobs file makes render-queue write logs under a literal `./~/` folder).
3. **Music** (after the shots, same machine rule): calm instrumental in the country's instruments, as long as the story:
   ```bash
   uv run --no-project ../muse-video/scripts/music.py --style "<calm cinematic documentary, local instruments, warm strings, soft hand drums>" --bpm 84 --body-beats <ceil(seconds*84/60)+4> --out ~/Movies/museai/story-<slug>/track.m4a
   ```
3b. **Narration** (the story teaches, so it is spoken too): each beat gets a `vo` line, one or two short sentences in a calm documentary voice, same fact as the card, hook question asked in the first beat and answered mid-video, ending on the cta. Put spelling for the voice in `say` ("Pnom Koolen", "Bai-yon", years as words). Then:
   ```bash
   uv run --no-project --python 3.11 --with "kokoro>=0.9" --with soundfile --with "misaki[en]" python scripts/vo.py story.json
   ```
   (Kokoro, local; `--voice af_heart` default, `am_michael`, `bf_emma`. edge-tts stays banned.) Beats then last line + 0.9 s (about 6-8.5 s each, story ~75 s), so size the music from `compose.py --dry` (`--body-beats` it prints) instead of the reading-time estimate in step 3.
4. **Check each shot**: shared step 5 (`qa.py sN.mp4 --travel 0 sheetN.jpg`). Re-render a shot that shows a fake landmark, text or the wrong subject for its fact.
5. **Compose**:
   ```bash
   uv run --no-project --python 3.12 --with pillow --with fonttools python scripts/compose.py \
     --story ~/Movies/museai/story-<slug>/story.json --music track.m4a --out ~/Movies/museai/story-<slug>/story-<slug>.mp4
   ```
   Per beat it takes the steadiest window of the clip, lifts a dark shot, lays the card (fades in 0.45 s after the cut, out before the dissolve), then joins beats with 0.7 s dissolves under one music bed that ducks under the voice-over (voice ~9 dB above the bed, two-pass loudnorm to -14 LUFS; one-pass loudnorm lifts the bed in the pauses). Cards stay inside the feed safe zone (top 230, bottom 430, right 150 px).
6. **Verify**: contact sheet (`ffmpeg -i story-<slug>.mp4 -vf "fps=1/2,scale=180:-1,tile=8x4" -frames:v 1 sheet.png`): hook readable on frame 0, every card legible and matching its shot, no muse text, length 45-60 s.
7. **Deliver**: shared step 7 (thumbnail with the hook question, captions whose first line is the hook, shot-history record before `FINAL=1`).

## Maintaining this skill
Same rules as `../muse-video/SKILL.md` "Maintaining this skill": a lesson proven by a render or the user's feedback goes into this file or `scripts/compose.py`, not into one story.
