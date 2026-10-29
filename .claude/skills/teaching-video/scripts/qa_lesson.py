"""Usage: qa_lesson.py lesson.json final.mp4 final.timeline.json --format 9x16|16x9
Run: uv run --no-project --python 3.12 --with numpy --with librosa --with faster-whisper \\
     --with pypinyin --with opencc-python-reimplemented python scripts/qa_lesson.py ...

Quality gate for one finished lesson export (after compose.py). final.timeline.json is the
placed timeline voice.py dub wrote next to the dubbed teacher video (same times as the final).
  file      name is <topic>_vertical_9x16.mp4 / <topic>_horizontal_16x9.mp4, size matches the
            format, 24-60 fps, 110-130 s, has an audio stream
  loudness  integrated -16 +-1.5 LUFS, true peak <= -1 dBTP
  room      the challenge pause is quiet but not digital silence (-75..-45 dBFS): a dead-zero
            gap between phrases is what makes TTS sound pasted
  pause     the challenge pause is really >= 3 s without voice in the final mix (ticks allowed)
  gaps      no silence > 1.0 s that the lesson did not plan (repeat / challenge pauses)
  prosody   per phrase: pitch range p10-p90 >= 2 semitones (else MONOTONE); syllables per voiced
            second (pauses inside the phrase excluded) in RATE; one-word inline zh skipped
  voices    median pitch of the vi and zh voices within 3 semitones (else the switch sounds like
            two people)
  vi words  Whisper hears each Vietnamese phrase with >= 0.85 similarity, or at most one word off
            (VI=0 skips)
  zh tones  writes zh_cues.json (lines of >= 2 characters) and runs ../muse-video/scripts/pron.py on it
            (PRON=0 skips)
Lip sync: writes <video>.cues.json (every phrase) and prints the muse-video speakers.py command to run.
"""
import difflib
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SIZE = {"9x16": (1080, 1920), "16x9": (1920, 1080)}
NAME = {"9x16": "vertical_9x16", "16x9": "horizontal_16x9"}
SR = 16000
RATE = {"vi": (3.4, 7.0), "zh": (3.5, 7.0), "slow": (2.4, 4.8)}  # syllables per voiced second
fails, warns = [], []


def fail(msg):
    fails.append(msg)
    print("FAIL", msg)


def warn(msg):
    warns.append(msg)
    print("WARN", msg)


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", video],
                         capture_output=True, check=True, text=True).stdout
    return json.loads(out)


def loudness(video):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", video, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary).group(1))
    return i, tp


def pcm(video):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def db(y):
    return 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-9)


def seg(audio, a, b):
    return audio[int(max(a, 0) * SR):int(b * SR)]


def silences(audio, thr=-40.0, win=0.05):
    """[[start, end], ...] where 50 ms windows stay under thr dBFS."""
    n = int(win * SR)
    quiet = [db(audio[i:i + n]) < thr for i in range(0, len(audio) - n, n)]
    out, start = [], None
    for k, q in enumerate(quiet + [False]):
        if q and start is None:
            start = k
        if not q and start is not None:
            out.append([start * win, k * win])
            start = None
    return out


def voiced_time(y, thr=-38.0, win=0.05):
    """seconds of audible speech: commas and sentence breaks inside a phrase do not count"""
    n = int(win * SR)
    return win * sum(db(y[i:i + n]) > thr for i in range(0, len(y) - n + 1, n))


def syllables(it):
    if it["lang"] == "zh":
        return len([c for c in it["text"] if "一" <= c <= "鿿"])
    return len(re.findall(r"[^\s,.;:!?“”\"'()…—-]+", it["text"]))


def semitones(f):
    return 12 * np.log2(f)


