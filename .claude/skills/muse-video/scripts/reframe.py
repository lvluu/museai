"""Usage: reframe.py video.mp4 report.json plan.json [cue_lines...]
Turns the lines speakers.py flagged LISTENER MOUTH MOVES into punch-ins on the speaker
(shot / reverse shot), so the miming listener is off screen. Footage is only cropped, never
retimed, so lip sync is kept. Run speakers.py with REPORT=report.json on the edit first, then
  python3 scripts/reframe.py edit.mp4 report.json plan.json && python3 scripts/cutedit.py plan.json out.mp4
and run speakers.py on out.mp4 again: punch-in lines then have no listener to check.
Extra arguments are 1-based line numbers to punch in as well (e.g. a line whose listener face
was not found and that you saw miming on the mouth sheet).
Each punch-in starts 0.15 s before its line and runs until 0.15 s before the next line.
The crop is 9:16, 55 % of the frame width, centred on the speaker's median face, with the face
centre at 33 % of the crop height so the chin stays above the caption box (y57 %)."""
import json
import subprocess
import sys

video, report, out = sys.argv[1:4]
extra = {int(x) for x in sys.argv[4:]}
lines = json.load(open(report))
W, H = (int(x) for x in subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", video],
    capture_output=True, text=True, check=True).stdout.strip().split(","))
end = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                           capture_output=True, text=True, check=True).stdout)
CW = 0.55  # crop width as a fraction of the frame width


def crop(box):
    cw = int(CW * W) // 2 * 2
    ch = int(cw * 16 / 9) // 2 * 2
    x = min(max(int(box[0] * W - cw / 2), 0), W - cw)
    y = min(max(int(box[1] * H - 0.33 * ch), 0), H - ch)
    return f"{cw}:{ch}:{x}:{y}"


spans = []  # [start, end, crop, speaker]
for i, ln in enumerate(lines):
    if not (any("LISTENER" in f for f in ln["flags"]) or ln["line"] in extra) or not ln["box"]:
        continue
    a = max(0.0, ln["start"] - 0.15)
    b = lines[i + 1]["start"] - 0.15 if i + 1 < len(lines) else end
    if spans and spans[-1][3] == ln["speaker"] and a - spans[-1][1] < 0.6:
        spans[-1][1] = b  # same speaker again: one punch-in
    else:
        spans.append([a, b, crop(ln["box"]), ln["speaker"]])
segs, t = [], 0.0
for a, b, c, _ in spans:
    a = max(a, t)
    if a - t > 0.05:
        segs.append([0, round(t, 3), round(a, 3), None, 0])
    segs.append([0, round(a, 3), round(b, 3), c, 0])
    t = b
if end - t > 0.05:
    segs.append([0, round(t, 3), round(end, 3), None, 0])
json.dump({"inputs": [video], "segments": segs}, open(out, "w"))
print(f"{len(spans)} punch-ins -> {out}")
for s in segs:
    print(s)
