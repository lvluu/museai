"""Usage: qa.py video.mp4 cues.json words.json [expected_cuts=0] [sheet.jpg]
       qa.py video.mp4 --travel [expected_cuts=0] [sheet.jpg]
Quality gate for a muse video. Exit 1 when any check fails.
--travel: no dialogue, so voice/pace are skipped, 16:9 or 9:16 are allowed,
          sound only needs no clipping + audible music, and the sheet samples 12 even frames.
  format  1080x1920, 24-30 fps (length is not checked: it follows the dialogue)
  voice   Whisper transcript matches the script (>= 90% of characters, lists missing/extra words)
  sound   no clipping, dialogue loud enough
  pace    one steady daily-conversation speed, no long pauses (pace.py)
  smooth  no frozen stretches or duplicated frames, number of hard cuts == expected (default 0)
  mouth   writes a contact sheet (one frame mid-line per cue) to check realism + lip sync by eye
"""
import difflib
import json
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
expected_cuts = int(rest[0]) if rest else 0
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
if travel:
    ok = (w, h) in ((1080, 1920), (1920, 1080)) and 23.5 <= fps <= 30.5
else:
    ok = (w, h) == (1080, 1920) and 23.5 <= fps <= 30.5
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

# sound
vol = subprocess.run(["ffmpeg", "-hide_banner", "-i", video, "-vn", "-af", "volumedetect", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
peak = float(re.search(r"max_volume: (-?[\d.]+)", vol).group(1))
mean = float(re.search(r"mean_volume: (-?[\d.]+)", vol).group(1))
floor = -35 if travel else -30
ok = peak < -0.5 and mean > floor
print(f"sound   {'ok  ' if ok else 'FAIL'} peak {peak} dB, mean {mean} dB (peak < -0.5, mean > {floor})")
ok or fails.append("sound")

# pace
if not travel:
    pace = subprocess.run([sys.executable, str(Path(__file__).with_name("pace.py")), cues_path],
                          capture_output=True, text=True)
    bad = [ln for ln in pace.stdout.splitlines() if "TOO" in ln or "LONG" in ln or "UNEVEN" in ln]
    print(f"pace    {'ok  ' if pace.returncode == 0 else 'FAIL'} {pace.stdout.splitlines()[-1]}")
    for line in bad:
        print("       ", line.strip())
    pace.returncode == 0 or fails.append("pace")

# smooth
freezes = re.findall(r"freeze_duration: ([\d.]+)", ffmpeg_log("-vf", "freezedetect=n=0.0005:d=0.5"))
cuts = re.findall(r"pts_time:([\d.]+)", ffmpeg_log("-vf", "select='gt(scene,0.35)',showinfo"))
# repeated frames (stutter / lag): frames mpdecimate would drop as near-identical to the previous one
kept = len(re.findall(r"pts_time:", ffmpeg_log("-vf", "mpdecimate=hi=64*4:lo=64:frac=0.1,showinfo")))
total = round(dur * fps)
dup = 1 - kept / total if total else 0
ok = not freezes and len(cuts) == expected_cuts and dup <= 0.05
print(f"smooth  {'ok  ' if ok else 'FAIL'} freezes={[f'{float(f):.1f}s' for f in freezes]} "
      f"repeated frames {dup:.0%} (max 5%) cuts at {[round(float(c), 2) for c in cuts]} (expected {expected_cuts})")
ok or fails.append("smooth")

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
