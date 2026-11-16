# The Curious Mechanism — Channel Playbook

The objective is to build a recognisable educational media brand, not an automated content factory.

---

## PART 1 — Channel rules

### 1.1 Positioning
The Curious Mechanism explains the hidden stories, engineering, science and design decisions behind ordinary things. Every video answers a question viewers never thought to ask.

### 1.2 Content pillars

| Pillar | Share | Scope | Examples |
|---|---|---|---|
| Everyday Engineering | 40% | How everyday objects work and why they're designed that way | elevators, pens, airplane windows, keyboards, microwaves |
| Invisible Systems | 25% | Hidden infrastructure behind modern life | GPS, undersea cables, bank transfers, power grids |
| Strange Origins | 20% | The odd history of inventions, standards and habits | QWERTY, time zones, A4 paper, the kilogram |
| Forgotten Mechanisms | 15% | Lost inventions and failed experiments | Antikythera mechanism, airships, abandoned concepts |

### 1.3 Topic selection
Every topic must pass five tests, each scored 1–5 (see `templates/topic-scorecard.md`):

| Criterion | Question |
|---|---|
| Curiosity | Does it make people ask *why* or *how*? |
| Relevance | Can ordinary people relate to it? |
| Explanation | Is there something meaningful to reveal? |
| Visual potential | Can we illustrate it well? |
| Evidence | Can we find reliable sources? |

**Approve at ≥ 20/25.** If Evidence scores below 3, reject the topic, however good the rest is.

---

## PART 2 — Production pipeline

1. Topic discovery
2. Research and fact verification
3. Scriptwriting
4. Storyboard and visual planning
5. Illustration generation
6. Voice generation
7. Editing and sound design
8. Thumbnail and title
9. Quality assurance
10. Publishing and analytics

**Order matters:** research first, script second, visuals third. Never generate 50 images before you know what the script needs.

### Step 1 — Topic discovery
Sources: Google autocomplete and "People also ask", Reddit (r/AskEngineers, r/askscience, r/AskHistorians, r/explainlikeimfive, r/DesignPorn), Wikipedia (only as a starting point), museum collections, patent databases, engineering publications.

For each backlog entry, record: working title, central question, main discovery, pillar, visual scenes, source availability and score.

**Rule:** one central question per video.

### Step 2 — Research and verification
- At least **two independent, reliable sources** per important claim.
- Prefer primary sources, technical docs, papers, museums, universities and official bodies.
- Verify dates, numbers, names and mechanisms.
- List myths and disputed explanations explicitly. They often make the best "twist".
- **Never use an AI answer as the only evidence.**
- Use `templates/research-template.md`.

**Non-negotiable:** if you can't verify a claim, cut it or state the uncertainty on screen.

### Step 3 — Scriptwriting
Narration runs at about 140–150 words per minute: 8 min ≈ 1,150 words, 10 min ≈ 1,450 words, 12 min ≈ 1,750 words.

| Time | Section | Purpose |
|---|---|---|
| 0:00–0:20 | Hook | An unexpected observation or contradiction. No channel intro. |
| 0:20–1:30 | Mystery | Why this ordinary detail is worth investigating |
| 1:30–3:30 | Background | History, the original problem or design |
| 3:30–7:30 | Mechanism | How it works: analogies, diagrams, demonstrations |
| 7:30–9:30 | Unexpected discovery | A consequence, overlooked detail or surprising development |
| 9:30–10:00 | Payoff | Answer the question and leave one memorable insight |

Writing rules:
- Write for the ear. Use short, natural sentences.
- One technical idea at a time. Explain jargon or drop it.
- Use analogies for complex mechanisms.
- Avoid filler phrases like "Since the dawn of humanity…".
- Never invent quotes, dialogue or historical scenes.
- Don't stretch a 2-minute answer into 10 minutes.
- Every paragraph explains something, raises a question or moves the story forward.

### Step 4 — Storyboard
Turn the script into scenes with `templates/storyboard-template.md` (prompt 3 in `templates/prompts.md`). Every scene gets a narration excerpt, a visual objective, an image prompt, a camera move, a duration and accuracy notes.

### Step 5 — Illustrations
See `brand/style-guide.md`. Generate the main object first, then close-ups and cutaways. Use real reference images whenever mechanical accuracy matters. **AI illustrations are not automatically accurate technical diagrams.**

Visual budget for a 10-minute video:

| Type | Qty |
|---|---|
| Main illustrations | 12–18 |
| Close-up details | 8–12 |
| Diagrams / cutaways | 4–6 |
| Maps / historical | 2–4 |
| Titles / transitions | 3–5 |

Reuse one illustration as a wide shot, close-up, annotated detail and slow zoom.

