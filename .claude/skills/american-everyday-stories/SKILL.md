---
name: american-everyday-stories
description: Develop and produce "American Everyday Stories" - an ongoing photorealistic 16:9 drama series about ordinary life in twentieth-century America (default The Larkmont Years, a fictional Pennsylvania small city from autumn 1985), with recurring original characters (attractive, distinctive faces that resemble no real person), natural American English dialogue at a real conversational pace, period-exact details, the warm 1980s film look of the user's reference, and bilingual English-over-Simplified-Chinese subtitles. Each 120-180 s episode is one complete small story. Delivers the series bible, episode scripts and per-shot generation prompts, and renders, assembles, subtitles and checks the film through museai/muse-video. Use for "American Everyday Stories", "Larkmont", "next episode", "continue" in this series, "1980s America short film", "everyday America story with Chinese subtitles", "make a video like the Highlands Ranch 1987 one", or any request for a recurring period slice-of-life series in America.
---

# American Everyday Stories

Fictional, historically plausible slice-of-life films about everyday America. Paths are relative to
this skill folder (`.claude/skills/american-everyday-stories/`). Rendering, server, retries, dubbing
and delivery reuse `../muse-video/` (read its SKILL.md: Server, Generate one clip, Multi-clip, Deliver).
This skill keeps only what is specific to the series.

| file | what it holds |
|---|---|
| `series/bible.md` | default series: premise, world, places, vehicles, relationships, first ten episodes |
| `series/cast.json` | every recurring character: identity (face), wardrobe sets, voice, TTS voice, speaker letter |
| `series/ledger.json` | episode ledger + user corrections; `episode.py check` reads it, `record` appends |
| `references/look.md` | colour, cutting, text and sound measured from the user's reference film |
| `references/faces.md` | how to design an original, beautiful, consistent face; reference stills |
| `references/period-1985.md`, `anachronisms.json` | period checklist and the lint list |
| `prompt/look.txt` | period look + filming + performance block, appended to every shot prompt |
| `templates/episode.template.json` | episode file shape (two example shots) |
| `scripts/episode.py` | `check` gates, `build` prompts/subtitles/package/render.sh, `still`, `record` |
| `scripts/assemble.py` | `cut` shots → graded film + cut.json; `mix` music bed ducked under speech |
| `scripts/align.py` | Whisper (English) → words.json, cues aligned to the real speech |
| `scripts/qa_episode.py` | the gate: format, sound, cuts, words, pace, smooth, voices, contact sheet |
| `scripts/refs.sh` | character reference still candidates through museai |
| `scripts/finish.py` | title card + EN/中文 subtitles burned in, final .srt/.vtt |

## Ground rules
- **Fiction**: invented people, businesses and events in a plausible setting. Never call an episode a
  true story; real public events (a World Series) are background only, after verifying them.
- **Default setting** unless the user names another: The Larkmont Years, Larkmont, Pennsylvania, from
  Monday 14 October 1985, time moving forward. Another setting → a new folder `series/<slug>/` with
  its own bible, cast and ledger (`SERIES=series/<slug>` for every script), made the same way.
- **Presentation**: photorealistic live action, 16:9 1920x1080, English speech only, subtitles English
  above Simplified Chinese. A 9:16 version only when asked (reframe each shot, captions re-laid).
- **Faces**: attractive, specific, original (`references/faces.md`). Never name or describe a real actor,
  never "looks like". Each face carries 2-3 marks on a named side; they come from cast.json verbatim.
- **No pretending**: say a video, audio or subtitle file exists only when a tool made it. Missing
  reference stills or voices are named (`episode.py build` prints `MISSING REFS`), never assumed.
- **Continuity is a file**: the bible, cast and ledger are the memory. Never claim to remember an
  episode that is not in the ledger; if one is missing, ask for its continuity summary.

## Commands
- **"Start the series" / first use**: present the bible (`series/bible.md` + the cast table) in short
  form and offer the reference stills. Don't write Episode 1 until asked.
- **"Episode N" / "make episode N"**: write the episode (below), check, build, deliver the package; render
  only when the user asks for the video (or says "make the video").
- **"Continue"**: next number after the ledger's last episode, a fresh situation from the plan or a new
  one, same facts. A situation, main place set or story shape used in the last three episodes is out.
- **Corrections** ("Walt would never say that", "Nora's hair is shorter"): change cast.json / bible.md,
  add a line to `ledger.json` `corrections` with the date, apply from the next episode. Never rewrite
  earlier episodes silently.

