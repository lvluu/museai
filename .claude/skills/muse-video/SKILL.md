---
name: muse-video
description: Generate videos with muse.ai through this repo's museai server that pass a quality gate - real-looking, fluid continuous motion (no jitter, frozen frames, stitched-clip jumps), natural everyday conversation (precise lip sync, only the speaker's mouth moves, one steady pace), clean sound, and big synced captions placed clear of faces and platform UI; plus a travel-documentary mode (real places, natural light, slow camera, instrumental music, no narration or text). Use for every video request through museai - "make a video with muse", "create video", "EVERYDAY CHINESE #NN", people talking, travel / destination / landscape videos, multi-scene or long videos, or adding subtitles to a muse video.
---

# muse-video

Every video generated through museai follows this skill. Paths below are relative to this skill folder (`.claude/skills/muse-video/`).

Nothing is delivered until `scripts/qa.py` says PASS and the contact sheet looks right (or the user accepts a named failure):
1. **Looks real** - photoreal people and place, no AI artifacts (morphing, extra fingers, warped objects, garbled text).
2. **Fluid motion + continuity** - consistent anatomy, faces, clothes, lighting, object positions. No jitter, stutter, frozen or duplicated frames, flicker, sudden pose changes, sliding. One continuous take by default.
3. **Natural conversation** - attentive listeners, replies at the right moment with brief pauses, no overlap, no awkward delays. Only the speaker's mouth moves.
4. **Lip sync + sound** - every syllable matches lips and jaw, no drift; spoken words = script; clean dialogue, no clipping, music quiet.
5. **One steady pace** - normal everyday speed for the whole video; never rushed, stretched or slowed to fit the clip.
6. **Readable captions** - large, bold, high contrast, outlined, synced, short phrases, never covering faces, mouths, gestures or key objects.

## Style block (automatic)
`scripts/muse-video` appends one style block to every prompt (set `QUALITY=0` only to debug). Edit these files to change the rules for all future videos; don't paste the rules into each prompt.
- `prompt/quality.txt` (default) - people talking: motion / continuity / conversation / lip-sync / speech pace / acting / caption-safe composition / final check. The model renders no text; captions are burned in afterwards.
- `prompt/travel.txt` (`STYLE=travel`) - travel documentary: real geography and landmarks, natural grade and light, slow plausible camera, instrumental music + ambience, no narration, no text on screen.

## Server
- museai FastAPI on 127.0.0.1:18610 (`uv run python -m museai` in the repo root, in a visible terminal tab). Check: `lsof -nP -iTCP:18610 -sTCP:LISTEN`; not listening → start it, wait for "Application startup complete".
- Never print `data/api_key` or `data/accounts.json` (live muse.ai session cookies).
- `MUSE2API_VIDEO_TIMEOUT=1500` in `.env` (30-40 s videos take >10 min).
- Results also land in `data/media/vid_*.mp4`; copy each raw render into the working folder right away.
- Each account renders one video at a time; with N enabled accounts, N videos render in parallel. Extra requests queue for the next free account (`MUSE2API_MEDIA_QUEUE_TIMEOUT`, default 0 = no limit), so independent videos can be submitted at once. Sending the same prompt (and first frame) again while it is still queued or running returns the same task, not a second render: submit each clip once and wait for it. Clips of one multi-clip video still render in order (each needs the previous last frame).
- Add an account: export cookies from a logged-in https://muse.ai tab (Cookie-Editor JSON), then `uv run python scripts/import_account.py <export.json> --label muse-N` in the repo root (keeps only session cookies, checks the session). Delete the export afterwards. Every account is premium; never take one out of video jobs because of a bad render without proof.

## Before rendering: fit the script to the clip
`python3 scripts/budget.py script.txt <duration>` (a file with the dialogue lines only; run on the full prompt it counts every line and overshoots) - needs ≤ duration and ≥ 75 % of it at 4.5 syllables/s. TOO LONG → shorten the script (keep the meaning) or extend the clip. TOO SHORT or BELOW 30s MINIMUM → add a natural line (e.g. a closing reply); muse renders about as long as the speech, so asking for 30 s with 26 s of dialogue gives a 28 s video that fails QA. Never ask the model to speed up or slow down instead. Split lines over 14 syllables.

