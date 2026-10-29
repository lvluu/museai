# Look, cutting and sound of the reference film

Reference: a 155 s Chinese-subtitled AI short, "Highlands Ranch, Colorado 1987" (user, 2026-10-29).
Measured with ffmpeg (`signalstats`, `select=gt(scene,0.25)`, `volumedetect`) and frame sheets.
Take its craft, not its content: its characters, place and story are not reused.

## Colour (measured, 0-255 YUV)
| metric | value | reads as |
|---|---|---|
| luma mean | 95-133 (night/interior 48) | mid-key, nothing crushed, no bright HDR sky |
| U (blue-yellow) | 109-128, mean ~118 | pulled toward yellow: warm |
| V (red-cyan) | 135-154, mean ~143 | pushed toward red/orange |
| saturation mean | 15-32 (median ~23) | moderate: rich oranges, never neon |

- Highlights cream/amber, skies a soft powder blue (not deep cyan), shadows brown-olive with a
  faint teal in glass and chrome. Blacks lifted (no pure black), whites rolled off (no clipping).
- Fine film grain, gentle halation around windows and chrome, slight softness: a 1980s
  35 mm print, not a "retro filter" (no vignette bars, scratches, VHS lines or light leaks).
- Production design does most of the colour work: rust, burnt orange, camel, mustard, cream,
  harvest gold, avocado and teal objects; wood panelling; low sun through windows.
- `scripts/grade.sh` reproduces this on muse renders (warm curves, lifted blacks, soft halation,
  grain). Grade every shot the same; never grade per shot by eye.

## Cutting (measured)
- 24 cuts in 155 s: one shot every 5-7 s (range 4.5-15 s). The camera sits still or moves slowly;
  energy comes from cutting between places, not from camera tricks.
- Structure: 0-12 s two silent establishing views (suburb over the city, a commercial avenue under
  the mountains) with the place-and-year title; then the car conversation through the windshield;
  errands (police stop, office, plaza, bakery, supermarket); drive home; a quiet unpeopled tour of
  the house (living room, kitchen, study, dining table, bedroom, laundry, bath) to close.
- Dialogue shots: frontal two-shot through the windshield, over-the-counter medium shots, walking
  medium-wides. Few close-ups. Inserts are things (a pie, a list, a door).

## Text
- Opening title over the first establishing shot, centred slightly above middle: place line in a
  warm white serif (Georgia/Baskerville class, ~7 % of frame height), the year under it, the
  Chinese place name under that in a bold sans. Soft dark shadow, no box. Holds ~4 s, fades.
- Subtitles: small, white, bottom-centre at ~85-90 % height, English line above the Chinese line,
  thin dark outline/shadow, no box. One utterance per cue.
- A small channel credit sits bottom-centre; this skill does not add one unless the user asks.

## Sound
- Mono 44.1 kHz in the reference; deliver stereo 48 kHz.
- A continuous warm music bed under everything (mean -8.9 dB, no silence anywhere): soft
  mid-80s instrumental (electric piano, chorus guitar, soft synth pads, gentle drum machine).
  This skill keeps that bed but ducks it 10-12 dB under speech so dialogue stays intelligible,
  and lets location ambience (traffic, store hum, a register bell) carry the transitions.
