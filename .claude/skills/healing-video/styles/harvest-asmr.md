# Style: harvest-asmr (user reference 2, 2026-11-12)

A hands-only garden harvest montage: one crop per shot, picked in close-up, with the real crisp sound of the picking. Different from the other styles: no kitchen, no text, no story; the garden is the star and the sound is the hook.

## Measured on the reference (FDown mp4, 360x640, 25.6 s)
| | |
|---|---|
| cuts | ~28 hard cuts (1.3, 2.1, 2.9, 3.7, 4.7, 5.3, 5.9, 6.6 ... 24.3 s) = ~29 shots, **~0.9 s each**, a few 1.5-2 s holds (wide opener 0-1.3 s, tomatoes at 10.6-12.9 s) |
| order | wide opener (woman in an orange top holds up a melon-like fruit, wicker basket of veg + 2 cats on the lawn) → one crop per shot → closing top-down basket with the cats beside it (hold) |
| subject | a northern-European vegetable and flower garden in late summer: melon, eggplant, plums, purple beans, peppers, chilis, tomatoes, greenhouse. Calendula, cosmos and nasturtium in frame as colour |
| shot formula | close POV, hand and forearm only (orange, plaid or bare sleeve), the crop ON its plant, pruners or fingers mid-action, picked crop shown in the palm or dropped in a basket; often two hands. Never a face to camera |
| framing | handheld phone, almost still, 1 crop fills ~40 % of the frame, leaves and flowers fill the rest |
| text | none |
| picture | bright overcast-to-sunny daylight, saturated true greens, no grade beyond phone default |
| sound | NO music in the reference: real picking sound (snips, snaps, leaf rustle, plucks) with birdsong. -28.6 LUFS, LRA 12.9 LU (sharp transients), spectral centroid median 2.7 kHz (crisp, bright). Spectrogram: broadband vertical clicks at every cut/pick |
| pacing | constant, no build; each shot is one complete pick |

## How it differs
- postcard / ode: rooms and one line of text, 1.2-1.6 s; here no text, garden only, ~1 s, hands in plants.
- story: narrated 16:9 cooking; here silent montage.
- garden-montage (rotation sibling, 10 x 1 s with a caption): this one has no caption, a harvest-only hand-POV formula, a wide opener + basket-with-animal close, and **real picking sound is the content** (foley kept loud, piano very soft under it).

## Shot formula (what the bank generates, `scripts/harvest_ideas.py`)
1. **Wide opener** (1.3-1.5 s): she, back to camera, holds up a few fresh crops; basket on the grass, a cat or dog beside it.
2. **10 crop shots** (1.0 s each): "Close-up, handheld phone POV, her hand in a cream knit sleeve <snips|plucks|pulls up|twists off|picks> <crop on its plant>"; name the SOUND of the verb in the brief so muse renders it in sync.
3. **Close** (2 s): top-down basket full of the crops, her hand adds one, the animal watches.
Mix verbs (snip, pluck, pull, twist, pick); mix colours (never two same-coloured crops in a row); one crop per shot, never a row of identical things.

## Idea bank
`python3 scripts/harvest_ideas.py next [--season summer] [--garden Korean]` prints a fresh idea (12 gardens x 3 crop sequences = 36 ideas, ids `ha-NNNN`). History is the shared `~/.config/museai/healing-history.json`: record with `--caption style:harvest-asmr` so the rotation sees the style. Widen the bank by adding gardens/crops at the END of `GARDENS` in the script. Each garden is a real region with crops that grow there in that season; never put a crop in a garden where it does not grow.

## Rotation
Before picking, look at the last 3 history entries: never two videos of the same style in a row, and never the same garden/crops (`harvest_ideas.py next` enforces garden-in-last-10 and crop-sequence-used). Caption `style:<name>` on every recorded video of every style.

## Render + compose
```bash
python3 scripts/harvest_ideas.py next --garden Korean > ~/Movies/museai/healing-<slug>/idea.json   # then jobs.txt: one `scripts/shot` line per shot, DURATION=6, 1 queue
python3 scripts/compose.py --idea idea.json --music p1.m4a --out healing-<slug>.mp4 --no-text --shot 1.1 --bed clips --foley 1.3 --music-in 0 s1.mp4@1.5 s2.mp4@1.5 ...   # 14 s from 12 shots
```
- Shot 1 and last shot 1.5-2 s: use `--shot 1.1` and give the opener/closer a second clip window if wanted; the rest 1.0-1.1 s (reference 0.9).
- Pick each window where the pick happens (the snip, the pop): the sound IS the shot. `--bed clips` = the clips' own garden ambience; `--foley 1.3` keeps picks audible over the piano; `--music-in 0` (no music delay: sound from frame 0).
- Music: soft ACE piano as SKILL.md step 4 (calm.py gate), quieter than other styles under the real sound.
- Look rules: SKILL.md Real look (bait words, bright, few objects) + `prompt/healing.txt`. Crop colours stay true; hands stay beautiful (healing.txt).
