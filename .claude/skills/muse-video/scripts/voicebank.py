"""Voice bank: natural muse voices that dub.py clones, rotated so videos don't all sound alike.
  python3 scripts/voicebank.py list
  python3 scripts/voicebank.py pick W [M ...] --for work/dubbed.mp4      (what dub.py does itself)
  uv run --no-project --python 3.11 --with demucs --with soundfile --with faster-whisper \\
      --with resemblyzer --with librosa --with setuptools --with pypinyin \\
      python scripts/voicebank.py harvest [--dry] [--tasks data/tasks.json] data/media/vid_*.mp4
Each voice is 1.2-9 s of one muse character's lines from one render, cut from muse's vocal stem
(demucs), with the script text those lines say: voices/<id>.wav + an entry in voices/bank.json.
Ids read <gender>-<register>-<n>: W/M by pitch (female > 165 Hz) and register low / mid / high by
median pitch (W < 200 / > 250 Hz, M < 110 / > 140 Hz), so a brief can ask for a deep-voiced clerk
(`VOICE_M=M-low-*`). muse's own voices sound human; the fixed edge-tts pair (Xiaoxiao + Yunjian) on
every dubbed episode sounded like AI and the same two people every day (user, 2026-10-29).
  pick     one voice per letter for a video, least recently used first, never the same voice for
           two characters. The choice is kept per output path in ~/Movies/museai/voice-usage.json,
           so re-dubbing the same video keeps its voices.
  harvest  takes raw muse renders from the server (data/media/vid_*.mp4) and the prompt each was
           rendered from (data/tasks.json). Whisper finds the spoken lines and each is matched to a
           SCRIPT line ("2.3-3.4 s: MAN speaks ...: 一般两三天。"). The reference text must be what
           the audio says: the first bank took Whisper's segments with the whole script line, and
           muse's slurred 包裹, a cut-off 十五 or a line split over two segments left text the audio
           did not say; F5 then added a sound before nearly every cloned line (EP42 付好了 -> Save好了,
           请问 -> 给请问; 31 of 36 test lines right after the fix, the rest caught by clone_tts.py).
           So a segment is kept only when >= 85 % of its syllables are heard as the script says them
           (spoken()), with the part of the script it covers as text, cut on Whisper's words (not the
           segment, which can open with seconds of music), never with digits or latin in it. A
           character's kept lines in one render are joined (0.3 s apart, up to 9 s) into one
           reference; the longest reference of a voice wins and a voice already in the bank
           (resemblyzer similarity >= 0.75) is skipped. Vocal stems are kept in ~/.cache/museai/voice-stems."""
import difflib
import fnmatch
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BANK_DIR = os.path.join(HERE, "..", "voices")
BANK = os.path.join(BANK_DIR, "bank.json")
USAGE = os.path.expanduser(os.environ.get("VOICE_USAGE", "~/Movies/museai/voice-usage.json"))
SR = 24000
STEMS = os.path.expanduser("~/.cache/museai/voice-stems")  # demucs vocal stems per render


def load():
    return json.load(open(BANK)) if os.path.exists(BANK) else []


def voice(vid):
    """The bank entry for an id; ref is an absolute path."""
    for v in load():
        if v["id"] == vid:
            return {**v, "ref": os.path.join(BANK_DIR, v["file"])}
    sys.exit(f"voice {vid} is not in {BANK} (voicebank.py list)")


def pick(letters, key, wanted=None):
    """{letter: bank id} for one video. wanted maps a letter to an id or a glob like 'M-low-*'."""
    wanted = wanted or {}
    use = json.load(open(USAGE)) if os.path.exists(USAGE) else {"videos": {}, "last": {}}
    key = os.path.abspath(key)
    got = dict(use["videos"].get(key, {}))
    bank = load()
    for who in letters:
        w = wanted.get(who)
        if who in got and (not w or fnmatch.fnmatch(got[who], w)):
            continue
        pool = [v["id"] for v in bank if v["gender"] == who and v["id"] not in got.values()
                and fnmatch.fnmatch(v["id"], w or "*")]
        if not pool:
            sys.exit(f"no voice in the bank for {who}{' ' + w if w else ''}: harvest some (voicebank.py harvest)")
        random.shuffle(pool)
        got[who] = min(pool, key=lambda i: use["last"].get(i, 0))
    now = time.time()
    for i in got.values():
        use["last"][i] = now
    use["videos"][key] = got
    os.makedirs(os.path.dirname(USAGE), exist_ok=True)
    json.dump(use, open(USAGE, "w"), indent=1)
    return got


