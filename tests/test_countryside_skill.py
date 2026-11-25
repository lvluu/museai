"""countryside skill: idea bank never repeats, story gate refuses stills and missing clips."""
import importlib.util
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "countryside" / "scripts"


def _load(name):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ideas = _load("ideas")
story = _load("story")


def test_bank_is_unique_and_six_scenes():
    b = ideas.bank()
    assert len(b) == 1000
    assert len({i["id"] for i in b}) == 1000
    assert all(len(i["scenes"]) == 6 for i in b)


def test_next_skips_used_title_and_scenes():
    first = next(ideas.fresh([]))
    h = [{"id": first["id"], "title": first["title"], "scenes": [s["scene"] for s in first["scenes"]],
          "style": "x"}]
    for idea in list(ideas.fresh(h))[:50]:
        assert idea["id"] != first["id"]
        assert idea["title"] != first["title"]
        assert len({s["scene"] for s in idea["scenes"]} & set(h[0]["scenes"])) < 3


def test_style_never_one_of_last_two():
    h = [{"style": "hydrangea-cottage"}, {"style": "meadow-farmhouse"}]
    assert ideas.pick_style(h)["id"] not in {"hydrangea-cottage", "meadow-farmhouse"}


def _filled(tmp_path):
    idea = ideas.bank()[0]
    style = json.loads(ideas.STYLES.read_text())[0]
    st = story.new(idea, style, "t", 6, 20)
    for b in st["beats"]:
        b["shot"], b["move"] = "Wide garden.", "Only the leaves move."
    for s in st["songs"]:
        s["title"] = "a song"
    st["light"] = {k: "soft light" for k in st["light"]}
    return st


def test_template_passes_and_lands_in_range(tmp_path):
    code, msgs = story.check(_filled(tmp_path))
    assert code == 0, msgs
    assert len(story.chapters(_filled(tmp_path))) == 6


def test_still_beat_is_refused(tmp_path):
    st = _filled(tmp_path)
    st["beats"][3]["kind"] = "still"
    code, msgs = story.check(st)
    assert code == 1 and "real video only" in msgs[0]


def test_missing_clip_blocks_compose(tmp_path):
    st = _filled(tmp_path)
    for i in range(1, len(st["beats"])):
        (tmp_path / f"s{i}.mp4").write_bytes(b"x")
    code, msgs = story.check(st, tmp_path)
    assert code == 3 and "never compose from stills" in msgs[0]
    (tmp_path / f"s{len(st['beats'])}.mp4").write_bytes(b"x")
    assert story.check(st, tmp_path)[0] == 0
