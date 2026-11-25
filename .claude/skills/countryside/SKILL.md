---
name: countryside
description: Make an 18-20 minute horizontal 16:9 "slow countryside playlist" film through museai - six soft original songs (one per scene of a calm day, ~3 min each, chapter timestamps in the description) over real muse motion clips of ELLIE living alone in a country house with a garden - morning coffee, watering flowers, cycling a lane, reading under a tree, baking, the walk home at dusk, lamplight at night. Long locked shots with the motion inside the frame, cut to the music phrase, no narration and no text on screen. REAL VIDEO ONLY: every beat is a rendered clip, never a still. Picks a mood title, six scenes and a style (hydrangea cottage, meadow farmhouse, seaside cottage, autumn orchard, snow cottage, rainy garden) with a history so no film repeats. Use for "countryside video", "countryside playlist", "relaxing playlist video", "slow living playlist", "music for stress relief video", "video like Countryside Echoes", or the next one of these.
---

# countryside

Paths are relative to this folder. The format comes from `STUDY.md` (read it first). It reuses the existing
pipeline instead of copying it:
- `../healing-longform/scripts/plan.py` (refs -> stills -> clips; the stills are only the first frames of clips)
- `../healing-longform/scripts/longform.py` (compose, `cuts`, `grade`, `shake`, `xf`)
- `../field-to-table/scripts/music_chain.sh` (join tracks with crossfades)
- `../muse-video/` (server, `render-queue`, `qa.py`, delivery) and `../healing-video/scripts/music` (ACE-Step)

The girl is ELLIE (`../character-bank/`): braid over her LEFT shoulder, seen from behind, the side or at a distance,
never a face to camera. Pip the cat may walk through. Nobody else. Never copy the studied channel: no series
bracket, no "(Relaxing Playlist Music for Stress Relief)" suffix, no welcome paragraph, no songs, no Japanese tags.

## HARD RULE: real video only (user, 2026-11-25)

Every beat is a muse motion clip (`kind: clip` with a `move`). A film is never composed from still images
("image jumping"): `scripts/story.py check` refuses a still beat, and `check --work .` exits 3 while any `sN.mp4`
is missing. When muse's video quota stops the clip queue: write what is missing in the work folder, end the turn,
and re-run the same clip queue after the 24-hour reset. Never compose, never fall back to stills.

## The format (from STUDY.md)

- 18-20 min (1000-1320 s), 16:9 1920x1080, one film every 2 days at most.
- Six songs, one per scene of one calm day (morning -> late morning -> noon -> afternoon -> dusk -> night), each
  ~3 min. The description lists them as chapters (`story.py chapters`).
- Songs carry the film: soft acoustic/piano ballads with a gentle vocal (ACE-Step `TAGS` from the style's
  `music`, our own lyrics) or instrumental when ACE-Step vocals come out rough. The clips' own sound sits far under.
- No narration, no subtitles, no chapter cards (`chapter_cards: false`), no text on screen.
- Title: our own mood phrase from the idea (lowercase, a place or a feeling) + "| slow countryside days" style
  suffix of our own. Thumbnail: one scenery frame, no person.
- Shots: a ~3 s rhythm (measured median 3.0 s, mean 3.8 s). Each clip is cut into 3 shots of ~3 s (the wide take,
  a 1.3x crop, a 1.15x crop: `cuts`), ~8.6 s per clip, 21 clips per song, ~126 clips. Never hold one shot long.
  Alternate wide (house, garden, lane) - medium (ELLIE at work from behind or the side) - close (hands, cup,
  flowers, a page). Every third beat has nobody in it (`cast: []`).

## Steps

1. **Pick.** `python3 scripts/ideas.py style --season now`, then `python3 scripts/ideas.py next --season now`.
2. **Story.** `python3 scripts/story.py new <ct-id> --style <style id> --slug <slug> > story.json` in the work
   folder `~/Movies/museai/healing-<slug>/`. Fill every `TODO`: the `light` per time, our own song titles, and each
   beat's `shot` + `move` for that song's scene (one real action per shot, follow `../field-to-table/SKILL.md`
   "Rules that keep it from looking AI": locked camera, "Close-up" first for small subjects, "her hands" for
   hands-only shots, no knives, containers named with their contents). `python3 scripts/story.py check story.json`
   must print `ok` (aim 1000-1320 s).
3. **Plan + render** (detached), `H=../healing-longform/scripts`, `Q=../muse-video/scripts/render-queue`:
   `python3 $H/plan.py jobs story.json`, then `$Q -j 3 jobs-refs.txt && $Q -j 3 jobs-stills.txt && $Q -j 2 jobs-clips.txt`.
   Check the first-frame sheet before the clips (braid LEFT, outfit, nobody else). 120 clips take several quota
   days: re-run the clip queue after each reset (it skips what is on disk).
4. **Gate.** `python3 scripts/story.py check story.json --work .` must exit 0 (every clip on disk). Exit 3 = stop
   here and come back after the reset.
5. **QA** every clip with `../muse-video/scripts/qa.py` and a frame sheet sampled by time; delete and re-render a
   broken clip (face to camera, morphing hands, second person, moving camera).
6. **Music.** Six ~200 s tracks, one per song, different seeds: `TAGS="<style music>" ../healing-video/scripts/music
   "<scene>" mN.m4a 200 <seed>`, joined with `../field-to-table/scripts/music_chain.sh music.m4a m1.m4a ... m6.m4a`.
7. **Compose.** `python $H/longform.py story.json --music music.m4a --out healing-<slug>.mp4 --dry`, then without
   `--dry`. `python3 scripts/story.py chapters story.json` gives the description's chapter list.
8. **Deliver + record.** Film, 16:9 thumbnail (`../healing-video/scripts/cover.py` from a no-person clip), story
   to `~/Desktop/countryside/<slug>/`; copy the story to `stories/<slug>.json`; then
   `python3 scripts/ideas.py record <ct-id> --style <style id> --slug <slug> --video <path>`.