def register(g, f0):
    lo, hi = (200, 250) if g == "W" else (110, 140)
    return "low" if f0 < lo else "high" if f0 > hi else "mid"


def script_lines(prompt):
    """[(speaker, hanzi text)] of the SCRIPT lines in a muse-video prompt."""
    out = []
    for line in prompt.splitlines():
        m = re.match(r"\s*[\d.]+\s*-\s*[\d.]+\s*s:\s*([A-Z]+)\b.*:\s*([^:]*[\u4e00-\u9fff][^:]*)$", line)
        if m:
            out.append((m.group(1), re.sub(r"\s*\([^)]*\)", "", m.group(2)).strip()))  # drop "(pinyin)"
    return out


def hanzi(t):
    return re.sub(r"[^\u4e00-\u9fff]", "", t)


def spoken(heard, script):
    """The part of a script line that a heard segment says, with the script's own characters and
    marks, or None when under 85 % of that part's syllables were heard (muse slurred it)."""
    from pypinyin import lazy_pinyin

    chars = [(i, c) for i, c in enumerate(script) if re.match(r"[\u4e00-\u9fff]", c)]
    want, got = lazy_pinyin([c for _, c in chars]), lazy_pinyin(hanzi(heard))
    blocks = [b for b in difflib.SequenceMatcher(None, want, got, autojunk=False).get_matching_blocks() if b.size]
    if not blocks:
        return None
    a0, a1 = blocks[0].a, blocks[-1].a + blocks[-1].size
    if a1 - a0 < 4 or sum(b.size for b in blocks) < 0.85 * max(a1 - a0, len(got)):
        return None
    text = script[chars[a0][0]:chars[a1 - 1][0] + 1]
    return text + (script[chars[a1 - 1][0] + 1:][:1] or "。")


