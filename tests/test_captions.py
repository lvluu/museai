import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "captions", ROOT / ".claude/skills/social-captions/scripts/captions.py"
)
captions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(captions)

GOOD = {
    "youtube": "Tập 18 | Quán hết chỗ? Nói câu này để ngồi chung bàn ☕\n\n"
    "Học câu tiếng Trung xin ngồi chung bàn.\n\n#hoctiengtrung #tiengtrung #Shorts",
    "tiktok": "Quán hết chỗ? Nói câu này là được ngồi chung bàn ☕\n#hoctiengtrung #tiengtrung",
    "facebook": "Quán hết chỗ? Nói câu này là được ngồi chung bàn ☕\nLưu lại để dùng nhé!",
    "instagram": "Quán hết chỗ? Nói câu này ☕\n#hoctiengtrung #tiengtrung #learnchinese",
    "x": "Quán hết chỗ? Nói 这里有人吗？☕ #hoctiengtrung",
    "threads": "Quán hết chỗ thì nói gì? 这里有人吗？ Bạn đã thử chưa? #hoctiengtrung",
}


def test_x_length_weights():
    assert captions.x_length("hello") == 5
    assert captions.x_length("这里") == 4
    assert captions.x_length("ế") == 2  # Vietnamese letters in U+1E00-1EFF count 2
    assert captions.x_length("👍🏽") == 2
    assert captions.x_length("see https://example.com/a/very/long/path") == 4 + 23


def test_good_captions_pass(tmp_path):
    errors, _, lines = captions.check(GOOD)
    assert errors == [] and len(lines) == 6
    f = tmp_path / "c.json"
    f.write_text(json.dumps(GOOD, ensure_ascii=False))
    assert captions.main(["check", str(f)]) == 0


def test_hard_limits_fail():
    bad = {
        **GOOD,
        "x": "a" * 281,
        "instagram": "hook " + " ".join(f"#t{i}" for i in range(6)),
        "threads": "hook #one #two",
        "youtube": "t" * 101 + "\n\ndesc #Shorts",
        "myspace": "x",
    }
    del bad["tiktok"]
    errors, _, _ = captions.check(bad)
    text = "\n".join(errors)
    for needle in ("x: 281", "instagram: 6 hashtags", "threads: 2 hashtags", "title is 101",
                   "tiktok: missing", "myspace: unknown"):
        assert needle in text