## Generate one clip
```
SIZE=9:16 DURATION=40 OUT_NAME=clip.mp4 NO_OPEN=1 scripts/muse-video -f prompt.txt
```
Output in `~/Movies/museai/`. The video length comes from the prompt: always set `DURATION`, and the script adds an OUTPUT line asking for exactly that many seconds in full HD 1080p (1080x1920 for 9:16). It prints the delivered length and size and never rejects or blocks a render. `IMAGE=first.png` sets the first frame. A busy account (`no_account_available`), a server restart (`interrupted`) or a down server are retried automatically (`RETRIES=15`, `RETRY_WAIT=120` s), so one call yields one finished video; run it in the background and don't resubmit by hand. If muse replies with text only (`upstream_refused`), prepend "NEW STANDALONE REQUEST. Ignore any earlier versions, drafts or projects. Generate one new video from scratch and return the finished video file in this reply. Do not reply with text only." and retry.

## Prompt (per video; the quality block is added for you)
Sections: CAST, SETTING, VOICE, CAMERA, SCRIPT.
- **CAST**: age, ethnicity, hair, exact outfit colours, voice type per person. "Keep faces, hairstyles, outfits, props and voices identical for the whole video."
- **SETTING**: one real, specific place with a few concrete objects that stay where they are.
- **VOICE**: language + accent, e.g. "Natural Standard Mandarin (Putonghua), accurate tones, warm everyday intonation, about 4.5 syllables per second for every line." Optional "very quiet instrumental music far below the dialogue", or none.
- **CAMERA**: default "One continuous take, steady locked camera, medium two-shot framed from the waist up, both bodies face the camera squarely, each person turns only the head partway toward the other (front three-quarter view, both eyes and the whole mouth visible, never side profile), faces large in the upper half of the frame." "Angled about 45 degrees toward the camera" still came back with the man in profile in 4 of 4 EP10 takes; "bodies face the camera squarely, turn only the head partway" held three-quarter faces and passed `lipsync.py` on the first take. Knees-up framing with the man nearly in profile gave EP10 weak, mumbled lips and a listener whose smile read as talking (`lipsync.py` failed 4 of 11 lines). Add a cut only if the user asks; give its time and what carries over.
- **Intro shot + cut** (e.g. a to-camera intro, then the two-shot): muse redraws the person after the cut and has aged or swapped faces (EP07: 40-year-old in the intro, 25-year-old at the desk). Pass `IMAGE=` a 9:16 still of that person (crop a frame of an earlier episode or render) and write "The woman in the attached image is the same woman in every shot: identical face, age, hairstyle and outfit."
- **Turn to camera at the end**: write "she turns her head and starts speaking within 0.3 s"; otherwise the turn adds a >1 s silent gap that fails the pace check. muse often ignores this and the "listener never looks at camera" rule (EP09: 6 of 6 takes had a 2-2.5 s pause before the turn and the man turned to camera too, three-quarter phrasing included). Plan the post fix below instead of a 4th re-render.
- **Faces toward the camera need a first frame**: the CAMERA text alone did not hold it (EP10 clip 2: "45 degrees, three-quarter, never profile" still came back in profile, and an `IMAGE=` of the woman alone made the camera drift to find the man). What worked: generate the two-shot still first, then render with `IMAGE=` it and "The attached image is the exact first frame: keep both faces, angles, framing and camera position." Still: `POST /v1/images/generations` with `{"prompt": ..., "n": 2, "size": "1080x1920", "response_format": "b64_json"}` (same CAST/SETTING text + "both bodies and faces angled about 45 degrees toward the camera, front three-quarter view, NOT side profile, framed from just below the waist up, mouths closed"), pick the one whose people match the earlier shots, scale to 1080x1920.
- **SCRIPT**: dialogue lines only, one per line with speaker label, in order.

