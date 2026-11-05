# The reference reels, measured

The user's target (2026-11-05): every video looks exactly like the memoriescore.studio reels
(facebook.com/memoriescore.studio, "made with higgsfield.ai"): 1990s rom-com AI short movies,
40K-1.1M views each. The first section is their measurement; the three IG reels of 2026-11-03 follow
(brighter, slower; kept as the `airy` grade and for the subtitle/sound facts).

## memoriescore.studio (ten reels, measured in the browser 2026-11-05)
Measured in-page at 90x160, one sample per 0.5 s: mean RGB, share of pixels under 40 (deep shadow) and
over 200 (bright), saturation (max-min over max), cuts (frame difference > 30), motion (mean frame
difference between cuts).

| reel | scene | s | shots | avg shot | mean RGB | <40 | >200 | sat | motion |
|---|---|---|---|---|---|---|---|---|---|
| 1648971626738602 | night subway stairs, bride helps old lady with spilt oranges | 26.4 | 22 | 1.2 | 87/68/59 | .29 | .01 | .37 | 15 |
| 3278040659052657 | golden-hour Beverly Hills street, retriever buys lemonade with her handbag | 20.0 | 14 | 1.4 | 108/85/72 | .00 | - | .39 | 12 |
| 1616088190258208 | night penthouse, he vacuums in pyjama pants | 15.0 | 4 | 3.8 | 89/68/61 | .26 | - | .45 | 7 |
| 29119567117672640 | lamp-lit kitchen, he kneels on the counter, compact mirror | 18.5 | 11 | 1.7 | 92/60/47 | .28 | .01 | .50 | 9 |
| 1293692339564799 | autumn street market, girl sits on a turkey, mum pleads | 29.3 | 13 | 2.3 | 100/74/61 | .28 | .04 | .46 | 8 |
| 1004276802695012 | dusk Halloween garden party, Team Rocket vs Pikachu | 12.8 | 18 | 0.7 | 106/76/72 | .22 | .03 | .42 | 14 |
| 1118250454342150 | same party, long cut | 27.7 | 22 | 1.3 | 96/69/62 | .33 | .01 | .48 | 16 |
| 1813574730374342 | night restaurant, pink satin dress, tuxedo, she walks out | 30.1 | 21 | 1.4 | 88/61/62 | .36 | .01 | .40 | 14 |
| 2120806805495466 | midday lake pool, he lowers his sunglasses, they fall in | 26.9 | 20 | 1.3 | 97/80/74 | .17 | .02 | .38 | 15 |
| 2712102769240675 | seaside jewellery shop, wedding rings, mirror | 26.0 | 15 | 1.7 | 108/86/76 | .18 | .05 | .42 | 16 |
| **mean** | | 23 | 16 | **1.7** | **97/73/65** | **.24** | .02 | **.43** | 13 |

### Picture
- Warm 1990s Kodak film: red leads green by ~24 and green leads blue by ~8 in every reel, day or
  night. Day scenes are golden-hour sunny (108/85/72, no deep shadow at all) or hard midday sun with
  deep blue water (97/80/74); night scenes are amber lamps, candles and string lights against cool blue
  windows (87-92/60-69/47-62, a third of the frame in deep shadow).
- Real blacks: a quarter of the pixels under 40. Highlights roll off: at most 5 % over 200. Saturation
  0.37-0.50, mean 0.43 (the IG reels: 0.34; a raw muse clip: 0.26-0.33). Rich clean colour, not muted:
  orange fruit, pink satin, a red convertible, deep blue sky; skin golden and glowing, not matte.
- Halation glow around lamps and windows, visible grain, a slightly soft picture; nothing razor-sharp.
- Faces: 1990s supermodel glamour, 19-23: big blown-out hair, strong brows, glossy lips; period
  wardrobe (white power suit, black slip dress, pink satin, tuxedo, camel coat and turtleneck). Men
  tanned, thick-haired, boyish. Extras carry the gags: a kid at a lemonade stand, an old lady, a
  golden retriever, a bride, old bakers.
- finish.py `film` grade (default) reaches it from a muse clip: ME-0002 day medium 115/94/80 sat 0.46,
  night wide 88/69/64 sat 0.49 (`GRADE=airy` keeps the IG look below).

### Cutting and motion
- 13-22 shots in 20-30 s, average 1.7 s, many under 1 s; the one slow reel (4 shots in 15 s) is the
  exception. A line shot runs 2-3.5 s, a physical take 3-5 s.
- Coverage per scene: wide establishing with both people → big close-up singles (eyes just beside the
  lens) → inserts of hands and objects (oranges on the steps, a handbag in a dog's mouth, sunglasses
  floating, two rings in a box, a cocktail, a compact mirror) → a two-shot for the physical beat → a
  reaction close-up button, sometimes straight into the lens (a finger to the lips, a wink).