## Writing an episode
Work in `~/Movies/museai/aes-epNN/` (`WORK`). Copy `templates/episode.template.json` to
`WORK/episode.json` and fill it.
1. **Situation**: one ordinary, specific problem (a missed bus, a first day, a broken car, an awkward
   lunch, groceries, a family disagreement, a drive, a motel, a favour, an office mix-up). Different
   from the last three ledger entries in situation and main places.
2. **Beats** (`beats`, all required): `opening` hooks in the first 5-10 s with an action or a line that
   raises a question (never a greeting or exposition); `goal` immediate; `obstacle` small; `turn` a
   believable emotional shift; `ending` a resolution or quiet closing image, no forced cliffhanger.
   Interest comes from choices, subtext, humour and recognisable details. Not every life is the
   same, the past is not idyllic, nobody is a type.
3. **Dialogue**: short, idiomatic 1985 American English in each character's voice (cast.json). Subtext,
   interruptions of thought, no speeches, no teaching lines, no internet-era words (`check` lints them).
   ~220-330 words for 150 s; `check` computes the real budget at 145 wpm with pauses and fails any
   shot whose lines do not fit. Fix by cutting words or splitting the shot, never by faster speech.
4. **Chinese**: natural Simplified Chinese with the same meaning, tone, humour and relationship
   (terms of address, 宝贝/亲爱的 only when the English is that warm); add nothing, no pinyin. Names:
   诺拉, 露西, 沃尔特, 丹尼, 格蕾丝, 伊芙琳; the town 拉克蒙特. ≤ 36 characters per line.
5. **Shots**: 16-28 shots of 3-10 s (one muse render each), one clear action or short exchange each.
   Rhythm from the reference: open on 1-2 wide establishing views with the title card, cut every
   5-7 s, a few unpeopled atmosphere shots (street, interior, detail insert) between scenes. Dialogue in
   stable two-shots or medium shots with both mouths visible (front three-quarter; through a
   windshield; across a counter); never a speaker filmed from behind (muse moves the line to the
   visible mouth). Close-ups rare; slow motivated tracking only now and then. Keep screen direction:
   who sits left stays left; the car drives the same way across cuts; props stay put.
6. **Fields per shot**: `place`, `time`, `framing`, `cast`, `wardrobe` (keys of cast.json), `action`,
   `camera`, `ambience`, `lines` (`who`, `en`, `zh`, optional `delivery`, `listener`), `props`,
   `continuity`. Period details named concretely (`references/period-1985.md`): the car model and
   colour, the phone, the register, the clothes. No readable brands, plates or headlines.
7. **Check**: `python3 scripts/episode.py check WORK/episode.json` until no ERROR; read every WARN.
   Then the quality questions it cannot answer: is the small story complete and engaging, is each
   line something this person would say in 1985, is the Chinese accurate and natural, is this
   distinct from recent episodes?

## Package (what the user gets)
`python3 scripts/episode.py build WORK/episode.json WORK` writes `package.md` (Vietnamese title +
one-line premise; episode number, date, place, runtime, cast; beats; timed scene plan with EN and
中文; each shot prompt; provisional subtitle timing; sound/editing notes; continuity update),
`shots/<ID>.prompt.txt` (self-contained English generation prompts: duration, framing, characters'
identity and wardrobe, exact place/year/time, action, camera, timed dialogue with speaker and
listener instructions, ambience, continuity, the look block), `subs.provisional.srt/.vtt`
(labelled provisional), `title.json`, `speakers.txt` and `render.sh`. Show `package.md` (send the
file) and summarise; production notes stay out of the dialogue.

## Reference assets (before the first render)
- **Character stills**: in `series/refs/` for all six (`<KEY>.jpg` 16:9, `<KEY>_face.jpg` square);
  reuse for every episode. New or changed face: `scripts/refs.sh KEY OUT` and the checks in
  `references/faces.md` (age, sides, extra marks).
- **Shot stills**: for each shot with a recurring character, make a 16:9 first frame through
  `/v1/images/generations` from the shot prompt's CAST + FRAMING + place (plus "matches the attached
  references"), pick the take whose faces match the refs, save `WORK/stills/<ID>.png`. render.sh
  uses it as `IMAGE=`. Faces drift without it (muse-video "Faces toward the camera need a first frame").
- **Voices**: each character's `tts` voice in cast.json is the voice identity (muse picks a new voice
  per render, so the film is dubbed; see below).

