---
language: French
language_upper: FRENCH
lang_code: fr
country: France
word_list: the CEFR (DELF A1/A2) reference vocabulary for French (Référentiel / Niveau A1-A2 pour le français)
answer_form: the French noun with its definite article (le/la); words that take l' or les are not used, so the gender is always visible
grammar_check:  and article (le/la)
word_notes:  Never use nouns that start with a vowel or mute h (l' hides the gender) or plural-only nouns. Watch words with a second meaning (la glace = ice cream or ice/mirror, la souris = mouse or computer mouse, la serviette = napkin or towel) and frame the scene so only the meant object is shown.
pronunciation: the broad IPA in slashes, with syllable dots (example: /bu.lɑ̃ʒ.ʁi/); no English-style respelling
pronunciation_example: /ʃa.to/
answer_example: le château
answer_style: article colored by gender, le blue #4DA3FF, la red #FF6B6B; noun in white; the article is always written
voice_says: the article and noun together
scene_example: le pont = a bridge clearly in view
font_rule: Use a font that has all IPA symbols and French accents (é è ê à ç œ), for example DejaVu Sans.
text_layout: Left-to-right text.
---

# French — playbook

Made from `german.md` on 2026-11-05 for the 60-episode French run (A1 1-36, A2 37-60).

## Choices and why

| Item | Choice | Why |
|---|---|---|
| Word list | DELF A1/A2 reference vocabulary | Official level the learner prepares for |
| Answer | le/la + noun, colored le blue, la red | Gender is the hard part; no l'/les words so it is always visible |
| Pronunciation | IPA with syllable dots | Same rule as German: one notation |
| Scenery | France: Paris streets, Provence, Alps, Brittany coast, markets, cafés | |

## Lessons

- 2026-11-05 run, 60 episodes on 2 accounts with 5 chats each: 51 finished in the first chat. 8 needed a second chat (45-min timeouts, or muse.ai went quiet without a final video). All 60 came back 30-60 s long.
- Gate blocks to avoid: niche cues ("desk bell"), B1 words (potager, brouette), cues that name more than the answer ("garden path" for le chemin).
- Topic slugs with accents (café) break browser-harness daemon names; run_account.sh now strips them.

## Check settings

`bash scripts/check_video.sh <file> fr`
