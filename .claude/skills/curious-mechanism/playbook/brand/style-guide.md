# Brand & Visual Style Guide

**Name:** The Curious Mechanism
**Tagline:** *Nothing is ordinary when you understand how it works.*
**Aesthetic:** 19th-century scientific encyclopedias, patent drawings, museum archives.

## Colour palette

| Name | Hex | Use |
|---|---|---|
| Antique paper | `#EFE6D2` | Backgrounds |
| Ink blue | `#1F3A5F` | Primary linework, headings |
| Charcoal | `#2B2B2B` | Body linework, text |
| Muted red | `#A63D32` | Accents, arrows, highlights (sparingly) |
| Brass | `#B08D57` | Mechanical details, logo accent |

## Typography

| Role | Font | Notes |
|---|---|---|
| Headlines / titles | Libre Baskerville or Cormorant Garamond | Serif, editorial |
| Supporting text | Inter or Source Sans 3 | Clean, legible |
| Labels / annotations | Inter, small caps, letter-spacing +8% | Uppercase editorial labels |

All of these are free on Google Fonts. Save copies in `brand/fonts/`.

## Logo direction
- A monogram "CM" or a single engraved gear/cog combined with a magnifying glass or keyhole.
- Ink blue on antique paper, with an optional brass accent.
- It must read at 48×48 px as the channel avatar.
- Store the source files and exports in `brand/logo/`.

## Illustration rules
- Engraved, ink-drawing look with fine cross-hatching.
- Show cross-sections and mechanical details.
- Keep proportions and geometry consistent across a video.
- Limited palette (above).
- **No photorealistic AI images mixed into the illustrated look.**
- Avoid distorted or fake text in images. Add labels in the editor instead.
- Use real reference photos to check mechanical accuracy.

## Master illustration prompt

```
Create an educational scientific illustration in the style of a 19th-century engineering encyclopedia.

Subject: [OBJECT OR MECHANISM]
Show: [SPECIFIC VISUAL DETAIL]

Style:
- Detailed hand-engraved ink illustration
- Antique ivory paper background
- Fine cross-hatching and precise linework
- Muted navy blue and charcoal ink, occasional muted red accent
- Subtle vintage imperfections
- Scientifically plausible proportions
- Museum-quality technical drawing

Composition: 16:9 landscape, clear central subject, visually readable, suitable for an educational documentary.

Avoid: modern photography, photorealism, cartoon characters, excessive decoration, random labels, watermarks, illegible text.
```

**Variants**
- *Cutaway:* add "cutaway cross-section revealing internal components, exploded-view style".
- *Close-up:* add "macro detail view, tight framing on [part]".
- *Map:* swap the style for "antique hand-drawn cartographic map, sepia and ink blue, compass rose".
- *Shorts (9:16):* change the composition to "9:16 vertical portrait, subject in upper two-thirds".

## Thumbnail template
- 1280×720, antique paper background.
- One large illustrated subject, offset slightly from centre.
- An optional comparison inset (e.g. square vs round).
- 2–4 words in Libre Baskerville Bold, ink blue or muted red, with a thin charcoal outline.
- Small brass "CM" mark in the bottom-right corner.
- Store the template file (Canva/Figma/PSD) in `brand/thumbnail-template/`.

## Motion rules
- Slow Ken Burns zooms and pans (5–10% scale over the shot).
- Parallax: separate the foreground object from the paper background.
- Draw-on line animations for diagrams.
- Use AI image-to-video (Kling/Runway) sparingly, only when the movement explains something.

## Narrator voice
- One consistent voice. Record the voice name/ID here: `__________`
- Settings (stability, style, speed): `__________`
