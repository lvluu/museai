#!/usr/bin/env python3
"""Write one muse clip prompt per word (clip1.txt ... clip6.txt) and episode.json for build.py.

Words file: 6 lines "English | answer | pronunciation | scene", in quiz order; lines starting with # are ignored.
The scene is one sentence that shows the object clearly (example: "a single sheet of white paper on a wooden
school desk, close-up"). Fails if a word was already used for this language in log.md -> Vocabulary by another
episode (a re-render of the same episode number may reuse its own words).
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
REQUIRED = ("LANGUAGE", "LANG_CODE", "COUNTRY", "TTS_VOICE")


def front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        sys.exit(f"{path}: no front matter")
    values = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        values[key.strip().upper()] = value.strip()
    return values


def read_words(path: Path) -> list[list[str]]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    words = [[f.strip() for f in line.split("|")] for line in lines]
    if len(words) != 6 or any(len(w) != 4 or not all(w) for w in words):
        sys.exit(f"{path}: need exactly 6 lines of 'English | answer | pronunciation | scene'")
    return words


def used_answers(language: str, episode: int) -> set[str]:
    """Answers logged for this language in log.md -> Vocabulary by other episodes."""
    log = SKILL / "log.md"
    if not log.exists():
        return set()
    table = log.read_text(encoding="utf-8").split("## Vocabulary", 1)[-1]
    used = set()
    for line in table.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # Columns: Episode # | Language | Level | Topic | English | Answer | Pronunciation
        if len(cells) == 7 and cells[1].lower() == language.lower() and cells[0] != str(episode):
            used.add(cells[5].lower())
    return used


def article_colors(spec: str) -> dict:
    """'der #4DA3FF, die #FF6B6B' -> {'der': '#4DA3FF', 'die': '#FF6B6B'}"""
    return {k: v for k, v in (p.split() for p in spec.split(",") if p.strip())}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lang", required=True, help="file name in languages/, e.g. german")
    ap.add_argument("--level", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--next-level", required=True)
    ap.add_argument("--next-topic", required=True)
    ap.add_argument("--words", required=True, type=Path, help="file with the 6 picked words")
    ap.add_argument("--episode", required=True, type=int, help="episode number from series.md")
    ap.add_argument("--out", required=True, type=Path, help="episode work folder")
    a = ap.parse_args()

    lang_file = SKILL / "languages" / f"{a.lang}.md"
    if not lang_file.exists():
        sys.exit(f"No playbook {lang_file}. Copy languages/_new-language.md first.")
    values = front_matter(lang_file)
    empty = [k for k in REQUIRED if not values.get(k)]
    if empty:
        sys.exit(f"{lang_file}: fill these keys: {', '.join(k.lower() for k in empty)}")

    words = read_words(a.words)
    repeated = [w[1] for w in words if w[1].lower() in used_answers(values["LANGUAGE"], a.episode)]
    if repeated:
        sys.exit(f"Already used in log.md: {', '.join(repeated)}")

    a.out.mkdir(parents=True, exist_ok=True)
    template = (SKILL / "clip-template.md").read_text(encoding="utf-8")
    for i, (english, answer, _, scene) in enumerate(words, 1):
        fill = {
            "LANGUAGE": values["LANGUAGE"],
            "COUNTRY": values["COUNTRY"],
            "ENGLISH": english,
            "ANSWER": answer,
            "SCENE": scene,
        }
        prompt = re.sub(
            r"\{([A-Z_]+)\}", lambda m, fill=fill: fill.get(m.group(1), m.group(0)), template
        )
        left = sorted(set(re.findall(r"\{[A-Z_]+\}", prompt)))
        if left:
            sys.exit(f"Unfilled placeholders: {', '.join(left)}")
        (a.out / f"clip{i}.txt").write_text(prompt.strip() + "\n", encoding="utf-8")

    episode = {
        "episode": a.episode,
        "language": values["LANGUAGE"],
        "lang_code": values["LANG_CODE"],
        "level": a.level,
        "topic": a.topic,
        "next_level": a.next_level,
        "next_topic": a.next_topic,
        "tts_voice": values["TTS_VOICE"],
        "article_colors": article_colors(values.get("ARTICLE_COLORS", "")),
        "font_bold": values.get("FONT_BOLD", ""),
        "font_regular": values.get("FONT_REGULAR", ""),
        "words": [{"english": e, "answer": ans, "pron": p} for e, ans, p, _ in words],
    }
    (a.out / "episode.json").write_text(
        json.dumps(episode, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {a.out}/clip1.txt ... clip6.txt and episode.json")


if __name__ == "__main__":
    main()
