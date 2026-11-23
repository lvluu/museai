---
name: curious-mechanism
description: Make a video for The Curious Mechanism (@curiousmechai) - a faceless, AI-illustrated educational channel that explains the hidden engineering, design decisions and strange history of everyday things, in a clean 2D cartoon look (bold outlines, flat colours, cel shading, expressive characters, teal / amber / cream with red for danger). Every story opens on what went wrong (an accident, a failure, a near miss) and then explains why. Long-form 8-12 min 16:9 mini-documentaries (one a week) and 30-55 s 9:16 Shorts (complete mini-stories), built from one episode.json - verified claims with 2 sources each, a script for the ear, illustrations through museai animated scene by scene with muse video, one fixed narrator voice, editorial labels drawn in the edit, a 1280x720 thumbnail drawn by muse and a QA gate. Use for "Curious Mechanism", "curiousmechai", "why are airplane windows round", "how X actually works", "hidden engineering of X", "everyday engineering video", "explainer like the airplane window one", or the next episode or Short of this channel.
---

# curious-mechanism

Paths are relative to this folder. Script: `scripts/cm.py` (run with
`uv run --no-project --python 3.12 --with edge-tts --with pillow python scripts/cm.py ...`).
The full channel playbook is in `playbook/` (`PLAYBOOK.md`, `brand/style-guide.md`, `templates/`,
`research/topic-backlog.md`, `production/001-airplane-windows/`). The channel kit (handle, bios, art) is
`../new-channel/channels/curious-mechanism/`. Never print `data/api_key` or `data/accounts.json`.

**Honesty rule**: never say a video, file or check exists or passed unless the command that makes it ran
and its output says so. Never put a fact into narration that is not a verified claim with 2 sources.

## The channel in five lines
- One video answers one question an ordinary viewer never thought to ask ("Why are airplane windows round?").
- Pillars: Everyday Engineering + Invisible Systems ~80 %, Strange Origins ~15 %, Forgotten Mechanisms ~5 %.
- Look: clean 2D cartoon, like a good animated educational series (`prompt/look.txt`, `prompt/avoid.txt`):
  bold outlines, flat colours with soft cel shading, expressive characters, deep teal, warm amber, cream,
  red only for danger or the key part, subject filling the frame. Never photoreal. No text inside
  generated images: labels are drawn in the edit. (2026-11-13: replaces the playbook's engraving look, which
  was faded on a phone; picked over a cinematic painted look after a side-by-side test of s002.)
  Change the look in those two files only. `CM_LOOK=painted` renders the old painted look
  (`prompt/look-painted.txt`) into its own work folder `<id>--painted` for comparison.
- Story = problem, then the engineers' solution (user rule 2026-11-21, model episode: s003 v2 "How do we
  protect internet cables from underwater avalanches?"). Tell a good story that leads the viewer into a real
  problem; let the problem lead to the solution engineers actually use; end on a twist and the viewer's own
  everyday object. The opening does not have to be an accident or a shock: any real problem told well works
  (an accident, a failure, a myth, a limit of nature, a daily nuisance). The video teaches what the viewer
  did not know, never just a detailed retelling of an event: an incident gets 1-2 scenes as evidence, the
  solution gets most of the time. Before writing scenes, state in one line: the problem, the solution, and
  the surprise.
- People: anonymous, ordinary passengers, crew, engineers, with real emotion. Never a real victim's face,
  never invented dialogue or quotes, no gore. Show the accident itself (viewers expect to see it), but only
  from far away, as a witness would (a jet breaking apart high in the sky), or through what it leaves (an
  empty gate, a suitcase). Never people dying, never inside the cabin at the moment of the accident.
- Voice: one narrator for the whole channel (`CM_VOICE`, default `en-US-AndrewNeural`, rate `+0%`): a curious
  storyteller, warm, restrained, a pause before reveals. Change it only for the whole channel, never per video.
- Language: episode `"lang"` (default `en`; `vi` = `vi-VN-NamMinhNeural` at `+15%`) sets the narrator, rate, outro, title
  formulas (vi: *Vì sao...?* / *Làm sao...?*), Whisper language and word limits (vi counts syllables, ~3.1/s at +15%
  measured, so a Short is 84-145). A translated version reuses the original's pictures and clips: new episode
  `<id>-vi` with `from_video`, copy `img/` and `anim/` into its work folder, then `voice`, `build`, `thumb`, `qa`.
  Vietnamese runs longer than English: trim lines until `qa` shows <= 60 s and no scene over its clip by 25 %.
  edge-tts sometimes fails a whole burst ("No audio was received"); run `voice` again.
  To publish both languages as one video: after `voice` for both, `cm.py dual <id> <id>-vi` builds both on one
  timeline (each scene lasts the longer of its two narrations) and writes `<id>-dual.mp4` (audio 0 = eng default,
  audio 1 = vie, English and Vietnamese subtitles) and `<id>-vi.m4a` (the Vietnamese audio, same length as the video)
  in the `<id>` work folder. Facebook, TikTok and Instagram play only the first track; YouTube takes the m4a as a
  multi-language audio upload. Labels are burned in English in the dual file. It exits 1 if the lengths differ by > 0.1 s.