## Short renders
muse has returned 10 s 720x1280 clips for 30 s requests (2026-10-26), on muse pro accounts, while replying "Generating your 30-second video". The OUTPUT line states the length and 1080p explicitly to steer it. If a clip still comes back short, tell the user the length and size the script printed; don't disable accounts for it. A first render that comes back 10 s with the whole script squeezed into it is unusable (rushed speech): switch to a multi-clip plan right away instead of retrying the single render (EP06: 30 s request -> 10 s clip with 8 of 12 lines).

## Multi-clip videos (continuity) - ALWAYS
The last frame of clip N-1 is the first frame of clip N.
1. **Plan in 10 s clips.** Split the script so each clip holds 7-8 s of speech (30-36 syllables, about 4 short lines, `budget.py part.txt 8` must say OK, not TOO SHORT), and each clip's prompt says `PART n of N`, 10 seconds, its own lines only. Put an intro cut in clip 1 and a turn to camera in the last clip. Render with `DURATION=10`. An under-filled clip gets padded with silence whatever the TIMING text says (EP09 clip 3: 21 syllables in 10 s -> 1 s lead-in + 2.3 s pause in every take; clip 1 with 3 lines had a 3.5 s silent tail). Move lines between clips until every clip is full, the last clip included.
   **One take at a time** (user rule): submit a clip once, check it, and only then re-render it if it fails. A re-render quotes the failing rule more strongly in the prompt. `muse-video` sends `X-Muse-Session` (`MUSE_SESSION`, default `$CLAUDE_CODE_SESSION_ID`), so the server runs one render per session at a time and queues the rest.