### Step 6 — Narration
- A curious storyteller, not a lecturer or an advert.
- Neutral international English, medium pace, warm but restrained, with pauses before reveals.
- **One consistent narrator voice for the whole channel.**
- Check pronunciation of technical terms and proper nouns before export.
- Tool: ElevenLabs (or similar). Check the commercial-use licence on your plan.

### Step 7 — Editing and sound
Tool: DaVinci Resolve (free).

| Scene | Sound |
|---|---|
| Opening mystery | Subtle atmosphere |
| Historical background | Soft orchestral / ambient |
| Technical explanation | Minimal rhythmic bed |
| Unexpected discovery | Brief musical emphasis |
| Conclusion | Calm resolution |

Editing rules:
- Change the composition every 4–8 seconds (a starting guideline).
- Use slow pans, zooms and parallax on still images.
- Highlight key parts with arrows and labels.
- Only use transitions that serve the story. Go easy on sound effects.
- Cut silent gaps and awkward AI pauses.
- Narration must always stay clearly audible.
- Use only licensed music and sound effects (log them in `templates/asset-license-log.md`).

### Step 8 — Title and thumbnail

**Title formulas**
- A: *Why does X…?* → "Why Are Airplane Windows Round?"
- B: *The hidden story of X* → "The Hidden Engineering Inside a Ballpoint Pen"
- C: *How X actually works* → "How GPS Knows Where You Are"

Title rules: one idea, plain language, no "Scientists are TERRIFIED", and never promise a mystery the video doesn't solve.

**Thumbnail checklist**
- One main subject, high contrast, readable on a phone.
- Consistent illustration style.
- 2–4 words maximum, and never just the title repeated.
- No cluttered collages.

### Step 9 — QA
Run `templates/qa-checklist.md`. **Never publish with an unresolved factual error, a misleading thumbnail or a copyright concern because of a deadline.**

### Step 10 — Publish and measure
Schedule: 1 long-form video, 2–3 Shorts and 1 community post per week. Quality beats schedule.

Shorts: give each one its own hook and payoff, so it's a complete mini-story, not a trailer.

---

## PART 3 — Rules you must follow (YouTube, AI, copyright)

| Area | Rule |
|---|---|
| Originality | Each video provides original educational value and real editorial input |
| AI visuals | Allowed, but never to fabricate real-world evidence |
| AI narration | Allowed, but it doesn't replace substance |
| Repetitive content | Don't mass-produce near-identical videos. This is the main monetization risk for AI channels |
| Copyright | Only original, licensed, public-domain or authorised material |
| Realistic synthetic content | Disclose when YouTube's altered/synthetic content policy requires it |
| Accuracy | Separate fact, speculation and disputed theory |
| Thumbnails | Never imply something the video doesn't show |

Notes:
- Using AI doesn't by itself block monetization. The "inauthentic / repetitive content" rules are separate from the AI-disclosure rules.
- Clearly stylised illustrations are generally treated differently from realistic synthetic footage, but assess each video.
- "Copyright-free" doesn't always mean "attribution-free". Read each licence.

**Asset priority order**
1. Your own AI-generated illustrations
2. Public-domain archival material with verified status
3. Properly licensed stock footage and music
4. Creative Commons material, following its conditions exactly

Never assume a Google Images result is free to use.

**Bookmark these and re-check them before monetization and whenever your workflow changes:**
- YouTube channel monetization policies
- YouTube altered or synthetic content disclosure
- YouTube copyright basics
- YouTube Community Guidelines

---

## PART 4 — Metrics

| Metric | Tells you | Starting target* |
|---|---|---|
| Impressions | How often YouTube shows your thumbnail | — |
| CTR | Whether the packaging works | 4–7% |
| Retention at 30 s | Whether the hook works | 65%+ |
| Avg % viewed | Whether the story holds | 40–50% |
| Returning viewers | Whether people want more | rising month over month |
| Subs gained | Whether viewers become an audience | — |

*Working targets, not guarantees or ranking rules.

**How to read the numbers**
- Low CTR + good retention → fix the title and thumbnail.
- High CTR + poor retention → the video doesn't deliver what the packaging promises.
- Strong first 30 s, then a sudden drop → fix the transition into the explanation.
- Good views + few returning viewers → strengthen identity and topic consistency.

Judge patterns across several uploads, never one video.

---

## PART 5 — First three videos

1. **001 — Why Are Airplane Windows Round?** Everyday curiosity, engineering and a strong historical twist.
2. **002 — The Hidden Engineering Inside a Ballpoint Pen.** An accessible mechanism, ideal for cutaways.
3. **003 — The Internet Has a Physical Address.** Expands the channel into invisible infrastructure.

**Advice:** spend week 1 on brand and templates. Then make one complete video, from research to publishing, before automating anything.