def norm_vi(s):
    s = unicodedata.normalize("NFC", s.lower())
    return re.sub(r"[^\w\s]", " ", s).split()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fmt = sys.argv[sys.argv.index("--format") + 1]
    lesson_path, video, tl_path = args[0], args[1], args[2]
    lesson, timeline = json.load(open(lesson_path)), json.load(open(tl_path))
    items = timeline["items"]

    # file
    want = f"{lesson['topic']}_{NAME[fmt]}.mp4"
    if Path(video).name != want:
        fail(f"file name {Path(video).name}, deliver as {want}")
    info = probe(video)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    if (v["width"], v["height"]) != SIZE[fmt]:
        fail(f"size {v['width']}x{v['height']}, {fmt} needs {SIZE[fmt][0]}x{SIZE[fmt][1]}")
    num, den = map(int, v["avg_frame_rate"].split("/"))
    fps = num / den if den else 0
    if not 24 <= fps <= 60:
        fail(f"{fps:.2f} fps")
    dur = float(info["format"]["duration"])
    if not 110 <= dur <= 130:
        fail(f"duration {dur:.1f} s, needs 110-130")
    if not any(s["codec_type"] == "audio" for s in info["streams"]):
        fail("no audio stream")
        return
    print(f"file      {v['width']}x{v['height']} {fps:.2f} fps {dur:.1f} s")

    # loudness
    i, tp = loudness(video)
    print(f"loudness  I {i:.1f} LUFS, true peak {tp:.1f} dBTP")
    if abs(i + 16) > 1.5:
        fail(f"integrated loudness {i:.1f} LUFS, target -16")
    if tp > -1.0:
        fail(f"true peak {tp:.1f} dBTP > -1")

    audio = pcm(video)

    # room tone + challenge pause
    pauses = [it for it in items if it["kind"] == "pause"]
    for p in pauses:
        core = seg(audio, p["start"] + 0.4, p["end"] - 0.4)
        # median of 50 ms windows: the countdown ticks are short and must not count as room tone
        level = float(np.median([db(core[i:i + 800]) for i in range(0, len(core) - 800, 800)]))
        print(f"room      pause {p['start']:.1f}-{p['end']:.1f} s at {level:.1f} dBFS")
        if level < -75:
            fail(f"pause at {p['start']:.1f} s is digital silence ({level:.1f} dBFS); room tone missing")
        if level > -45:
            fail(f"pause at {p['start']:.1f} s is not quiet ({level:.1f} dBFS)")
    quiet = silences(audio)
    no_voice = silences(audio, thr=-30.0)  # countdown ticks (-34 dB) are not the teacher speaking
    if not any(it.get("countdown") for it in pauses):
        fail("no countdown pause in the timeline")
    for p in pauses:
        if p.get("countdown"):
            span = max((min(b, p["end"] + 1) - max(a, p["start"] - 1) for a, b in no_voice
                        if a < p["end"] and b > p["start"]), default=0)
            print(f"pause     challenge silence {span:.2f} s")
            if span < 2.9:
                fail(f"challenge pause only {span:.2f} s of silence, needs >= 3")

    # unplanned gaps
    planned = [(it["start"], it["end"]) for it in pauses]
    planned += [(it["end"], it["end"] + it["repeat"] + 0.6) for it in items if it.get("repeat")]
    first = min(it["start"] for it in items if it["kind"] == "speech")
    last = max(it["end"] for it in items if it["kind"] == "speech")
    for a, b in quiet:
        if b - a > 1.0 and a > first and b < last:
            if not any(pa - 0.6 <= a and b <= pb + 0.6 for pa, pb in planned):
                fail(f"unplanned silence {a:.1f}-{b:.1f} s ({b - a:.1f} s)")

    # prosody per phrase
    import librosa
    med = {"vi": [], "zh": []}
    for it in items:
        if it["kind"] != "speech":
            continue
        y = seg(audio, it["start"], it["end"])
        n = syllables(it)
        f0, voiced, _ = librosa.pyin(y, fmin=120, fmax=450, sr=SR, frame_length=1024)
        f0 = f0[voiced & ~np.isnan(f0)]
        tag = f"{it['id']} {it['lang']} \"{it['text'][:30]}\""
        if len(f0) >= 10:
            st = semitones(f0)
            rng = np.percentile(st, 90) - np.percentile(st, 10)
            med[it["lang"]].append(np.median(f0))
            if rng < 2.0 and n >= 4:
                fail(f"MONOTONE {tag}: pitch range {rng:.1f} st")
        if it.get("inline") or n < 3:
            continue
        rate = n / max(voiced_time(y), 0.1)
        lo, hi = RATE["slow"] if it.get("slow") else RATE[it["lang"]]
        if not lo <= rate <= hi:
            warn(f"rate {tag}: {rate:.1f} syl/s outside {lo}-{hi}")
    if med["vi"] and med["zh"]:
        dv, dz = np.median(med["vi"]), np.median(med["zh"])
        diff = abs(semitones(dv) - semitones(dz))
        print(f"voices    median pitch vi {dv:.0f} Hz, zh {dz:.0f} Hz ({diff:.1f} st apart)")
        if diff > 3:
            fail(f"vi and zh voices {diff:.1f} st apart; the switch sounds like two speakers")

    # Vietnamese words
    if os.environ.get("VI", "1") != "0":
        from faster_whisper import WhisperModel
        model = WhisperModel(os.environ.get("WMODEL", "large-v3"), device="cpu", compute_type="int8")
        pad = np.zeros(SR // 2, np.float32)
        for i, it in enumerate(items):
            if it["kind"] != "speech" or it["lang"] != "vi" or syllables(it) < 3:
                continue
            # stop before the next phrase: the onset of a Chinese word right after made Whisper invent a
            # "subscribe to the channel" outro on a correctly spoken line (2026-10-29, b20s2)
            nxt = items[i + 1]["start"] if i + 1 < len(items) else it["end"] + 0.2
            clip = np.concatenate([pad, seg(audio, it["start"] - 0.15, min(it["end"] + 0.2, max(it["end"], nxt - 0.02))), pad])
            segs, _ = model.transcribe(clip, language="vi", vad_filter=False, condition_on_previous_text=False)
            heard = "".join(s.text for s in segs)
            want_w, got_w = norm_vi(it["text"]), norm_vi(heard)
            sm = difflib.SequenceMatcher(None, want_w, got_w)
            r = sm.ratio()
            # one misheard word in a 3-word phrase is Whisper guessing without context (nhé -> nha), not the voice
            missed = sum(max(a2 - a1, b2 - b1) for op, a1, a2, b1, b2 in sm.get_opcodes() if op != "equal")
            ok = r >= 0.85 or missed <= 1
            print(f"{'ok  ' if ok else 'FAIL'} vi {r:4.0%} {it['text']}  heard {heard.strip()}")
            ok or fails.append(f"vi words {it['id']}")

    # Mandarin tones
    # a lone character (比 inside a Vietnamese sentence, 0.3 s) is too little audio: Whisper invents a
    # sentence for it (2026-10-28: 比 heard as 业务联系中); its tone is the TTS's dictionary reading
    cues = [[it["start"], it["end"], it["text"]] for it in items
            if it["kind"] == "speech" and it["lang"] == "zh" and syllables(it) >= 2]
    cue_path = Path(video).with_name(Path(video).stem + ".zh_cues.json")
    cue_path.write_text(json.dumps(cues, ensure_ascii=False))
    if os.environ.get("PRON", "1") != "0":
        pron = HERE.parent.parent / "muse-video" / "scripts" / "pron.py"
        r = subprocess.run(["uv", "run", "--no-project", "--python", "3.12", "--with", "faster-whisper",
                            "--with", "pypinyin", "--with", "opencc-python-reimplemented", "python", str(pron),
                            video, str(cue_path)], capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode:
            fails.append("zh tones (pron.py)")

    # lip sync runs in its own env (mediapipe): every spoken phrase, one solo speaker
    lines = [[it["start"], it["end"], it["text"]] for it in items if it["kind"] == "speech"]
    all_path = Path(video).with_name(Path(video).stem + ".cues.json")
    all_path.write_text(json.dumps(lines, ensure_ascii=False))
    print(f"lips      run: LEFT=W uv run --no-project --python 3.12 --with mediapipe==0.10.14 "
          f"--with opencv-python-headless==4.10.0.84 --with librosa python ../muse-video/scripts/speakers.py "
          f"{video} {all_path} {'W' * len(lines)} {Path(video).with_suffix('.mouths.jpg')}")

    print("RESULT", "FAIL " + "; ".join(fails) if fails else "PASS", f"({len(warns)} warnings)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
