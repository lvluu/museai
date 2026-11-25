#!/usr/bin/env python3
"""Pick the next countryside playlist film: a mood title, six scenes (one per song) and a style, never repeating.

The bank is built in code (deterministic, 1000 ideas, ids ct-0001..ct-1000): every idea is a mood title plus six
scenes of one calm day (morning -> night), each scene one song long. History: ~/.config/museai/countryside-history.json.

  ideas.py next [--season now|spring|summer|autumn|winter] [--n 3]
  ideas.py show ct-0042
  ideas.py style [--season now]          look/world from styles.json, never one of the last 2, never-used first
  ideas.py record ct-0042 --style ID --slug SLUG [--video PATH]
  ideas.py list

next skips: used ids, a title of the last 40 films, and any idea sharing 3+ scenes with one of the last 3 films.
"""
import argparse
import datetime
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
STYLES = HERE / "styles.json"
HISTORY = Path.home() / ".config" / "museai" / "countryside-history.json"
SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring", 6: "summer", 7: "summer",
           8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}

# Our own mood titles: a place or a feeling, lowercase, 3-6 words. Never another channel's phrases.
TITLES = [
    "the kettle can take its time", "a morning with nowhere to be", "the garden kept me company",
    "just the wind and the curtains", "nothing to fix today", "slow light on the windowsill",
    "the lane goes nowhere in particular", "tea gone cold, still happy", "a day for small chores",
    "the window open all afternoon", "letting the hours wander", "soft rain, warm kitchen",
    "the path through the long grass", "where the bread rises slowly", "a quiet table for one",
    "the bees did all the work", "evening comes in gently", "a basket of nothing much",
    "the house smells of apples", "sitting with the afternoon", "the river doesn't hurry",
    "a page, then another", "watering can mornings", "the last light on the hills",
    "nobody needs me till tomorrow", "the porch and a long sigh", "flowers on every sill",
    "the kind of day you keep", "a gentle sort of tired", "small hands of sunshine",
    "the lamp is on early tonight", "a field of tall quiet", "a cup between two chores",
    "the wind brought the seeds", "a slow cup by the stove", "days that fold like linen",
    "the shed, the soil, the sun", "the bicycle and the hedgerows", "after the rain, the garden",
    "the clock forgot to tick", "a soft place to land", "the hills hold the evening",
    "one jar of jam at a time", "an open door all day", "the meadow after supper",
    "a little hush at noon", "a window full of weather", "wool socks and woodsmoke",
    "the morning took its shoes off", "the slowest walk home",
]

# Scenes by time of day; each scene fills one song (~3 min). {s} = the season word.
SCENES = {
    "morning": ["opening the curtains to the garden", "making coffee on the stove", "watering the flower beds",
                "feeding the cat on the back step", "picking herbs for breakfast", "airing the quilts on the line",
                "a slow breakfast by the window", "walking the lane in the morning mist"],
    "late morning": ["weeding the vegetable patch", "cutting flowers for the house", "cycling to the village bakery",
                     "repotting seedlings in the greenhouse", "hanging laundry in the wind", "picking fruit in the orchard",
                     "sweeping the porch", "carrying water from the stream"],
    "noon": ["a picnic at the edge of the meadow", "lunch on the porch", "reading under a tree",
             "a nap in the hammock", "sketching the garden", "a walk along the shore",
             "sitting by the stream with her feet in the water", "shelling peas on the step"],
    "afternoon": ["baking bread", "making jam on the stove", "arranging flowers in jars", "knitting by the window",
                  "writing a letter at the desk", "tea and cake in the garden room", "pressing flowers in a book",
                  "mending a basket"],
    "dusk": ["the walk home across the fields", "closing the greenhouse", "watching the sun go down from the bench",
             "bringing in the laundry", "cooking a simple supper", "the cat waiting at the gate",
             "lighting the stove", "watering the pots in the last light"],
    "night": ["reading by lamplight", "a bath of warm water and a towel on the chair", "writing in a journal",
              "a cup of milk tea by the window", "rain on the glass, a blanket on her knees",
              "listening to the radio by the stove"],
}
ORDER = ["morning", "late morning", "noon", "afternoon", "dusk", "night"]
SEASON_OK = {"spring": None, "summer": None, "autumn": None,
             "winter": {"a nap in the hammock", "sitting by the stream with her feet in the water",
                        "a picnic at the edge of the meadow", "airing the quilts on the line",
                        "hanging laundry in the wind", "picking fruit in the orchard", "a walk along the shore"}}


