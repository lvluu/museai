"""Narrate a place-story: one voice-over line per beat with Kokoro (local, Apache-2.0, natural English).

  uv run --no-project --python 3.11 --with "kokoro>=0.9" --with soundfile --with "misaki[en]" \
      python scripts/vo.py story.json [--voice af_heart] [--speed 0.95]

Each beat's `vo` is what the narrator says (`say` overrides it for pronunciation: "Pnom Koolen",
"Taa Prome"); writes vo/b<N>.wav next to story.json, which compose.py lays under its beat and times the
beat to. Voices: af_heart (warm female, default), af_bella, am_michael (male), bf_emma (British).
edge-tts stays out: its voices sounded like AI to the user (muse-video dub.py, 2026-10-30).
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

SR = 24000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--voice", default="af_heart")
    ap.add_argument("--speed", type=float, default=0.95)
    a = ap.parse_args()
    story_path = Path(a.story).resolve()
    story = json.loads(story_path.read_text())
    out = story_path.parent / "vo"
    out.mkdir(exist_ok=True)
    pipe = KPipeline(lang_code="b" if a.voice.startswith("b") else "a")
    for i, b in enumerate(story["beats"], 1):
        text = b.get("say") or b.get("vo")
        if not text:
            continue
        audio = np.concatenate([np.asarray(chunk) for _, _, chunk in pipe(text, voice=a.voice, speed=a.speed)])
        sf.write(out / f"b{i}.wav", audio, SR)
        print(f"b{i}: {len(audio) / SR:4.1f} s  {text}")


if __name__ == "__main__":
    main()
