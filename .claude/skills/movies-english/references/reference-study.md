# The reference reels, measured

The user's target (2026-11-05): every video looks exactly like the memoriescore.studio reels
(facebook.com/memoriescore.studio, "made with higgsfield.ai"): 1990s rom-com AI short movies,
40K-1.1M views each. The first section is their measurement; the three IG reels of 2026-11-03 follow
(brighter, slower; kept as the `airy` grade and for the subtitle/sound facts).


### Frame-level measurements (reels 2 and 9, ten frames each, 135x240 samples)
Luminance percentiles and the mean colour of skin pixels (r>g>b, r-b>15):

| | p5 | p25 | p50 | p75 | p95 | skin RGB |
|---|---|---|---|---|---|---|
| memoriescore night restaurant (reel 9) | 5 | 14-42 | 27-92 | 85-142 | 117-204 | 124-152 / 86-118 / 73-108 |
| memoriescore day boutique (reel 2) | 1-25 | 48-74 | 75-109 | 107-150 | 149-235 | 134-154 / 95-113 / 75-98 |
| ME-0002 film grade v1 | 2-12 | 27-49 | 64-108 | 106-163 | 176-210 | 142-169 / 101-127 / 82-105 |
| ME-0002 film grade v2 (S1, S2, S5) | 2-4 | 29-39 | 67-87 | 113-129 | 166-176 | 137-147 / 103-111 / 77-81 |

So the reels keep p75 near 110 and p95 near 165 even in daylight; our v1 grade sat 30-40 points higher in the
upper mids, which is what reads as flat and bright. Skin is a deep golden tan (R-B ≈ 55), not pale pink.

What the close-ups show (zoomed frames): one warm directional key light, the far cheek in shadow, a glow on
the hair edge; the background darker than the face (dark wood, black, night) and simple; an out-of-focus
foreground piece (a shoulder, a glass) at one side; big voluminous hair; high-shine glossy pink-red lips;
defined eyes; gold jewellery; bold solid-colour wardrobe (white, red, black satin). Our bakery frames had the
opposite: a bright busy pastel background, flat window light, pale skin, matte dark lips.

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

## Round 2 (2026-11-05): one more memoriescore reel and six Christmas reels
- memoriescore "STILL WORKS" (lake dock in heavy rain, 28.6 s): one location, one outfit each (white
  strapless mini, soaked; white open shirt, black trousers, both barefoot), a macro insert (a hand
  catching rain) opens the reel, an empty wide of the dock is the breath before the kiss.
- Christmas reels (memoriescore "TEN BANANAS, OZZY", "HI, AGAIN", "THAT WAS HIM"; "THE WRONG HOUSE";
  two palette references): same curve as the night restaurant reels, darker in the shadows:
  p5 6-13, p25 17-42, p50 70-98, p75 109-129, p95 149-165, skin 123-149 / 90-111 / 66-97; a decoration
  slideshow in a dark room reaches p25 15, p50 25-45, p95 244 (only the lights clip). A white blazer
  frame reaches p75 178. Look: snow falling, one warm practical source (tree, string lights, carousel
  bulbs), blue-black behind the faces, red / cream / gold / burgundy / forest green wardrobe, shearling
  collars and cuffs, tartan, fur over sequins, leather gloves, a red paper cup of cocoa.
- Animals: a golden retriever (adult on a lead; a puppy carried), a tiny white Pomeranian as the
  comedy device; each with a close-up insert and a beat in a person's arms.
- Everything catalogued in `style-catalogue.md`; the four Christmas scripts are `library/batch_xmas.json`.

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

## Round 3 (2026-11-05): the "AI look", measured

Side by side with a memoriescore close-up (THAT WAS HIM, the blonde in the fur coat; same 135x240 measure,
skin = warm-pixel mask), the LIGHT v1/v2 stills differed in light and skin colour, not in exposure:

