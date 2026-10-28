"""Usage: qa.py video.mp4 cues.json words.json [expected_cuts=0] [sheet.jpg]
       qa.py video.mp4 --travel [expected_cuts=0] [sheet.jpg]
Quality gate for a muse video. Exit 1 when any check fails.
--travel: no dialogue, so voice/pace are skipped, 16:9 or 9:16 are allowed,
          sound only needs no clipping + audible music, and the sheet samples 12 even frames.
  format  1080x1920 or 4K 2160x3840, 24-30 fps (length is not checked: it follows the dialogue)
  voice   Whisper transcript matches the script (>= 90% of characters, lists missing/extra words)
  sound   no clipping, dialogue loud enough
  noise   no hiss/static floor (quietest 50 ms windows above 7 kHz < -70 dB)
  pace    one steady daily-conversation speed, no long pauses (pace.py)
  pron    Mandarin: every syllable heard with the script's sound and tone (pron.py, Whisper large-v3)
  voices  SPEAKERS=WWM... (one letter per cue): each character keeps one voice (voices.py);
          required for dialogue with 2+ lines per character, missing = FAIL
  gaze    GAZE=CMWM... (one letter per cue, gaze.py): both people look at each other on dialogue
          lines (W/M), only the host looks at the lens on C lines; side profile counts as off.
          Required for dialogue, missing = FAIL
  motion  --travel: nature moves like real footage, not a frozen photo, an in-place warp or a
          time-lapse (motion.py: optical flow per 10 % band)
  smooth  no frozen stretches, duplicated frames or one-frame picture jumps (jumps.py; seams
          not eased with ease_seams.py, muse in-clip snaps), hard cuts == expected (default 0)
  mouth   writes a contact sheet (one frame mid-line per cue) to check realism + lip sync by eye
"""
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

travel = sys.argv[2:3] == ["--travel"]
if travel:
    video, rest = sys.argv[1], sys.argv[3:]
else:
    video, cues_path, words_path = sys.argv[1:4]
    rest = sys.argv[4:]
    cues = json.load(open(cues_path))
# the docs write it as planned_cuts=1; EP23 crashed on that form, so take both
expected_cuts = int(rest[0].removeprefix("planned_cuts=")) if rest else 0
sheet = rest[1] if len(rest) > 1 else Path(video).stem + "_qa.jpg"
fails = []


def norm(text):
    return re.sub(r"[^一-鿿A-Za-z]", "", text.replace("Wi-Fi", "W")).replace("WiFi", "W")


def ffmpeg_log(*vf):
    return subprocess.run(["ffmpeg", "-hide_banner", "-i", video, *vf, "-an", "-f", "null", "-"],
                          capture_output=True, text=True).stderr


# format
probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,avg_frame_rate:format=duration", "-of", "json", video],
                                  capture_output=True, text=True).stdout)
w, h = probe["streams"][0]["width"], probe["streams"][0]["height"]
dur = float(probe["format"]["duration"])
num, den = probe["streams"][0]["avg_frame_rate"].split("/")
fps = float(num) / float(den or 1)
# muse renders 1080p; upscale.sh (run by deliver.sh) makes the delivered file 4K UHD
sizes = ((1080, 1920), (2160, 3840)) + (((1920, 1080), (3840, 2160)) if travel else ())
ok = (w, h) in sizes and 23.5 <= fps <= 30.5
print(f"format  {'ok  ' if ok else 'FAIL'} {w}x{h} {dur:.1f}s {fps:.1f}fps")
ok or fails.append("format")

# voice
if not travel:
    script = norm("".join(c[2] for c in cues))
    heard = norm("".join(x["w"] for x in json.load(open(words_path))))
    sm = difflib.SequenceMatcher(None, script, heard, autojunk=False)
    ratio = sm.ratio()
    ok = ratio >= 0.9
    print(f"voice   {'ok  ' if ok else 'FAIL'} {ratio:.0%} match")
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op != "equal":
            print(f"        {op}: script '{script[a1:a2]}' -> heard '{heard[b1:b2]}'")
    ok or fails.append("voice")

# sound + noise: muse can return a shot with no audio track (scenic-drop-reel Reynisfjara s2);
# travel music replaces clip audio, so only dialogue fails on it
has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                 "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip())
if not has_audio:
    print(f"sound   {'skip' if travel else 'FAIL'} no audio stream")
    print("noise   skip no audio stream")
    travel or fails.append("sound")
