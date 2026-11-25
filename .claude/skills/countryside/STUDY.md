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

## Pacing and camera (NOT yet measured)

The cut count was not taken: the session's browser closed before the frame-difference pass ran, and downloading
the video for `ffmpeg scdet` needs the user's OK. The lines below are the genre's working assumptions, used as the
skill's targets; replace them with measured numbers (`ffmpeg -vf "select='gt(scene,0.3)',showinfo"` on a 2-min
excerpt) when the video may be fetched:
- Long, calm shots, roughly 5-10 s each, cut on the song's phrases (about one cut per sung line or two), simple
  hard cuts or short dissolves, no zooms, no speed ramps, no flashy transitions.
- Camera is mostly locked or a slow, near-still handheld; the motion is inside the frame: curtains, steam, leaves,
  her hands, water, a cat walking through.
- Shot sizes alternate wide (house, garden, field) - medium (her from behind or the side, at work) - close (hands,
  cup, flowers, book page).
- Subjects: tending flowers, watering, reading by the window, tea and coffee, baking, cycling a lane, sitting on a
  porch, a picnic, by a stream or the sea, a dog or cat, evening lamps. Seasons rotate (hydrangeas, summer, spring,
  "after dark").
- She is seen from behind, the side or at a distance; faces stay soft or turned away.

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
- Real imperfections: soft focus edges, a little grain, wind moving hair and fabric.

## What our skill takes from it (and what not)

Takes: the 18-20 min 16:9 playlist length, 6 songs of ~3 min as chapters, the place-and-feeling mood title, songs
as chapter timestamps in the description, a calm one-girl country day in 6 scenes, long locked shots with motion
inside the frame, cut to the music phrase, a scenery-only thumbnail.
Never: the series bracket or suffix wording, the welcome paragraph, the song titles or lyrics, the Japanese
title/tags, their girl or house. Our girl is ELLIE (braid over her LEFT shoulder) in our own world.
