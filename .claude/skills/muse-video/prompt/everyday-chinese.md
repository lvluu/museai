# EVERYDAY CHINESE - episode brief format

The user writes each episode brief in this exact format (EP12, 2026-10-27). When asked for the next
episode, copy it, bump the number, pick a topic not in the log below, and change only TITLE, CAST
outfits/roles, the set line, SCRIPT and ENDING. Keep every other section word for word (the eye-line line in ACTING AND CAMERA was added after EP12, where the woman sat in profile looking past the man).

Script rules: one intro line to camera, 9-10 dialogue lines alternating MAN/WOMAN, one ending question
to camera; about 85-95 syllables in total (30-40 s at a natural pace); each line ≤ 14 syllables;
pinyin with tone sandhi written as spoken (yí ge, yìqǐ, bú kèqi); Vietnamese natural and short.
No payment, food handling or object exchange in the scene.
Fixed script vs asked length (user rule, 2026-10-29, EP35): when the brief gives EXACT DIALOGUE and a
duration it cannot fill at a natural pace (EP35: ~69 syllables for 40-45 s), keep the exact script at
natural speed and let the video run shorter. Do not ask, add lines or slow anything; say the delivered
length on the preview.
Vocabulary recap (when the brief has one): each word is said at normal speed and followed by a
one-second review pause with its card on screen (SKILL.md, Timing step 5); never three words in a row.
Vocabulary cards while they talk (user rule, 2026-10-29, after EP27; every episode): the user liked
seeing each new word on screen at the moment it is said in the dialogue. Every episode picks 3 key words
(the brief's vocabulary list, or 3 words from the script when it has none) and shows each as a card
(hanzi / tone-marked pinyin / Vietnamese) at its first spoken use in the two-shot, gold-highlighted for
0.6 s on the word, then kept up until shortly before the next card or about 5 s; again for each word
in the recap; cleared before the ending question. One card at a time, upper-left above the heads,
never over a face. Made in post with `scripts/cards.py` (never an older episode's copied overlay script: EP31's EP28 copy drew 150 px hanzi in a gold frame and the user rejected it as too big and cramped) (SKILL.md, Timing step 5), after the captions.

Delivery title (user rule, 2026-10-27): the viewers are Vietnamese, so the final file and its posting
caption use a Vietnamese title, `Tiếng Trung mỗi ngày NN - <topic in Vietnamese>` (EP16: Đi cắt tóc). The caption's first line is
`Tập NN | <short hook>` (EP18: `Tập 18 | Quán hết chỗ? Nói câu này là được ngồi chung bàn ☕`);
see SKILL.md "Caption".
The brief's own header line stays in English for muse.

Viral rules (user rule 2026-10-29, from Chinese-learning Shorts that spread):
- **Hook in the first 1-2 s is the situation, not an intro**: the intro line to camera states the
  everyday problem or the wrong habit (`Đừng nói "Nǐ hǎo" khi vào quán ăn, hãy nói câu này!`,
  "Quán hết chỗ thì nói gì?"), never a greeting, a self-introduction or the episode name. Pick topics
  viewers hit this week: ordering food, asking for Wi-Fi or a charger, haggling, asking the way, a
  seat, the toilet, paying (said, not handed over: no object exchange in the scene).
- **Captions show the tones**: three lines hanzi / pinyin / Vietnamese side by side; `burn_subs.py`
  colours each pinyin syllable by tone (1 red, 2 orange, 3 green, 4 blue, neutral white).
- **The ending loops and asks**: the ENDING question is a mini quiz on the episode's key phrase (a
  blank to fill, or "which one is right?") and its wording echoes the hook, so a replay lands back on
  the problem it answers. The posting caption's CTA asks for the answer in the comments
  ("Comment câu trả lời của bạn bên dưới xem đúng không nhé!").
- **Title and cover name the dilemma**: the `Tập NN | <hook>` line and the first frame state the urgent
  everyday problem ("Quán hết chỗ?", "Điện thoại sắp hết pin?"), not the grammar or the word list.