def harvest(videos, dry, tasks):
    import librosa
    import numpy as np
    import soundfile as sf
    from faster_whisper import WhisperModel
    from resemblyzer import VoiceEncoder, preprocess_wav

    enc = VoiceEncoder("cpu", verbose=False)
    asr = WhisperModel("large-v3", device="cpu", compute_type="int8")
    gap = np.zeros(int(0.3 * SR), np.float32)

    def embed(y):
        return enc.embed_utterance(preprocess_wav(librosa.resample(y, orig_sr=SR, target_sr=16000), source_sr=16000))

    def pitch(y):
        return float(np.nanmedian(librosa.pyin(y, fmin=70, fmax=400, sr=SR)[0]))

    prompts = {}
    for t in json.load(open(tasks)):
        url = (t.get("result") or {}).get("url", "")
        if t.get("kind") == "video" and url:
            prompts[os.path.basename(url)] = t["request"].get("prompt", "")
    bank = load()
    known = [embed(librosa.load(os.path.join(BANK_DIR, v["file"]), sr=SR)[0]) for v in bank]
    os.makedirs(BANK_DIR, exist_ok=True)
    os.makedirs(STEMS, exist_ok=True)
    found = []  # (reference audio, its text, speaker, render)
    for video in videos:
        lines = script_lines(prompts.get(os.path.basename(video), ""))
        if not lines:
            continue  # no dialogue script (travel, product shots) or not rendered by this server
        stem = os.path.join(STEMS, os.path.basename(video)[:-4] + ".wav")
        if not os.path.exists(stem):  # demucs is the slow part; keep stems so a re-harvest is quick
            tmp = tempfile.mkdtemp()
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "2", "-ar", "44100",
                            f"{tmp}/mix.wav"], check=True)
            subprocess.run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", tmp,
                            f"{tmp}/mix.wav"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.replace(f"{tmp}/htdemucs/mix/vocals.wav", stem)
        voc, _ = librosa.load(stem, sr=SR, mono=True)
        segs, _ = asr.transcribe(librosa.resample(voc, orig_sr=SR, target_sr=16000), language="zh",
                                 word_timestamps=True, condition_on_previous_text=False)
        parts = {}  # speaker -> [(segment audio, spoken script text)] in time order
        for s in segs:
            words = [w for w in s.words if hanzi(w.word)]
            if not words or re.search(r"[0-9A-Za-z]", s.text):
                continue  # Whisper wrote 十五 as 15: the script's 十五 may be cut off the text
            who, text = max(((difflib.SequenceMatcher(None, hanzi(s.text), hanzi(t)).ratio(), w, t)
                             for w, t in lines))[1:]
            text = spoken(s.text, text)
            # cut on the words, not the segment: a segment can open with seconds of music or breath
            y = voc[int(max(words[0].start - 0.12, 0) * SR):int((words[-1].end + 0.15) * SR)]
            y, _ = librosa.effects.trim(y, top_db=35)
            if not text or not 0.8 <= len(y) / SR <= 9:
                continue
            h = len(y) // 2
            if max(pitch(y[:h]), pitch(y[h:])) / min(pitch(y[:h]), pitch(y[h:])) > 1.4:
                continue  # two people in one segment
            parts.setdefault(who, []).append((y, text))
        for who, ps in parts.items():
            # one character in one render keeps one voice: join its lines into one longer reference
            # (up to 9 s; muse gives a character 1-5 s of clearly said lines per render)
            es = [embed(y) for y, _ in ps]
            mean = np.mean(es, axis=0)
            ps = [p for p, e in zip(ps, es, strict=True) if float(e @ mean) / np.linalg.norm(mean) >= 0.75]
            y, text = np.zeros(0, np.float32), ""
            for py, pt in ps:
                if len(y) and (len(y) + len(gap) + len(py)) / SR > 9:
                    break
                y, text = np.concatenate([y, gap, py]) if len(y) else py, text + pt
            if len(y) / SR >= 1.2:
                found.append((y, text, who, os.path.basename(video)))
    # the longest take of a voice wins: several renders reuse one muse voice
    for y, text, who, src in sorted(found, key=lambda c: -len(c[0])):
        e = embed(y)
        if known and max(float(e @ k) for k in known) >= 0.75:
            continue  # a voice the bank already has
        f0 = pitch(y)
        g = "W" if f0 > 165 else "M"
        reg = register(g, f0)
        n = 1 + sum(v["gender"] == g and v["register"] == reg for v in bank)
        vid = f"{g}-{reg}-{n:02d}"
        print(f"{'(dry) ' if dry else ''}{vid}  {f0:3.0f} Hz  {len(y) / SR:3.1f} s  {who}: {text}  <- {src}")
        known.append(e)
        if dry:
            continue
        sf.write(os.path.join(BANK_DIR, f"{vid}.wav"), y / (np.abs(y).max() + 1e-9) * 0.9, SR)
        bank.append({"id": vid, "gender": g, "register": reg, "f0": round(f0), "file": f"{vid}.wav",
                     "text": text, "source": src})
        json.dump(bank, open(BANK, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "list":
        use = json.load(open(USAGE)) if os.path.exists(USAGE) else {"last": {}}
        for v in load():
            last = use["last"].get(v["id"])
            print(f"{v['id']:10} {v['f0']:3} Hz  last used {time.strftime('%Y-%m-%d', time.localtime(last)) if last else 'never':10}  {v['text']}")
    elif cmd == "pick":
        key = args[args.index("--for") + 1]
        print(json.dumps(pick([a for a in args[: args.index("--for")]], key)))
    elif cmd == "harvest":
        tasks = args[args.index("--tasks") + 1] if "--tasks" in args else "data/tasks.json"
        harvest([a for a in args if a.endswith(".mp4")], "--dry" in args, tasks)
    else:
        sys.exit(__doc__)
