"""Usage: pace.py cues.json  -> speaking speed per line; flags lines off daily-conversation pace.
Mandarin daily speech ~4-5 syllables/s, one steady speed for the whole video. Each Han char = 1 syllable, "Wi-Fi" = 2.
Lines of <=3 syllables are not rated (too short). Gaps > MAX_GAP s between lines are flagged.
Fastest / slowest rated line > MAX_SPREAD -> speed is not steady across the video."""
import json
import re
import sys

LOW, HIGH, MAX_GAP, MAX_SPREAD = 3.8, 5.5, 1.0, 1.35
cues = json.load(open(sys.argv[1]))
rates, gaps, prev_end = [], 0, None
for s, e, zh, *_ in cues:
    if prev_end is not None and s - prev_end > MAX_GAP:
        gaps += 1
        print(f"        gap {s - prev_end:.2f}s  LONG PAUSE")
    prev_end = e
    syl = len(re.findall(r"[一-鿿]", zh)) + 2 * zh.count("Wi-Fi")
    rate = syl / max(e - s, 0.01)
    if syl > 3:
        rates.append(rate)
    flag = "short" if syl <= 3 else "TOO SLOW" if rate < LOW else "TOO FAST" if rate > HIGH else "ok"
    print(f"{s:6.2f}-{e:6.2f} {syl:2d} syl {rate:4.1f}/s  {flag:8}  {zh}")
bad = sum(not LOW <= r <= HIGH for r in rates)
spread = max(rates) / min(rates) if rates else 1.0
uneven = spread > MAX_SPREAD
if uneven:
    print(f"        fastest/slowest {spread:.2f}  UNEVEN SPEED (max {MAX_SPREAD})")
print(f"lines off pace: {bad}/{len(rates)}  long pauses: {gaps}  spread {spread:.2f}  "
      f"(target {LOW}-{HIGH} syl/s, spread <= {MAX_SPREAD}, gaps <= {MAX_GAP}s)")
sys.exit(1 if bad or gaps or uneven else 0)