def bank():
    rng = random.Random(20261125)
    out, seen = [], set()
    while len(out) < 1000:
        scenes = [rng.choice(SCENES[t]) for t in ORDER]
        title = rng.choice(TITLES)
        key = (title, tuple(scenes))
        if key in seen:
            continue
        seen.add(key)
        seasons = [s for s, bad in SEASON_OK.items() if not bad or not set(scenes) & bad]
        out.append({"id": f"ct-{len(out) + 1:04d}", "title": title, "seasons": seasons,
                    "scenes": [{"time": t, "scene": s} for t, s in zip(ORDER, scenes, strict=True)]})
    return out


def load_history():
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def season_of(arg):
    return SEASONS[datetime.date.today().month] if arg == "now" else arg


def fresh(history, season=None):
    used = {e["id"] for e in history}
    titles = {e.get("title") for e in history[-40:]}
    recent = [set(e.get("scenes", [])) for e in history[-3:]]
    for idea in bank():
        sc = {s["scene"] for s in idea["scenes"]}
        if idea["id"] in used or idea["title"] in titles:
            continue
        if season and season not in idea["seasons"]:
            continue
        if any(len(sc & r) >= 3 for r in recent):
            continue
        yield idea


def pick_style(history, season=None):
    styles = json.loads(STYLES.read_text())
    last = [e.get("style") for e in history[-2:]]
    ok = [s for s in styles if s["id"] not in last and (not season or season in s["seasons"])]
    if not ok:
        return None
    count = {s["id"]: sum(e.get("style") == s["id"] for e in history) for s in ok}
    return min(ok, key=lambda s: count[s["id"]])


def main(argv):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("next")
    n.add_argument("--season")
    n.add_argument("--n", type=int, default=1)
    sub.add_parser("show").add_argument("id")
    st = sub.add_parser("style")
    st.add_argument("--season")
    r = sub.add_parser("record")
    r.add_argument("id")
    r.add_argument("--style", required=True)
    r.add_argument("--slug", required=True)
    r.add_argument("--video", default="")
    sub.add_parser("list")
    a = ap.parse_args(argv)
    h = load_history()
    if a.cmd == "next":
        got = []
        for idea in fresh(h, season_of(a.season) if a.season else None):
            got.append(idea)
            if len(got) >= a.n:
                break
        if not got:
            sys.exit("bank exhausted for this season: add titles or scenes to ideas.py")
        print(json.dumps(got, indent=1))
    elif a.cmd == "show":
        idea = next((i for i in bank() if i["id"] == a.id), None)
        if not idea:
            sys.exit(f"no idea {a.id}")
        print(json.dumps(idea, indent=1))
    elif a.cmd == "style":
        s = pick_style(h, season_of(a.season) if a.season else None)
        if not s:
            sys.exit("no style fits: add one to styles.json")
        print(json.dumps(s, indent=1))
    elif a.cmd == "record":
        idea = next((i for i in bank() if i["id"] == a.id), None)
        if not idea:
            sys.exit(f"no idea {a.id}")
        h.append({"id": a.id, "title": idea["title"], "scenes": [s["scene"] for s in idea["scenes"]],
                  "style": a.style, "slug": a.slug, "video": a.video, "date": datetime.date.today().isoformat()})
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text(json.dumps(h, indent=1))
        print(f"recorded {a.id} ({len(h)} films)")
    else:
        for e in h:
            print(e["date"], e["id"], e["style"], e["slug"], e["title"])


if __name__ == "__main__":
    main(sys.argv[1:])
