from __future__ import annotations

from datetime import datetime, timezone

from museai.api.routes import posting


def _video(folder, name):
    folder.mkdir(exist_ok=True)
    (folder / posting.FOLDER_MARK).touch()
    (folder / name).write_bytes(b"x")
    return folder / name


def _run(root, videos):
    now = datetime.now(timezone.utc)
    return posting._organize(root, videos, {}, now)


def test_folders_left_parked_by_an_earlier_pass_get_their_names_back(tmp_path):
    """A folder hidden as .museai-renaming-* (an earlier pass failed) is renamed straight to its name."""
    a = _video(tmp_path / f"{posting.PARK_PREFIX}0-1", "ep1.mp4")
    b = _video(tmp_path / f"{posting.PARK_PREFIX}1-1", "ep2.mp4")
    out = _run(tmp_path, [a, b])
    assert not [d for d in tmp_path.iterdir() if d.name.startswith(posting.PARK_PREFIX)]
    assert sorted(p.parent.name.split(" · ")[-1] for p in out) == ["ep1", "ep2"]
    assert all(p.is_file() for p in out)


def test_a_folder_with_two_videos_does_not_break_the_pass(tmp_path):
    two = tmp_path / "Chinese 01 · old"
    _video(two, "ep3.mp4")
    _video(two, "ep3-nov28.mp4")
    other = _video(tmp_path / "Chinese 09 · old", "ep4.mp4")
    out = _run(tmp_path, [two / "ep3.mp4", two / "ep3-nov28.mp4", other])
    assert (two / "ep3.mp4").is_file() and (two / "ep3-nov28.mp4").is_file()
    assert not [d for d in tmp_path.iterdir() if d.name.startswith(posting.PARK_PREFIX)]
    assert len(out) == 3 and all(p.is_file() for p in out)
