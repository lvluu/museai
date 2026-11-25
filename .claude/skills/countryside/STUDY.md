# Study: the "slow countryside playlist" format (2026-11-25)

Source: one Japanese-run channel of this genre, read on 2026-11-25 (channel page in a browser, `yt-dlp
--flat-playlist` over all 112 uploads, full `--dump-json` metadata for 6 videos: the 2 newest, the 4 most viewed,
auto-captions for 1). We learn the format; we never copy its titles, series name, songs, footage or people.

## Format (measured)

| what | number |
|---|---|
| uploads | 112 long videos, 0 Shorts |
| length | median 1145 s (19:05); range 1043-1310 s; 2 outliers (122 s, 522 s) |
| frame | 1920x1080, 30 fps, 16:9 |
| cadence | one upload every 2 days (page: 1d, 3d, 5d, 7d, 9d, 11d ago) |
| views | median 3.3k per video; best 207k, 153k, 115k, 93k, 92k |
| songs per video | 6 (5 of 6 videos with chapters), 7 once |
| song length | 122-261 s, mean ~195 s (3:15) |

Song lengths of the four measured playlists (s): 261 157 220 188 228 154 / 214 152 232 205 197 169 /
222 195 192 217 200 199 / 134 151 180 122 260 170 183.

## What it is

A **music playlist** dressed as a slow day in the countryside: ~19 minutes of soft original English songs with
vocals (gentle female/male pop-folk ballads: "the night is soft, the world is still", "no need to speak, no need
to run") over calm footage of one young woman living alone in a country house with a garden. The viewer puts it
on while working, studying or winding down after work; the description says so ("if you're coming here after a
long, exhausting day, there's no need to do anything"). Tags target study/work BGM, chill, vlog and 一人暮らし
(living alone) searches at the same time.

- **Title**: a fixed series bracket + one lowercase 3-6 word mood phrase + a fixed search suffix, e.g. the pattern
  `<series> <mood phrase>. (Relaxing Playlist Music for Stress Relief)`. Mood phrases are places and feelings,
  never events: "a place to linger longer", "where mornings move slowly", "home among the hydrangeas".
- **Description**: the song list as chapter timestamps (`00:00 - Song`), then the same welcome paragraph every
  time with small emoji, then 6 hashtags (#slowliving #quietlife ...).
- **Chapters = songs.** Each song is a little scene of the day; one video's chapters were named as places
  instead ("a day at the park", "peace by the sea", "camping by the stream"), so a song can carry a setting.
- **Thumbnail**: not inspected image by image in this pass (only the page text was read); the skill uses our
  own rule: one scenery frame of the film, no person.
- **Hook**: there is no spoken hook; the first 10 s are the best-looking wide of the day (garden in sun, a
  window with curtains moving) with the first song already playing. The title and thumbnail do the hooking.

## Pacing and camera (measured 2026-11-25)

Measured on the most viewed video (1169 s, 6 songs), downloaded at 480p, `ffmpeg select='gt(scene,0.25)'`, hits
closer than 0.6 s merged, then checked by eye on frame sheets:
- **310 shots, 309 cuts: mean 3.8 s, median 3.0 s** (p10 1.7 s, p25 2.3 s, p75 4.5 s, p90 6.2 s; max 40.9 s).
- Shot lengths: 0-2 s 53 | 2-4 s 161 | 4-6 s 60 | 6-8 s 22 | 8-10 s 6 | 10-15 s 5 | 15-30 s 2 | 30 s+ 1.
- Per song the average shot is 4.6 / 3.4 / 4.4 / 4.6 / 4.0 / 2.2 s (44-75 cuts a song): faster near the end.
- First 10 s: cuts at 3.8, 6.4, 8.7 s, so 3 different shots before the 10 s mark.
- The detector misses some soft cuts (a cat shot then a covered basket counted as one 6 s shot), so the real
  median is at or under 3.0 s. Transitions are a mix: 78 of 309 cuts score >= 0.6 (hard cuts), 98 score under 0.4
  (soft cuts and short dissolves), plus the odd fade through dark.
- So the film is not slow because shots are long: it is a quick, steady 3 s rhythm of calm images, every shot
  showing a different subject or scale. The calm comes from the motion inside each shot and the music.
- Order seen in one 90 s stretch (24 shots): ladle over a pan (close) - plate with a spoon (close) - woman at a
  low table through a window frame (wide) - eating, profile (medium) - porch table (wide) - misty forest (wide) -
  stream (wide) - wooden house with tea terraces (wide) - hands picking tea leaves (close) - picking, profile
  (medium) - stream (wide) - picker far off (wide) - flowering branch (close) - sitting on a ridge (wide) - looking
  up with a basket (medium) - leaves in a basket (top-down close) - house roof in rain (wide) - fridge door (close)
  - kitchen window (medium) - drinking (close) - kitchen (wide) - glass jar (close) - misty hills (wide) - standing
  in a doorway (wide). About 45% wide, 20% medium, 35% close.
- Camera (start vs end frames of 6 shots of 4-6 s): locked or near-still handheld, framing the same at both ends; the motion is inside the frame: curtains, steam, leaves,
  her hands, water, a cat walking through.
- Shot sizes alternate wide (house, garden, field) - medium (her from behind or the side, at work) - close (hands,
  cup, flowers, book page).
- Subjects: tending flowers, watering, reading by the window, tea and coffee, baking, cycling a lane, sitting on a
  porch, a picnic, by a stream or the sea, a dog or cat, evening lamps. Seasons rotate (hydrangeas, summer, spring,
  "after dark").
- She is seen from behind, the side or at a distance; in close and medium shots her face shows in profile or
  three-quarter while she eats or looks up, never into the lens.
- Look: muted greens, low saturation, soft contrast, filmic. The footage seems gathered from several sources
  (different women and houses inside one song; blurred burned-in subtitles in some shots), so one coherent world
  is something we do better than the channel, not something it does.

## Sound

(From the auto-captions of the most viewed video: lyrics run with no gap from 0:00, marked [music] /
[singing].) Music first: the songs ARE the content. No narration, no subtitles, no text on screen beyond the title. Ambient
sound is not featured; the footage's own sound, if any, sits far under the songs.

## Why it reads as real footage

- One coherent world: the same house, garden and girl across a whole video, the same outfit within a scene.
- Ordinary unposed actions done slowly from start to finish (pouring, turning a page, carrying a basket)
  rather than glamour poses.
- Natural light that changes with the time of day through the film (morning - noon - dusk - lamps at night).
- Steady locked framing; motion comes from the world, not from a floating camera.
- Many short different shots: no single frame stays long enough to be inspected for AI faults.
- Real imperfections: soft focus edges, a little grain, wind moving hair and fabric.

## What our skill takes from it (and what not)

Takes: the 18-20 min 16:9 playlist length, 6 songs of ~3 min as chapters, the place-and-feeling mood title, songs
as chapter timestamps in the description, a calm one-girl country day in 6 scenes, a ~3 s shot rhythm (each clip cut into 3 shots:
wide, then two closer crops) with locked shots and the motion inside the frame, wide / medium / close mixed,
muted soft grade, a scenery-only thumbnail (unchanged: the best healing frame, no person).
Never: the series bracket or suffix wording, the welcome paragraph, the song titles or lyrics, the Japanese
title/tags, their girl or house. Our girl is ELLIE (braid over her LEFT shoulder) in our own world.