- Title formulas: *Why does X...?* / *The hidden engineering inside X* / *How X actually works*. Thumbnail:
  one subject, 2-4 words that are not the title.

## Pipeline (one episode = `episodes/<id>/episode.json`)
Order matters: research, then script, then pictures. Never generate images before the script is locked.

1. **Topic.** Pick from `playbook/research/topic-backlog.md`; score it with
   `playbook/templates/topic-scorecard.md`. Approve at >= 20/25; Evidence < 3 = reject, however good the rest.
2. **Research.** Fill `claims` in the episode: every fact the narration states is one claim with 2
   independent sources (title, publisher, URL) and `verified: true` only after you opened both and they agree.
   Prefer primary sources (accident reports, manufacturer docs, museums, textbooks). An AI answer is never a
   source. List myths: they often make the best twist. Cannot verify? Cut it, or say the doubt on screen.
3. **Script = scenes.** `python scripts/cm.py new <id> "<Title>" [--short]` copies `episode.template.json`.
   Each scene: `say` (narration for one picture, 4-8 s, written for the ear), `section`
   (hook / mystery / background / mechanism / discovery / payoff), `image` (`subject`, `show`, `variant`:
   main | cutaway | closeup | map | diagram) or the id of an earlier scene to reuse its picture, `move`
   (push_in | pull_out | pan_left | pan_right | pan_up | pan_down | still), `labels` (uppercase editorial
   labels drawn on the frame), `claims` (ids the line relies on).
   - Long-form: 1150-1750 words (8-12 min at ~145 wpm). Hook <= 20 s, no channel intro. Structure from the
     playbook: hook, mystery, background, mechanism (analogies), unexpected discovery, payoff.
   - Short: 75-130 words, 30-55 s, spoken hook <= 3 s that names the problem ("Avalanches can cut the
     internet."), the problem shown (1-2 scenes), the question "so how do engineers deal with it?" (1), the
     solution step by step (3-4), the twist (1), the payoff on today's object. A complete mini-story, never a
     trailer for the long video.
   - Reuse one illustration as wide shot, close-up and labelled detail (`"image": "S03"`, new move / labels).
     Long-form budget: 12-18 main + 8-12 close-ups + 4-6 cutaways + 2-4 maps.
4. **Gate.** `cm.py check <id>` must print `RESULT ok` (length, hook, every claim with 2 sources and
   verified, no filler phrases like "since the dawn of", no text asked of the image model, valid
   moves / reuse, title formula, 2-4 thumbnail words). `--draft` lets unverified claims through for a test
   render only; never publish a draft.
5. **Pictures.** museai must run on the real browser driver (`python -m museai` with accounts; the mock
   driver returns 64 px squares that QA rejects). `cm.py images <id>` renders each scene's illustration with
   the master prompt from `playbook/brand/style-guide.md` at the episode's frame (16:9 or 9:16) into
   `videos/curious-mechanism/<id>/img/`; existing files are skipped, `--only S04` redoes one. Look at every
   image at 100 %: reject photoreal frames, garbled letters, wrong mechanics (check against a real
   reference photo). AI illustrations are not automatically accurate technical diagrams.
6. **Voice.** `cm.py voice <id>` -> one wav per scene + `timeline.json` (0.3 s breath inside a section,
   0.7 s between sections, 1.2 s hold at the end; every episode ends with the `CTA` subscribe outro from cm.py). Listen to it before building; fix a word by rewriting the
   line (spell a name the way it sounds), then re-run (unchanged lines are cached).
7. **Animate.** Every scene is a muse video clip, not a still (user rule 2026-11-13: "I want animation").
   Each scene needs `motion`: what moves and how, in concrete terms (the crack grows in short jumps, the
   water rises, clouds drift); `move` becomes the camera line. `cm.py anim <id>` writes one
   `muse-video` job per scene into `anim/jobs.txt` (`STYLE=animation`, the scene's illustration as the
   first frame, `DURATION` = scene length + 0.5 s, min 5 s); run it in ONE background call with
   `../muse-video/scripts/render-queue anim/jobs.txt` (one clip at a time, ~10-15 min each).
   `--only S05` re-renders one clip (RETAKE). Look at every clip: same cartoon style and faces as the
   still, the motion happens, no warp, no text, no cut.
8. **Build.** `cm.py build <id>` -> `<id>.mp4` (1920x1080 or 1080x1920, 24 fps like the muse clips): each scene's muse clip,
   muted and cut to the scene length (a clip up to 25 % short is slowed to fit, a shorter one holds its last frame; a clip drawn on twos, each picture shown twice, is interpolated to 24 fps); a scene without a clip falls
   back to a slow 8 % push / pull / pan on its still. Labels fade in after 0.6 s, narration -14 LUFS,
   optional licensed music (`music.file`, ducked under the voice), plus `<id>.srt` captions.
9. **Thumbnail.** `cm.py thumb <id> [--scene S03]` -> `<id>_thumb.jpg` (1280x720). muse draws the whole thumbnail
   (user rule 2026-11-23: every picture comes from muse): paper left with the 2-4 `thumbnail.text` words in ink
   blue + muted red, the scene's illustration attached as the reference on the right, brass CM mark. OCR
   (rapidocr) must read the words exactly; a miss is redrawn, up to `THUMB_TRIES` (3), then it stops and keeps
   the last render as `<id>_thumb_muse.png`. Still look at it: OCR does not see a wrong drawing.
10. **QA.** `cm.py qa <id>` checks frame, duration, audio, loudness, image size, time per picture and the
   thumbnail, then runs muse-video's quality gate `../muse-video/scripts/qa.py --travel` on the video
   (sound, noise, smooth: no freezes, repeated frames <= 5 %, no jumps, cuts only at the scene changes via
   `PLANNED_CUTS`; motion is only a WARN, it is tuned to real footage) and Whisper (`transcribe.py`,
   `WLANG=en`): >= 90 % of the narration heard as written. A jump inside a clip = re-render that clip
   (`anim --only`). Look at
   `<id>_qa.jpg`. Then it prints the playbook's manual checklist. Go through each manual line. Never publish with an
   unresolved factual error, a misleading thumbnail or a copyright doubt because of a deadline.
11. **Publish.** Description from `playbook/publishing/descriptions.md`: chapters, every source, "original
    illustrations created with AI-assisted tools", music licence, max 3 hashtags (`#howitworks
    #engineering #designhistory`). Turn on YouTube's *altered or synthetic content* label when the policy asks.
    Log music / SFX in `playbook/templates/asset-license-log.md` and results in
    `playbook/publishing/analytics/metrics-log.md`. Schedule: 1 long-form + 2-3 Shorts a week.

## Episodes
- `s005-lighthouse-lens` - Short "How does a lighthouse throw light so far?": lamps losing most of their light,
  Fresnel's stepped lens of prism rings gathering it into one beam, the same rings in car tail lights.
- `s004-rail-gaps` - Short "Why don't train tracks have gaps anymore?": sun kinks, old jointed rail,
  continuous welded rail stretched to a summer stress-free temperature and locked down, white paint.
- `s004-rail-gaps-vi` - the Vietnamese version of s004 (same pictures and clips), the first `lang: vi` episode.
- `s003-cable-avalanche` - Short "How do we protect internet cables from underwater avalanches?": the model
  for the story shape (1929 Grand Banks breaks as 1 scene of evidence, then routing, many paths, repair
  ships with a grapnel, cables that sense earthquakes). The rejected v1 (an incident retold in detail) is
  kept in `videos/curious-mechanism/s003-cable-avalanche/_v1/`.
- `s002-comet-corners` - Short "Why do airplane windows have round corners?": the 1954 Comet breakups,
  the water-tank test, the crack at the roof ADF window (not a passenger window), stress at corners.
- `s001-window-hole` - first test Short (hole in the window), engraving look; rejected by the user
  (look hard to see, no incident hook). Kept as a reference, not for publishing.
- Long-form 001 airplane windows: research leads in `playbook/production/001-airplane-windows/`
  (none verified yet; the Comet crack origin nuance is the trap most videos get wrong).

## Rules
- Do not mass-produce near-identical videos: each one needs real editorial input (YouTube's
  repetitive-content rule is the main monetisation risk for AI channels).
- Never invent quotes, dialogue or historical scenes. Stylised illustration only, never fake evidence.
- Change rules in this file, `scripts/cm.py` or `playbook/`, not in one episode's prompts.