## Episode log
- EP11 Buying fruit (fruit market, vendor)
- EP12 Ordering takeout (takeaway restaurant, cashier)
- EP13 Finding the subway (quiet street, passer-by giving directions)
- EP14 At the pharmacy (neighbourhood pharmacy, pharmacist) - drafted
- EP16 Getting a haircut (salon reception, stylist)
- EP17 Buying bread (bakery, baker)
- EP18 Asking to share a table (cafe, woman standing, man seated at a small table)
- EP19 Exchanging a shirt (clothing store service counter, shop assistant; first two-shot still had the man in profile -> clip A OFF GAZE; only a still asking for faces "turned only about 30 degrees toward each other, like a TV presenter pair" gave him a three-quarter face)
- EP20 Changing plans on a rainy day (apartment lounge, rain at the window; man stayed in profile in all 4 clip-A takes)
- EP21 Borrowing a phone charger (study lounge, both standing, no phone or cable on screen)
- EP30 Asking a neighbour to keep the noise down (apartment hallway, man in his already-open doorway; recap words needed one-second review pauses)
- EP22 Asking about a delayed order (restaurant, woman seated, waiter standing; muse put the woman near profile and the waiter turned to the lens in the ending in all 3 clip-D takes; the slow intro lips left a 2.4 s gap after the dubbed line -> dubbed the line in two comma parts and trimmed the intro's silent tail before the cut)
- EP23 Asking someone to repeat (language-school lounge, both standing; muse drew the brief's title "EVERYDAY CHINESE #23" on screen in the intro, so prompts carry no title line)
- EP24 Ordering coffee (cafe counter, barista; man in profile in all clip A-C takes; man turned to the lens in the ending in 2 of 2 clip-C takes; timed SCRIPT lines fixed a wrong-lip line)
- EP25 Dropping off laundry (laundry shop counter, clerk, folded coat on the counter; 72-syllable fixed script runs ~18 s at natural pace, not 30 s; clip A came back 704x1248 twice with both faces in profile; ending clip: man turned to the lens in 2 of 3 takes)
- EP26 Getting a library card (library service desk, librarian in a dark-green sweater; 6 added lines on how long, renewing online; still requests with n=2 timed out at the 240 s server limit, n=1 worked; a 5 s CONTINUE_FROM ending clip failed twice (line missing, then the question said twice), so the ending line stayed in the previous full clip; renders 704-720 px wide, faces three-quarter but gaze.py read profile)
- EP27 Buying cinema tickets (cinema ticket counter, clerk in a navy polo; 6 added lines on which film and which hall; man turned to the lens in the final question in 3 of 3 clip-D takes, also with "stays in profile" wording; muse repeated or dropped 复习一下, dubbed in)
- EP35 Asking about a food allergy before ordering (restaurant ordering counter, man in white shirt + brown apron; exact ~69-syllable script kept, 21 s delivered; muse said 过敏 as zhòng kùn in every take even with a pinyin guide, so the whole video was dubbed; all 3 clip-B takes dropped or skipped a recap word or the question, so the recap was dubbed over remapped lips; Vietnamese caption lines cannot show hanzi (font has none), write the pinyin instead)
- EP32 Reporting a leaking faucet (residential maintenance desk, man in a navy work shirt; ~20 s script kept at the user's choice; recap with one vocab card at a time upper-left, synced to the spoken word; man turned to the lens in the ending in all 3 clip-B takes despite the "stays in profile" line, shipped as a named failure)
- EP28 Finding a lost umbrella (mall information desk, clerk; blue umbrella on the counter; vocab cards upper-left added in post)
- EP29 Asking about a gym membership (gym reception desk, staff in a dark-gray polo; 6 added lines on opening hours, what to bring, trainers; the man's 不客气 at the start of clip D was mouthed by the woman in 3 of 3 takes, so the line was dropped and clip D held only the recap and ending; muse's loud music hid the pauses from gaps.py, so pauses were cut on the demucs vocal stem's spans; Whisper merged the recap into one 4.9 s span, so it was dubbed word by word on the vocal-stem spans; 34 s after cutting pauses to 0.8 s; woman near profile in every two-shot line, shipped as a named failure)
- EP33 Buying birthday flowers (flower shop counter, florist in an olive apron; sunflowers in a vase stay on display; recap with three vocab cards upper-left y16-31% to clear her head; script fills only ~22 s at natural pace, so a 40-45 s request needs more lines)
- EP31 Printing a document at a copy shop (print-shop counter, clerk in a brown knit polo; 8 added lines on page count, stapling, wait time; muse said 打印文件 as 单笔/单日万全 in every take, whole video dubbed; muse returned clips A-B at 720p, upscaled before ease_seams; man turned to the lens in the final question in 2 of 3 clip-D takes, take 3 with "camera-shy, never looks into the lens" in CAST held; vocab cards first burned with EP28's copied overlay.py (150 px hanzi, gold border), user said too big, cramped: use `scripts/cards.py`, the EP27 style)
- EP34 Asking how to sort household waste (apartment recycling corner, unlabelled blue/green/grey/red bins, empty plastic bottle on a ledge; recap re-rendered as its own clip from the frame after 谢谢你: take 1 skipped 回收 and stared up at the wall for 5 s when asked to glance at the cards, take 2 with "THREE review words, never skipping one" and "one glance under half a second" kept all words; muse left 3 s after 分类 and 0.3 s after 塑料瓶, so shorten_pauses ran twice (KEEP= the recap, then max 2.0 keep 1.4); 分类 only in the intro close-up and ending, so its card is recap-only)
- EP38 Breaking a banknote (convenience-shop counter, shopkeeper in a forest-green shirt; ~71-syllable fixed script = 21 s at natural pace, not the 40-45 s asked; still asked for the top of both heads at ~40 % of the frame height so upper-left cards (y16-40 %) clear both faces, and it held in the video; intro from a crop of the two-shot woman looking sideways turned to the lens with a ~15-years-older face, a separately generated front-facing still with the same CAST text matched her; woman in profile in both clip-A takes even with "HEAD ANGLES ARE FIXED", man turned to the lens in the recap; dubbed recap without the colon (复习一下零钱、换成、正好) to leave a 0.3 s gap before the final question; first built from a checkout 30 commits behind origin/main, so tone colours and dialogue cards were missing; v2 at the user's request slowed the recap to 1.3-1.7 s review pauses (recap-only clip + separate ending-question clip, TTS on face-mesh lip onsets, one pause stretched with a boomerang insert, muse's drawn title line patched out), 27 s final)
- EP37 Leaving luggage at a storage counter (staffed luggage-storage counter, clerk in a dark-purple polo, her suitcase never handled; ~70-syllable fixed script = 27 s at natural pace, not the 40-45 s asked; muse said 寄存 as yízǒng in every clip and garbled 复习, so the whole video was dubbed; clip A take 1 had the clerk miming her first line; the clerk turned to the lens in the ending in 2 of 3 clip-C takes until he was given a task: looking down at the counter "storage log" from her turn to camera; both faces in profile in the two-shot again, named)
- EP39 Buying a SIM card (phone-shop counter, clerk in a charcoal polo, no phone or SIM handled; ~78-syllable fixed script = 28 s at natural pace, not the 40-45 s asked; clip B gave the woman's line 2 to a male voice, so the whole video was dubbed; recap take 1 skipped 流量, numbering the words ("word 1/2/3, MUST say all three") fixed it; muse left only 0.5 s between 套餐 and 流量 in the recap, named; woman near profile in the two-shot despite a locked camera and "nose at most 20 degrees toward the man", named; thumbnail from the ending frame, where both smile at the lens)

## Template

```
EVERYDAY CHINESE #NN — TITLE
Create a 30–40s vertical 9:16 video, 1080×1920. Photorealistic adults, natural skin, <lighting for the set>.

CAST AND SET
Woman, 25, shoulder-length black hair, <top>, <trousers>. Pleasant female Mandarin voice.
<Male role>, 27, short black hair, <shirt>, <apron/coat>. Warm male Mandarin voice.
Keep established faces and voices if references exist. Clothing stays consistent within this episode.
Woman SCREEN LEFT, <role> SCREEN RIGHT behind counter. Quiet <place>. No moving background people. No food handling, payment or object exchanges.

VOICE AND LIP SYNC
Natural Standard Mandarin (Putonghua), accurate consonants, vowels, tones and tone changes. Pleasant everyday intonation and normal conversational speed throughout.
No regional accent, mispronounced words, slow teaching voice, stretched syllables or sudden acceleration.
Speak ONLY Chinese dialogue; never read pinyin, Vietnamese or instructions.
Replies follow naturally within 0.15–0.3s. No overlap, long silence or extra words.
Finalize audio first; use it for audio-driven lip-sync if supported. Match lips and jaw precisely to each syllable and speech onset/ending.
Strict speaker assignment: female audio moves ONLY the woman's mouth; male audio moves ONLY the man's mouth. Listener stays attentive with mouth relaxed and closed.
Keep mouths visible. Never retime footage after lip-sync. Correct pronunciation and synchronization errors before export.

ACTING AND CAMERA
Relaxed posture, still hands, subtle breathing and ordinary brief blinks. Expressions follow the dialogue.
No nodding, waving, pointing, swaying, eye fluttering, winking or prolonged eye closure.
Eye line: while talking and listening, each person's eyes rest on the other person's face; never on the room, counter, floor or lens, never past the other person. Heads turn only partway toward each other (three-quarter to the camera, never side profile); the eyes carry the rest of the look.
Intro: woman centered, facing camera. One hard cut to a locked medium two-shot. Keep both faces visible.
No alternating close-ups, zooms, pans or further cuts.
For separate clips, use the previous final frame as the next starting reference. Match poses, gaze, hands, background and lighting. Continue motion smoothly; no replayed actions, freezes, jumps or stutter.

SUBTITLES
Three lines: Chinese / pinyin / Vietnamese.
Large, clear white text with dark outline; Chinese largest.
Position x10–82%, y62–76%. Keep faces above text; leave bottom 20% and rightmost 15% clear.
Sync captions to speech. Add exact text in post if needed.

SCRIPT
INTRO: Woman centered, arms relaxed.
WOMAN:
<汉字>
<Pinyin>
<Tiếng Việt>

Cut to counter. Both already looking at each other.

MAN: / WOMAN: ... (same three-line blocks, alternating)

ENDING
Woman gently turns toward camera once, body and hands still. Ask with a small natural smile:
<question 汉字>
<Pinyin>
<Tiếng Việt>

After the final syllable, settle into a gentle closed-mouth smile. End within 0.5s. No extra speech, answer cards, gestures or deliberate blink.

AUDIO
Catchy, soft instrumental, pleasant melody, gentle beat, no vocals. Different track from earlier episodes when references exist.
Music clearly below dialogue; duck during speech.
Clean voices. No chatter, restaurant ambience, hiss, hum, static or sound effects. Continuous music, no restarts or abrupt volume changes.
No logos, watermarks or extra actions.
```
