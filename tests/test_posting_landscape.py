from __future__ import annotations

import struct

from museai.api.routes import posting


def _box(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(payload), kind) + payload


def _tkhd(w: int, h: int) -> bytes:
    # version 0: flags, times, track id, reserved, duration (24 bytes), then 52 bytes to width / height
    return _box(b"tkhd", bytes(24) + bytes(52) + struct.pack(">II", w << 16, h << 16))


def _mp4(path, w: int, h: int):
    audio = _box(b"trak", _tkhd(0, 0))
    video = _box(b"trak", _tkhd(w, h))
    path.write_bytes(_box(b"ftyp", b"isom" + bytes(4)) + _box(b"mdat", bytes(64)) + _box(b"moov", audio + video))
    return path


def test_landscape_video_posts_on_youtube_only(tmp_path):
    wide = _mp4(tmp_path / "healing-wide.mp4", 1920, 1080)
    tall = _mp4(tmp_path / "healing-tall.mp4", 1080, 1920)
    assert posting._video_size(wide) == (1920, 1080)
    assert posting._platforms(wide, {}) == ["youtube"]
    assert posting._platforms(tall, {}) == list(posting.TIMES["healing"])


def test_chinese_landscape_video_posts_on_every_channel_platform(tmp_path):
    wide = _mp4(tmp_path / "chinese-wide.mp4", 1920, 1080)
    assert posting._channel(wide.name, {}) == "chinese"
    assert posting._platforms(wide, {}) == list(posting.TIMES["chinese"])
    assert posting._platforms(wide, {"channel": "travel"}) == ["youtube"]


def test_unreadable_video_keeps_channel_platforms(tmp_path):
    junk = tmp_path / "healing-junk.mp4"
    junk.write_bytes(b"not an mp4")
    assert posting._video_size(junk) is None
    assert posting._platforms(junk, {}) == list(posting.TIMES["healing"])
