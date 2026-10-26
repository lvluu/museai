"""Usage: budget.py script.txt duration_s
Checks the dialogue fits the clip at everyday pace BEFORE rendering, so the model never has to rush or stretch.
script.txt: one line per turn, "A: 你好..." (speaker label optional). Han char = 1 syllable, "Wi-Fi" = 2.
Need = syllables / 4.5 + 0.3 s per turn change + 1.5 s (start + resting end). Exit 1 when need > duration,
or when need < 75 % of it: muse pads an under-filled clip with silence."""
import re
import sys

RATE, TURN_GAP, PAD, MAX_LINE = 4.5, 0.3, 1.5, 14
lines = [t.split(":", 1)[-1].split("：", 1)[-1].strip() for t in open(sys.argv[1], encoding="utf-8") if t.strip()]
duration = float(sys.argv[2])
syl = [len(re.findall(r"[一-鿿]", t)) + 2 * t.count("Wi-Fi") for t in lines]
need = sum(syl) / RATE + TURN_GAP * (len(lines) - 1) + PAD
for n, line in zip(syl, lines, strict=True):
    if n > MAX_LINE:
        print(f"LONG LINE {n} syl (max {MAX_LINE}, split it): {line}")
print(f"{len(lines)} lines, {sum(syl)} syllables -> needs {need:.1f}s of {duration:.0f}s")
if need > duration:
    print(f"TOO LONG: shorten the script by ~{(need - duration) * RATE:.0f} syllables or extend the clip")
elif need < duration * 0.75:
    print("TOO SHORT: add a line or shorten the clip, otherwise the model drags the speech or adds long pauses")
sys.exit(1 if need > duration or need < duration * 0.75 else 0)