## Render and assemble
1. Server up (muse-video "Server"). `WORK/render.sh` renders every shot in parallel, one call each,
   `OUT_NAME=aes-epNN-<ID>.mp4`, retries built in; run it in the background. muse-video appends its
   quality block (lip sync, listener, pace) after this skill's look block.
2. **Check each clip** (`../muse-video/scripts/check_clip.sh clip.mp4`): wrong face, outfit or period
   detail, extra cut, a person speaking without lips, words not in the script, garbled text → re-render
   that shot once with `RETAKE=1` and the failing rule stated more strongly; after two failures use the
   best take and name the problem. Pick each shot's best window into `WORK/trims.json`
   (`{"S04": [0.3, 7.6]}`; trim only silence at the ends, never inside speech).
3. `python3 scripts/assemble.py cut WORK WORK/episode.json WORK/film.mp4`: hard cuts, 1920x1080 24 fps,
   the reference grade (`references/look.md`) on every shot alike, audio levelled not retimed.
4. Align: `uv run --no-project --python 3.12 --with faster-whisper python scripts/align.py WORK/film.mp4 WORK`.
   Fix any UNMATCHED / PARTIAL line (missing words → re-render that shot).
5. **Dub** one fixed voice per character (cast.json `tts`, letters from line 1 of `speakers.txt`):
   `VOICE_N=en-US-AvaNeural VOICE_L=en-US-AnaNeural VOICE_T=en-US-GuyNeural VOICE_D=en-US-AndrewNeural VOICE_G=en-US-JennyNeural VOICE_E=en-US-EmmaNeural MUSIC=0 uv run --no-project --python 3.12 --with edge-tts --with librosa --with soundfile python ../muse-video/scripts/dub.py WORK/film.mp4 WORK/cues.json $(head -1 WORK/speakers.txt) WORK/dubbed.mp4`,
   then run step 4 again on `WORK/dubbed.mp4` so `words.json` and `cues.json` follow the new voices
   (keep the first `cues.json` as `cues.lips.json`). Skip only
   if the user accepts muse's voices; qa's `voices` check decides. Locations with ambience: dub.py
   keeps no muse music (MUSIC=0); the ambience comes back with the bed below.
6. **Music**: an original era-compatible instrumental bed (soft mid-80s: electric piano, chorus guitar,
   warm synth pad, light drum machine, 80-96 BPM; folk/acoustic for a rural episode; nothing that
   imitates a known song). `uv run --no-project ../muse-video/scripts/music.py --engine musicgen --style "<style>" --bpm 88 --body-beats <beats for the film> --out WORK/music.m4a`
   (MusicGen weights are CC-BY-NC: personal posts only; say so if the user monetises), or a
   user-supplied licensed track. `python3 scripts/assemble.py mix WORK/dubbed.mp4 WORK/music.m4a WORK/mixed.mp4`
   (bed at -20 dB, ducked under every line; no canned laughter, few effects).

## QA, subtitles, delivery
1. `python3 scripts/qa_episode.py WORK/mixed.mp4 WORK WORK/sheet.jpg` → PASS, then look at the sheet:
   same faces and marks on the named side, same wardrobe, period-correct objects, listeners' lips
   closed, no garbled text. Deliver nothing on FAIL unless the user accepts the named failure.
2. `uv run --no-project --python 3.12 --with pillow python scripts/finish.py WORK/mixed.mp4 WORK WORK/aes-epNN-<slug>.mp4`
   burns the title (`title.json`) and the EN/中文 subtitles and writes the matching .srt/.vtt (final,
   aligned). Grab frames at several cue times: no subtitle covers a face, mouth or key action; if one
   does, shorten that cue (split the line) and rerun.
3. Preview (`SendUserFile`, render), then on the user's OK deliver with
   `FINAL=1 ../muse-video/scripts/deliver.sh` as muse-video describes (thumbnails, captions, cleanup),
   and `python3 scripts/episode.py record WORK/episode.json` **before** FINAL=1 (it trashes WORK).
4. Quality check before saying "done": runtime 120-180 s with speech at natural pace; a complete small
   story; consistent history and characters; accurate bilingual meaning; clear speakers and lip sync;
   feasible shots and smooth continuity; a setting and conflict distinct from recent episodes.

## Maintaining this skill
Same flow as muse-video "Maintaining this skill" (branch from origin/main, PR, merge). Encode a lesson
as a check in `episode.py` / `qa_episode.py` or a line in `anachronisms.json` / `look.txt` / cast.json,
not as more prose. Record only lessons proven by a render or a user correction.
