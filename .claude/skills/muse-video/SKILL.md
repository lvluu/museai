---
name: muse-video
description: Generate videos with muse.ai through this repo's museai server that pass a quality gate - real-looking, fluid continuous motion (no jitter, frozen frames, stitched-clip jumps), natural everyday conversation (precise lip sync, only the speaker's mouth moves, one steady pace), clean sound, and big synced captions placed clear of faces and platform UI. Use for every video request through museai - "make a video with muse", "create video", "EVERYDAY CHINESE #NN", multi-scene or long videos, or adding subtitles to a muse video.
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

## Quality block (automatic)
`prompt/quality.txt` holds the motion / continuity / performance / lip-sync / speech / acting / composition / final-check requirements. `scripts/muse-video` appends it to every prompt (set `QUALITY=0` only to debug). Edit that file to change the rules for all future videos; don't paste the rules into each prompt.

## Server
- museai FastAPI on 127.0.0.1:18610 (`uv run python -m museai` in the repo root, in a visible terminal tab). Check: `lsof -nP -iTCP:18610 -sTCP:LISTEN`; not listening → start it, wait for "Application startup complete".
- Never print `data/api_key` or `data/accounts.json` (live muse.ai session cookies).
- `MUSE2API_VIDEO_TIMEOUT=1500` in `.env` (30-40 s videos take >10 min).
- Results also land in `data/media/vid_*.mp4`; copy each raw render into the working folder right away.
- One account → one render at a time.

## Before rendering: fit the script to the clip
`python3 scripts/budget.py script.txt <duration>` - needs ≤ duration and ≥ 75 % of it at 4.5 syllables/s. TOO LONG → shorten the script (keep the meaning) or extend the clip. TOO SHORT → add a line or shorten the clip. Never ask the model to speed up or slow down instead. Split lines over 14 syllables.

## Generate one clip
```
SIZE=9:16 DURATION=40 OUT_NAME=clip.mp4 NO_OPEN=1 scripts/muse-video -f prompt.txt
```
Output in `~/Movies/museai/`. `IMAGE=first.png` sets the first frame. If muse replies with text only (`upstream_refused`), prepend "NEW STANDALONE REQUEST. Ignore any earlier versions, drafts or projects. Generate one new video from scratch and return the finished video file in this reply. Do not reply with text only." and retry.

## Prompt (per video; the quality block is added for you)
Sections: CAST, SETTING, VOICE, CAMERA, SCRIPT.
- **CAST**: age, ethnicity, hair, exact outfit colours, voice type per person. "Keep faces, hairstyles, outfits, props and voices identical for the whole video."
- **SETTING**: one real, specific place with a few concrete objects that stay where they are.
- **VOICE**: language + accent, e.g. "Natural Standard Mandarin (Putonghua), accurate tones, warm everyday intonation, about 4.5 syllables per second for every line." Optional "very quiet instrumental music far below the dialogue", or none.
- **CAMERA**: default "One continuous take, steady locked camera, medium two-shot, both people fully in frame, faces in the upper half of the frame." Add a cut only if the user asks; give its time and what carries over.
- **SCRIPT**: dialogue lines only, one per line with speaker label, in order.

## Multi-clip videos (continuity) - ALWAYS
The last frame of clip N-1 is the first frame of clip N.
1. Render clip 1 normally; render every next clip with `CONTINUE_FROM=<previous clip>` (grabs its last frame as the first frame and prepends a CONTINUITY instruction).
2. Same cast, outfits, setting, lighting, camera position, action and gaze as the previous clip's ending. End each clip on a calm resting pose.
3. Render sequentially; check each seam (`ffmpeg ... hstack` of last/first frame); visible jump → re-render clip N.
4. Join with `scripts/stitch.sh out.mp4 part1.mp4 part2.mp4 ...` (drops the duplicate first frame). Subtitle and QA the stitched file.

## Timing, QA, captions
1. **Word timings**: `WMODEL=medium uv run --no-project --python 3.12 --with faster-whisper python scripts/transcribe.py video.mp4 words.json "<full script>"`. Missed lines → cut that span to wav and rerun with `VAD=0`.
2. **cues.json**: `[[speech_start, speech_end, line1, line2, ...], ...]` from the word timings (EVERYDAY CHINESE: zh, pinyin, vi). One short, meaningful phrase per cue.
3. **QA gate**: `python3 scripts/qa.py video.mp4 cues.json words.json [planned_cuts=0] sheet.jpg`
   - format 1080x1920, 30–40 s, constant 24–30 fps
   - voice: transcript vs script ≥ 90 %
   - sound: peak < -0.5 dB, mean > -30 dB
   - pace: every line 3.8–5.5 syllables/s, fastest ÷ slowest ≤ 1.35, no pause > 1.0 s
   - smooth: no freeze ≥ 0.5 s, ≤ 5 % repeated frames, hard cuts == planned
   - contact sheet: every tile real, same faces/outfits/background, normal hands, only the speaker's mouth open
   - FAIL → re-render with the failing rule quoted more strongly in the prompt. Never retime audio in post (breaks lip sync). After 2 failed re-renders, deliver the best one and name the failed checks.
4. **Burn captions**: `uv run --no-project --python 3.12 --with pillow python scripts/burn_subs.py video.mp4 cues.json out.mp4`
   - Large bold white text, thick dark outline. Chinese 112 px, Latin 66 px.
   - Single-language video: at most two lines on screen. EVERYDAY CHINESE: one line per language (zh / pinyin / vi), each kept to one row by short cues.
   - Box x6–84 %, y57–75 %, block centred near 66 %; bottom 25 % and right-side buttons stay clear. Fixed position, no bouncing or flashing. Shown 0.15 s before speech, until 0.7 s after or the next cue.
5. **Verify** frame grabs with captions at several cue times: text inside the box, no face, mouth, gesture or key object covered. Then deliver.