else:
    vol = subprocess.run(["ffmpeg", "-hide_banner", "-i", video, "-vn", "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    peak = float(re.search(r"max_volume: (-?[\d.]+)", vol).group(1))
    mean = float(re.search(r"mean_volume: (-?[\d.]+)", vol).group(1))
    floor = -35 if travel else -30
    ok = peak < -0.5 and mean > floor
    print(f"sound   {'ok  ' if ok else 'FAIL'} peak {peak} dB, mean {mean} dB (peak < -0.5, mean > {floor})")
    ok or fails.append("sound")

    # noise: hiss/static shows as a steady floor above 7 kHz in the quietest 50 ms windows
    # (muse returned EP10 clips with white hiss at -51 dB there; clean clips sit near -90 dB)
    rms = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-af",
                          "aresample=48000,highpass=f=7000,highpass=f=7000,asetnsamples=2400,"
                          "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
                          "-f", "null", "-"], capture_output=True, text=True).stdout
    levels = sorted(float(v) for v in re.findall(r"RMS_level=(-?[\d.]+)", rms))
    floor = levels[len(levels) // 10] if levels else -200
    ok = floor < -70
    print(f"noise   {'ok  ' if ok else 'FAIL'} hiss floor {floor:.0f} dB above 7 kHz (< -70; stitch.sh denoises)")
    ok or fails.append("noise")

# pace
if not travel:
    pace = subprocess.run([sys.executable, str(Path(__file__).with_name("pace.py")), cues_path],
                          capture_output=True, text=True)
    bad = [ln for ln in pace.stdout.splitlines() if "TOO" in ln or "LONG" in ln or "UNEVEN" in ln]
    print(f"pace    {'ok  ' if pace.returncode == 0 else 'FAIL'} {pace.stdout.splitlines()[-1]}")
    for line in bad:
        print("       ", line.strip())
    pace.returncode == 0 or fails.append("pace")
# pron: Mandarin lines only; voice >= 90 % passed EP09 v6 with 地铁 heard as 铁铁 and 吃饭 as 区方
if not travel and any(re.search(r"[\u4e00-\u9fff]", c[2]) for c in cues):
    pron = subprocess.run(["uv", "run", "-q", "--no-project", "--python", "3.12", "--with", "faster-whisper",
                           "--with", "pypinyin", "--with", "opencc-python-reimplemented", "python",
                           str(Path(__file__).with_name("pron.py")), video, cues_path], capture_output=True, text=True)
    lines = [ln for ln in pron.stdout.splitlines() if ln.startswith(("FAIL", "RESULT"))]
    print(f"pron    {'ok  ' if pron.returncode == 0 else 'FAIL'} {lines[-1] if lines else pron.stderr[-300:]}")
    for line in lines[:-1]:
        print("       ", line.strip())
    pron.returncode == 0 or fails.append("pron")

# voices: muse picks a new voice per clip; EP09 v7 passed every other check while the user heard
# both characters' voices change between lines (dub.py fixes it)
if not travel:
    who = os.environ.get("SPEAKERS", "")
    if not who:
        print("voices  FAIL set SPEAKERS=<one letter per cue, e.g. WWMWM> to check each character keeps one voice")
        fails.append("voices")
    else:
        vo = subprocess.run(["uv", "run", "-q", "--no-project", "--python", "3.11", "--with", "resemblyzer",
                             "--with", "librosa", "--with", "setuptools", "python",
                             str(Path(__file__).with_name("voices.py")), video, cues_path, who],
                            capture_output=True, text=True)
        lines = [ln for ln in vo.stdout.splitlines() if ln.startswith(("VOICE", "RESULT"))]
        print(f"voices  {'ok  ' if vo.returncode == 0 else 'FAIL'} {lines[-1] if lines else vo.stderr[-300:]}")
        for line in lines[:-1]:
            print("       ", line.strip())
        vo.returncode == 0 or fails.append("voices")

# gaze: EP12 passed voice, pron and voices while the woman sat in profile with wandering eyes and the
# man half-turned to the lens in the ending; the user saw it as AI generated
if not travel:
    targets = os.environ.get("GAZE", "")
    if not targets:
        print("gaze    FAIL set GAZE=<one letter per cue: W/M speaker, C to camera, e.g. CMWMWC> to check eye lines")
        fails.append("gaze")
    else:
        gz = subprocess.run(["uv", "run", "-q", "--no-project", "--python", "3.12", "--with", "mediapipe==0.10.14",
                             "--with", "opencv-python-headless==4.10.0.84", "python",
                             str(Path(__file__).with_name("gaze.py")), video, cues_path, targets,
                             str(Path(video).with_suffix("")) + "_gaze.jpg"],
                            capture_output=True, text=True)
        lines = [ln for ln in gz.stdout.splitlines() if "OFF GAZE" in ln or ln.startswith("RESULT")]
        print(f"gaze    {'ok  ' if gz.returncode == 0 else 'FAIL'} {lines[-1] if lines else gz.stderr[-300:]}")
        for line in lines[:-1]:
            print("       ", line.strip())
        gz.returncode == 0 or fails.append("gaze")

# smooth
freezes = re.findall(r"freeze_duration: ([\d.]+)", ffmpeg_log("-vf", "freezedetect=n=0.0005:d=0.5"))
cuts = re.findall(r"pts_time:([\d.]+)", ffmpeg_log("-vf", "select='gt(scene,0.35)',showinfo"))
# repeated frames (stutter / lag): frames mpdecimate would drop as near-identical to the previous one
kept = len(re.findall(r"pts_time:", ffmpeg_log("-vf", "mpdecimate=hi=64*4:lo=64:frac=0.1,showinfo")))
total = round(dur * fps)
dup = 1 - kept / total if total else 0
sys.path.insert(0, str(Path(__file__).parent))
from jumps import jumps  # noqa: E402

# a planned hard cut is a jump too; it is counted with the cuts instead
snaps = [round(t, 2) for t, *_ in jumps(video) if all(abs(t - float(c)) > 0.1 for c in cuts)]
ok = not freezes and len(cuts) == expected_cuts and dup <= 0.05 and not snaps
print(f"smooth  {'ok  ' if ok else 'FAIL'} freezes={[f'{float(f):.1f}s' for f in freezes]} "
      f"repeated frames {dup:.0%} (max 5%) cuts at {[round(float(c), 2) for c in cuts]} (expected {expected_cuts}) "
      f"jumps at {snaps} (seam -> ease_seams.py, inside a clip -> re-render it)")
ok or fails.append("smooth")

# motion (travel): frozen photo / in-place wobble / time-lapse, which smooth and the sheet miss
if travel:
    mo = subprocess.run(["uv", "run", "-q", "--no-project", "--python", "3.12",
                         "--with", "opencv-python-headless==4.10.0.84", "--with", "numpy", "python",
                         str(Path(__file__).with_name("motion.py")), video], capture_output=True, text=True)
    lines = [ln for ln in mo.stdout.splitlines() if not ln.startswith(("band", "RESULT"))]
    print(f"motion  {'ok  ' if mo.returncode == 0 else 'FAIL'} "
          f"{'; '.join(lines) if lines else 'nature travels at real-time speed' if mo.returncode == 0 else mo.stderr[-300:]}")
    mo.returncode == 0 or fails.append("motion")

# mouth: contact sheet, one frame in the middle of each line (travel: 12 even frames, whole frame)
times = [dur * (i + 0.5) / 12 for i in range(12)] if travel else [(s + e) / 2 for s, e, *_ in cues]
crop = f"scale=270:{270 * h // w}" if travel else "crop=1080:1100:0:0,scale=270:-1"
tile_h = (270 * h // w if travel else 275) + 5
tiles = []
for i, t in enumerate(times):
    tile = Path(sheet).with_suffix(f".{i:02}.jpg")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1",
                    "-vf", crop, str(tile)], check=True)
    tiles.append(tile)
cols = 6
rows = -(-len(tiles) // cols)
inputs = sum((["-i", str(t)] for t in tiles), [])
layout = "|".join(f"{(i % cols) * 270}_{(i // cols) * tile_h}" for i in range(len(tiles)))
subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex",
                f"xstack=inputs={len(tiles)}:layout={layout}:fill=black" if len(tiles) > 1 else "null",
                str(sheet)], check=True)
for t in tiles:
    t.unlink()
if travel:
    print(f"look    look at {sheet}: each tile real place, no invented landmarks, warped buildings, "
          "repeated mountains, HDR halos, text or watermarks; same light and weather throughout")
else:
    print(f"mouth   look at {sheet}: each tile real-looking, same faces/outfits/background, "
          "normal hands, only the line's speaker has an open mouth")

print("RESULT", "PASS" if not fails else "FAIL " + ",".join(fails))
sys.exit(1 if fails else 0)