| | reference | ours (v1/v2) |
|---|---|---|
| skin p10 / p90 | 88 / 135 (range 47: soft frontal light, no shadow side, no hot spot) | 76 / 180 (range 103: one hard side light, a hot cheek, a dark cheek) |
| skin saturation | 0.36 | 0.44-0.57 |
| skin RGB, G/B | 155/110/100, 1.09 (fair peach, pink blush: blue almost as strong as green) | 170/116/75, 1.5 (orange-gold: "golden-tan" in the prompt) |
| room behind the face p50 | 16, glowing bokeh | 12-26 |
| picture | slightly soft, hazy, muted film colour, beige wall 122/110/97 | razor-sharp, rich saturated |

That contrast, the orange skin and the sharpness are what read as AI.

Fixes: LIGHT v3 in build.py / look.txt asks for soft frontal low-contrast light, fair peach matte-glow
skin (never golden-tan, orange or yellow), muted film colour, a light haze; `scripts/still_check.py`
prints the bands (skin mean 100-130, p10 >= 75, p90 <= 150, range <= 70, sat 0.28-0.42, G/B 0.95-1.25,
bg p50 8-45, clipped < 1 %); `scripts/still_match.py` rolls the highlights off and shifts the skin to
peach on the chosen still (v3 stills land at p90 165-183, G/B 1.3 before it; 138-149, 1.08-1.15 after,
PASS); the film grade in finish.py dropped saturation x1.3 (it took clip skin from 0.36 to 0.54) for
x0.95, a harder roll-off (1 -> 0.80), a peach balance and a touch more blur. Two ffmpeg traps found on the
way: a screen blend in yuv420p lifts U/V (magenta cast) and gblur on packed rgb24 mixes the channels
(blue cast), so the halation split runs in planar gbrp. ME-0002 clips after the grade: skin mean 112-113,
p10 78-82, p90 139-152, sat 0.27-0.31, RGB ~132/107/95.

Round 3b: the reference frame measured again from a full-size grab (same mask): skin mean 113, p10 88,
p90 133, sat 0.34, skin RGB 136/106/91 (G/B 1.16); forehead 158/116/105, cheeks 160/112/105 and 140/91/79,
lips 140/74/68 (sat 0.52: the one saturated thing), hair 124-147/109-123/94-104, wall 122/110/99 (sat 0.19);
whole frame p50 96, p75 120; background mids RGB 112/100/94, sat 0.21. Our matched v4 stills: skin
135/106/98 (too blue), sat 0.28, frame p50 51-68, background mids 96-102/73-80/71-77, sat 0.30-0.39. So the
remaining gap was not the face but the world around it: muse paints a dark, saturated orange-brown room
behind the face (the prompt asked for "much darker than the face, deep brown, black, night"); the reference
is a mid-key, muted pastel frame (beige stone, snow, grey sky, blonde hair) where only the blush and the
lips carry colour. Fixes: LIGHT v4 / look.txt ask for pale desaturated surroundings (beige stone, cream,
grey, snow, pale sky, soft brown) with no strong colour except the blush and the glossy rose lips, overcast
or open-shade daylight instead of golden hour; still_match.py and the film grade keep the mids balance at
rm 0.06 / gm -0.02 / bm -0.01, pull red out of the shadows (rs -0.04, gs/bs +0.02) and saturate x1.1.
Stills with the v4 prompt (winter street, fur coat, snow) after still_match: skin 137/111/95 and 139/109/92
(G/B 1.17-1.18), sat 0.32-0.34, p90 149-151, background mids 114-126/99-116/88-108 at sat 0.20-0.28,
frame p50 64-94: on the reference for the first time, face and world.

Round 3c: a hand-tuned chain only approximates the reference; still_match.py now does a Reinhard colour
transfer in CIELAB instead, region by region (skin pixels onto the reference skin mean/std per channel,
L 47.6 / a 10.0 / b 13.4, std 8.3 / 5.5 / 3.7; the rest onto its background, L 19.1 / a 2.6 / b 3.3, std
22.9 / 3.0 / 4.3), blended by a blurred skin mask. The same four stills then measure skin 138/105-110/90-95
(G/B 1.16-1.17), mean 113-117, p10 86-88, p90 138-142, sat 0.31-0.35, bg p50 21-33: the reference's own
numbers (136/106/91, 113, 88, 133, 0.34). One side effect to know: the background takes the reference's
dark neutral statistics, so a strong colour there (a red scarf) comes out muted.