- Motion inside the frame is constant (mean frame difference 7-16): people walk, run down stairs,
  kneel, drop things, sip, turn; the camera drifts or pushes in slowly, never a fast move or a zoom.
- The first frame is already the gag mid-action; no title, no establishing pause. The last frame is a
  face.
- Subtitles: tiny white sans text at ~74 % of the height, only on spoken lines (finish.py: 26 px at
  720 wide). Caption on the post: one question ("When was the last time you were late because you
  chose kindness?"). A soft retro pop song under the dialogue (She & Him) on some reels.

## The three IG reels (2026-11-03; `GRADE=airy`)

They are short rom-com movies, not lessons. Match this sheet when the user asks for the airy look.
## Format
| | bakery (DeujtBpPtJW) | Aspen ski (Dezs4w1Jh7q) | Christmas pyjamas (Dehcem_o0ep) |
|---|---|---|---|
| length | 15.2 s | 30.2 s | 29.3 s |
| size, fps | 720x1280, 24 | 720x1280, 24 | 720x1280, 30 |
| shots | 6 | 11 | 6 |
| shot lengths (s) | 2.0 2.3 3.9 1.4 2.3 3.1 | 2.0 2.0 2.7 0.7 2.4 5.7 0.7 4.7 7.1 1.2 | 1.7 3.8 0.5 9.3 6.1 7.4 |
| lines | 3 | 6 | 7 |
| twist | the "handsome" baker gets $1, old bakers laugh | the crash victim is the ski teacher, she leaves him a date | she storms out with a suitcase over a fart |

Rhythm: quick 1-2.5 s reaction cuts mixed with 4-9 s physical-comedy takes. The first frame is
already mid-action (a scream, a counter exchange, a pillow fight); no establishing title.

## Shots
- Each line is a single: the speaker alone in a medium (waist up) or close-up, looking at the other person
  who stands just outside the frame beside the camera (bakery: her medium, his close-up, her medium, her
  medium; never both faces in one line shot). The camera is locked on a tripod.
- Both people share the frame only in a wide or a relaxed two-shot (lying in the snow, side by side at a
  door), never a cramped over-the-shoulder angle: an ots cut (ME-0002 drama version) read as unnatural.
- Expressions are open and lively: a wide grin with teeth, a scream, a raised brow, a real laugh.
- Extras fill the world: bakers in white caps, skiers, a lift, a Christmas tree, a stone lodge.
- Physical comedy carries the story: a tumble down the slope, packing a suitcase in a huff, a pillow
  fight. Words are few and short (1-8 words a line). Payoffs are visual: a $1 bill on the counter.

## Picture
- Bright, soft, airy late-1990s rom-com: soft diffused front light, low contrast, natural clean colour
  gently muted (clean cream whites, blush pink, camel, soft red), matte natural skin, a slightly soft
  picture (720p, no crisp micro-detail). NOT amber or orange: whites stay white, shadows stay neutral.
- Measured (180x320 samples, 2 fps): bakery mean 130/108/96, shadows 23/22/16, mids 152/126/111,
  highlights 233/217/216, saturation 0.34 (max-min over max); ski 100/84/81, sat 0.34; pyjamas 88/72/65,
  sat 0.41. A muse clip straight out of the box is already close (121/101/90, 0.36); the warm grade of
  PR #218 pushed it to 114/94/78 at 0.42 and read as orange, so finish.py now only lifts and hazes
  (result 129/110/100, 0.31).
- Faces: very young (19-21) and model-beautiful: the bakery girl (the user's minimum bar) has warm
  light-olive skin, dark eyes with soft liner, matte brick-red lips and a big smooth swept-back
  shoulder-length blowout. Men boyish and handsome, natural grins.
- Focus: 85 mm wide open. Only faces sharp, the background melted (edge mean 2.6-5.3, background
  corner 3.0-3.7 at 720x1280). Our stills land at ~8 / ~4; finish.py's 540 p pass closes the gap.
- Sending a reference frame as `"first"` works: muse animates it and keeps the face. It refused the
  same face in a new setting, so a reference frame only fits shots in that frame's own scene.
- What made earlier versions read as AI: sculpted contour and heavy brows (look 30), lined matte lips,
  contrasty saturated golden grade, razor-sharp 1080p detail, every face posed the same way, and the
  drama ots coverage with faces turned away from the camera.

## Text on screen
- Subtitles only, English, no box: white bold rounded sans (bakery, pyjamas) or serif (ski), thin dark
  outline, ~30 px font at 720 wide, centred, one line, centre at 73-78 % of the height.
- A small semi-transparent handle watermark (italic serif, bottom right or lower centre).
- No hook banner, no translation line, no highlight, no lesson card.

## Sound
Dialogue at about -18 dB mean with room ambience (gaps -22..-24 dB); at most a faint music bed. Muse's
own clip audio is right; add no music unless the user asks.
