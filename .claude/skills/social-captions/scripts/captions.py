#!/usr/bin/env python3
"""Check per-platform social captions against each platform's hard limits.

Usage:
  captions.py check captions.json   errors (exit 1) on a broken hard limit, warnings for soft rules
  captions.py template              prints an empty captions.json to fill in

captions.json maps each platform id to its caption:
  {"youtube": "title\\n\\ndescription", "tiktok": "...", "facebook": "...", "instagram": "...",
   "x": "...", "threads": "..."}
YouTube's first line is the title (<= 100), the rest after a blank line is the description.
Limits and their sources: ../references/platforms.md. The dashboard (src/museai/api/routes/posting.py
PLATFORMS) shows the same limits as counters.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata

PLATFORMS = ("youtube", "tiktok", "facebook", "instagram", "x", "threads")
# platform: (hard caption limit, max hashtags (hard), max hashtags (soft), first-line fold in chars)
RULES = {
    "youtube": (5000, 60, 5, None),  # > 60 hashtags: YouTube ignores all of them
    "tiktok": (4000, 5, 5, 90),
    "facebook": (2200, None, 3, 125),
    "instagram": (2200, 5, 5, 125),  # 5-hashtag cap since Dec 2025
    "x": (280, None, 2, None),
    "threads": (500, 1, 1, None),  # one topic tag per post
}
HASHTAG = re.compile(r"(?<![\w&])#\w+")
URL = re.compile(r"https?://\S+")
EMPTY_TAGS = {"#fyp", "#foryou", "#foryoupage", "#viral", "#xyzbca", "#trending"}


def x_length(text: str) -> int:
    """X's weighted length (docs.x.com counting-characters): code points in the light ranges count 1,
    everything else (emoji, CJK, Vietnamese letters like ế in U+1E00-1EFF) counts 2, a URL counts 23.
    An emoji's joiners, variation selectors and skin tones add nothing."""
    text = URL.sub("x" * 23, unicodedata.normalize("NFC", text))
    n, prev_emoji = 0, False
    for ch in text:
        c = ord(ch)
        if prev_emoji and (c in (0x200D, 0xFE0F) or 0x1F3FB <= c <= 0x1F3FF):
            continue
        light = c <= 4351 or 8192 <= c <= 8205 or 8208 <= c <= 8223 or 8242 <= c <= 8247
        n += 1 if light else 2
        prev_emoji = c >= 0x1F000 or 0x2600 <= c <= 0x27BF
    return n


def check(captions: dict) -> tuple[list[str], list[str], list[str]]:
    """Returns (errors, warnings, one summary line per platform)."""
    errors, warnings, lines = [], [], []
    for key in set(captions) - set(PLATFORMS):
        errors.append(f"{key}: unknown platform (use {', '.join(PLATFORMS)})")
    for p in PLATFORMS:
        text = str(captions.get(p) or "").strip()
        if not text:
            errors.append(f"{p}: missing caption")
            continue
        limit, max_tags, soft_tags, fold = RULES[p]
        tags = HASHTAG.findall(text)
        body = text
        info = []
        if p == "youtube":
            title, _, body = text.partition("\n")
            title, body = title.strip(), body.strip()
            info.append(f"title {len(title)}/100")
            if len(title) > 100:
                errors.append(f"youtube: title is {len(title)} characters, limit 100")
            elif len(title) > 70:
                warnings.append(f"youtube: title {len(title)} chars, ~70 show in search: front-load the keyword")
            if not body:
                errors.append("youtube: no description (title line, blank line, description)")
            if HASHTAG.search(title):
                warnings.append("youtube: hashtags belong in the description, not the title")
            if "#shorts" not in body.lower():
                warnings.append("youtube: end the description with #Shorts")
        length = x_length(body) if p == "x" else len(body)
        info.append(f"{'weighted ' if p == 'x' else ''}{length}/{limit}")
        if length > limit:
            errors.append(f"{p}: {length} characters, limit {limit}" + (" (X weighted)" if p == "x" else ""))
        info.append(f"{len(tags)} hashtag{'s' * (len(tags) != 1)}")
        if max_tags is not None and len(tags) > max_tags:
            errors.append(f"{p}: {len(tags)} hashtags, limit {max_tags}")
        elif len(tags) > soft_tags:
            warnings.append(f"{p}: {len(tags)} hashtags, best <= {soft_tags}")
        if empty := sorted({t.lower() for t in tags} & EMPTY_TAGS):
            warnings.append(f"{p}: {' '.join(empty)} say nothing about the video: use topic tags")
        first = body.splitlines()[0].strip() if body else ""
        if first.startswith("#"):
            warnings.append(f"{p}: opens with a hashtag: put the hook first")
        if fold and len(first) > fold:
            warnings.append(f"{p}: first line {len(first)} chars, '… more' cuts at ~{fold}: shorten the hook")
        lines.append(f"{p:9} " + " · ".join(info))
    return errors, warnings, lines


def main(argv: list[str]) -> int:
    if argv[:1] == ["template"]:
        print(json.dumps(dict.fromkeys(PLATFORMS, ""), indent=2))
        return 0
    if len(argv) != 2 or argv[0] != "check":
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        captions = json.load(f)
    if not isinstance(captions, dict):
        print(f"{argv[1]}: expected a JSON object of platform -> caption", file=sys.stderr)
        return 1
    errors, warnings, lines = check(captions)
    print("\n".join(lines))
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    print("FAIL" if errors else "PASS")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