2. Render clip 1 normally; render every next clip with `CONTINUE_FROM=<previous clip>` (grabs its last frame as the first frame and prepends a CONTINUITY instruction).
3. Same cast, outfits, setting, lighting, camera position, action and gaze as the previous clip's ending. End each clip on a calm resting pose.
4. **Check every clip before chaining**: `scripts/check_clip.sh clip.mp4 [previous.mp4]` (cuts, transcript, sheet with the seam), then `lipsync.py` and `pron.py` on the clip with its own cues (below). Re-render the clip, before rendering the next one, if it has a cut you did not ask for, a person outside the cast (EP06: a shopper walked in behind them in the last 0.8 s, together with a second cut), words not in the script (EP06: the assistant answered the ending question with 合身的), or the listener turning to the camera with the speaker. Everything after a bad clip has to be re-rendered, so catch it here.
5. **Trim silence at the seams** (cutting the ends of a clip does not retime anything, so lip sync is kept): cut each clip about 0.4 s after its last syllable *before* using it as `CONTINUE_FROM` (EP06 clip 1 had 2 s of music-only tail), and cut a continued clip's silent lead-in (EP06 clip 3 started speaking at 2.5 s). The lead-in often drifts or zooms slightly, so cut as little as needed and check the seam again. `ffmpeg -t <end> -c:v libx264 -crf 16 ...` / `ffmpeg -ss <start> ...`.
6. **Fix cuts and pauses in post when re-renders keep failing** (`scripts/cutedit.py plan.json out.mp4`, segments of the clips joined with hard cuts; nothing is retimed):
   - Intro cut missing (EP09: 3 of 4 clip-1 takes stayed in the two-shot, man half in the intro): punch in on the speaker (crop of the two-shot) for the intro line, then cut to the full two-shot *inside the pause after it*, which also drops that pause.
   - Listener turns to camera at the ending, or a long pause before the last line: cut to a punch-in on the speaker inside that pause. This is an extra cut: tell the user it breaks "no further cuts" if the brief says so.
   - Choose crops so the chin stays above 57 % of the frame (captions sit at 57-75 %) and the other person is fully out; check with a frame grab.
   - Pauses inside one continuous take cannot be cut without a jump: re-render that clip or name the failure.
   - Find cut points with `python3 scripts/gaps.py video.mp4` (energy-based speech spans and gaps).
   - Trimmed pauses shorten the video: if it falls under 30 s, add a natural line (needs the user's OK when the brief fixes the script) rather than leaving pauses in.
7. Join with `scripts/stitch.sh out.mp4 part1.mp4 part2.mp4 ...`: denoises each clip (`afftdn`; EP10 clips 2-4 came back with a white hiss floor at -51 dB above 7 kHz, which loudness matching raised to an audible -46 dB; the clean clip sat at -86 dB), drops the duplicate first frame and cuts each clip's audio to its kept frames (EP10: trimmed clips carry up to 25 ms more audio than video, and the dropped frame's audio stayed in; both pushed later clips' voices off their lips and left the join at 23.8 fps), scales every clip to the first one's size (muse returned clip 2 of a 1080p chain at 720x1280), and evens out loudness between clips (EP06 clips came back 8 dB apart). Subtitle and QA the stitched file.

## Timing, QA, captions
1. **Word timings**: `WMODEL=medium uv run --no-project --python 3.12 --with faster-whisper --with opencc-python-reimplemented python scripts/transcribe.py video.mp4 words.json` (no hint first: the script hint can make Whisper skip or invent lines; add it only if words are misheard). Word starts absorb leading silence, so tighten cue bounds with `scripts/gaps.py` (energy-based) before judging pace. Missed lines → cut that span to wav and rerun with `VAD=0`.
2. **cues.json**: `[[speech_start, speech_end, line1, line2, ...], ...]` from the word timings (EVERYDAY CHINESE: zh, pinyin, vi). One short, meaningful phrase per cue.
3. **QA gate**: `python3 scripts/qa.py video.mp4 cues.json words.json [planned_cuts=0] sheet.jpg`
   - format 1080x1920, 30–40 s, constant 24–30 fps
   - voice: transcript vs script ≥ 90 %
   - sound: peak < -0.5 dB, mean > -30 dB
   - noise: hiss floor above 7 kHz < -70 dB (only voices + music; `stitch.sh` denoises, a raw clip that fails is fine once stitched)
   - pace: every line 3.8–5.5 syllables/s, fastest ÷ slowest ≤ 1.35, no pause > 1.0 s
   - smooth: no freeze ≥ 0.5 s, ≤ 5 % repeated frames, hard cuts == planned
   - contact sheet: every tile real, same faces/outfits/background, normal hands, only the speaker's mouth open
   - **pronunciation** (Mandarin): `uv run --no-project --python 3.12 --with faster-whisper --with pypinyin --with opencc-python-reimplemented python scripts/pron.py video.mp4 cues.json` transcribes each line on its own and compares toned pinyin with the script; any missing or changed syllable/tone fails (a homophone with the same tones passes, 了→啦 particle swaps pass). Uses Whisper large-v3; medium flagged correct lines. A line that fails in a clip can often be moved to the next clip instead of re-rendering the whole clip (EP10: 竖 said as 收 in the last line of clip 2; clip 2 was cut after line 3 and the line opened clip 3).
   - **lip sync**: `uv run --no-project --python 3.12 --with "mediapipe==0.10.14" --with opencv-python-headless python scripts/lipsync.py video.mp4 cues.json <speakers> [cut times]` (speakers: one letter per cue, C = solo/intro shot, L/R = left/right person in the two-shot, e.g. `CLRLRLRLRLL 3.17`). Per line, the speaker's lip gap must open and close (osc ≥ 4) and the listener's must stay under half of that. Needs faces in front three-quarter view; a profile face is not tracked.
   - FAIL → re-render with the failing rule quoted more strongly in the prompt. Never retime audio in post (breaks lip sync). After 2 failed re-renders, deliver the best one and name the failed checks.
4. **Burn captions**: `uv run --no-project --python 3.12 --with pillow python scripts/burn_subs.py video.mp4 cues.json out.mp4`
   - Large bold white text, thick dark outline. Chinese 112 px, Latin 66 px.
   - Single-language video: at most two lines on screen. EVERYDAY CHINESE: one line per language (zh / pinyin / vi), each kept to one row by short cues.
   - Box x6–84 %, y57–75 %, block centred near 66 %; bottom 25 % and right-side buttons stay clear. Fixed position, no bouncing or flashing. Shown 0.15 s before speech, until 0.7 s after or the next cue.
5. **Verify** frame grabs with captions at several cue times: text inside the box, no face, mouth, gesture or key object covered. Then deliver.

## Travel videos (`STYLE=travel`)
Real destination, no dialogue, no captions. Rules 3-6 above don't apply; rules 1-2 do.
1. **Prompt** sections: PLACE, TIME + WEATHER, SHOTS, MUSIC.
   - **PLACE**: real named location + the concrete landmarks/terrain actually there (e.g. "Ha Long Bay, Vietnam: limestone karsts rising from emerald water, wooden junk boats"). Never ask for things that are not there.
   - **TIME + WEATHER**: one time of day and weather for the whole clip (e.g. "early morning, light mist, soft low sun from the left").
   - **SHOTS**: default one continuous shot with one slow move (drone push-in, slow pan, gentle dolly). Multiple shots only if asked; list them in order with the move per shot.
   - **MUSIC**: instrument + mood matching the place (e.g. "soft đàn bầu and strings, calm"), plus the ambience (waves, birds, wind).
2. **Render**: `STYLE=travel SIZE=16:9 DURATION=10 OUT_NAME=place.mp4 NO_OPEN=1 scripts/muse-video -f prompt.txt` (`SIZE=9:16` for shorts). Longer → multi-clip with `CONTINUE_FROM`, same as above.
   - **Asked for more than 10 s, muse may join its own clips**: a 15 s Lauterbrunnen request (2026-10-26) came back 15 s 1080x1920, but at 10.04 s it cut back to ground level with different light (qa: `cuts at [10.04]`). Keep the good part up to the cut (`ffmpeg -t <cut>`) and render the rest as a `CONTINUE_FROM` clip instead of re-rendering the whole video.
   - **Continued clips start reframed**: the first frame of a `CONTINUE_FROM` clip is slightly shifted and zoomed against the given frame, so the join jumps for one frame (frame difference 14 vs ~5 elsewhere, below the hard-cut threshold, so qa still passes). A re-render with "first frame pixel-identical, no reframing" jumped the same. Check the seam with `signalstats` YDIF; on a jump, join the two clips with a 0.5 s `xfade` + `acrossfade` instead of `stitch.sh` (the video gets 0.5 s shorter; say so on delivery). Travel only: a crossfade over speech would blend two mouths.
   - **"No zoom" still gets a push-in**: asked for a near-static lateral glide with "no zooms, no change in shot size, 2-3 m travel", a 15 s Lake Bled render (2026-10-26) pushed in over the first ~7 s (island ~2x bigger, foreground reeds left the frame), then held; qa passes this, so judge shot size on the contact sheet. Adding "slider at water level, constant focal length, never moves forward or backward, never zooms, the island stays exactly the same size in every frame, foreground trees and reeds stay in frame" halved it (island ~1.5x, reeds kept) but did not remove it. Use that wording from the first render, and tell the user about any push-in left.
3. **QA**: `python3 scripts/qa.py video.mp4 --travel [planned_cuts=0] sheet.jpg` - format 1920x1080 or 1080x1920, 8-40 s, 24-30 fps; no clipping, mean > -35 dB; smooth as above. Contact sheet (12 even frames): real place, no invented landmarks, warped buildings, repeated mountains, HDR halos, text or watermarks; same light and weather throughout. FAIL → re-render with the failing rule quoted more strongly.
4. No captions, no burn step. Deliver after PASS + sheet check.

## Maintaining this skill
Agents update this skill directly, without asking, whenever a render, QA run or user correction teaches something new: fix the rule here, in `prompt/*.txt` or in `scripts/`, commit on a branch, open a PR, and copy the changed files to `~/.claude/skills/muse-video/` so the installed copy stays in sync. Record only lessons proven by a render, not guesses.
