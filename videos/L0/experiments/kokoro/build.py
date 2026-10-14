"""Kokoro re-voice of a section (test): local Kokoro TTS (af_bella) instead of edge-tts, everything under kokoro/.

  python videos/L0/experiments/kokoro/build.py --section closing --tag v2                    # all steps
  python videos/L0/experiments/kokoro/build.py --section closing --tag v2 --step tts         # tts | mix | page | check | preview | render
  python videos/L0/experiments/kokoro/build.py --section closing --tag v2 --step preview --at 5,20,33.5

Inputs are L0's source/scripts/<section>.json, source/slides/<section>.html and build/audio/sfx_<section>.wav (all untouched).
Outputs: kokoro/audio/<id>.wav + <id>_mix.wav, kokoro/audio/units/<id>/, kokoro/timelines/<id>.json,
kokoro/slides/<id>.html + timeline_<id>.js, kokoro/preview/, kokoro/out/<id>.mp4  (id = <section>_<tag>).
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from pipeline import kpaths  # noqa: E402  (also puts the project root on sys.path)
from pipeline import mix, page, timeline, video  # noqa: E402

STEPS = ["tts", "mix", "page", "check", "preview", "render"]


def default_preview_times(P):
    import json
    tl = json.loads(P["timeline"].read_text(encoding="utf-8"))
    ts = [s["start"] + 2.0 for s in tl["slides"]] + [s["end"] - 0.5 for s in tl["slides"]]
    ts += [w for u in tl["units"] for w, x in u["words"] if x in ("Knowledge", "every") and u["slide"] == "S3"]
    return sorted({round(t, 2) for t in ts})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", default="closing")
    ap.add_argument("--tag", default="v2")
    ap.add_argument("--step", choices=STEPS + ["all"], default="all")
    ap.add_argument("--at", help="preview: comma-separated seconds")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    P = kpaths(a.section, a.tag)
    for step in STEPS if a.step == "all" else [a.step]:
        print(f"== {step}")
        if step == "tts":
            timeline.build(P)
        elif step == "mix":
            mix.build(P)
        elif step == "page":
            page.build(P)
        elif step == "check":
            video.check(P)
        elif step == "preview":
            video.preview(P, [float(x) for x in a.at.split(",")] if a.at else default_preview_times(P))
        elif step == "render":
            video.full(P, a.workers)


if __name__ == "__main__":
    main()
