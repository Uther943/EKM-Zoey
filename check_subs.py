"""Check that the English subtitle units reproduce the source script exactly.

  python check_subs.py                 -> L0 intro
  python check_subs.py --section ch1   -> videos/L0/source/scripts/ch1.json  (--video for another video)
"""
import argparse
import json
import sys

from sections import add_section_arg, paths
from tts import join_parts, split_parts

MAX_PART = 95  # characters per English subtitle line

ap = argparse.ArgumentParser()
add_section_arg(ap)
a = ap.parse_args()
P = paths(a.section, a.video)
script = json.loads(P["script"].read_text(encoding="utf-8"))
parts = [p.strip() for u in script["units"] for p in u["en"].split("|")]
joined = " ".join(join_parts(split_parts(u["en"])) for u in script["units"])
src = " ".join(script["source_text"].split())

if joined == src:
    print(f"OK: {len(script['units'])} units / {len(parts)} subtitle lines match the source text exactly.")
else:
    for i, (a, b) in enumerate(zip(joined, src)):
        if a != b:
            print(f"MISMATCH at char {i}:\n  subs:   ...{joined[max(0, i - 40):i + 40]}\n  source: ...{src[max(0, i - 40):i + 40]}")
            break
    else:
        print(f"MISMATCH: length differs ({len(joined)} vs {len(src)})")
    sys.exit(1)

long = [p for p in parts if len(p) > MAX_PART]
for p in long:
    print(f"TOO LONG ({len(p)} > {MAX_PART}): {p}")
for i, u in enumerate(script["units"]):
    if u["en"].count("|") != u["zh"].count("|"):
        print(f"unit {i}: en/zh have a different number of '|' splits")
        long.append(u)
if long:
    sys.exit(1)

tl = P["timeline"]
if tl.exists():
    t = json.loads(tl.read_text(encoding="utf-8"))
    if [u["en"] for u in t["units"]] != [join_parts(split_parts(u["en"])) for u in script["units"]]:
        sys.exit(f"{tl.name} is stale: re-run python tts.py" + (f" --section {P['id']}" if P["id"] != "intro" else ""))
    print(f"OK: {tl.name} is in sync with the script.")
