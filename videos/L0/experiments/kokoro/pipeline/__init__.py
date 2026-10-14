"""Kokoro (local TTS) test pipeline: voice -> timeline -> mix -> page -> video, all outputs under kokoro/."""
import pathlib
import sys

KROOT = pathlib.Path(__file__).resolve().parents[1]   # kokoro/ (videos/L0/experiments/kokoro)
ROOT = next(d for d in KROOT.parents if (d / "sections.py").exists())   # project root (tts.py, render.py, engine/ ...)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VIDEO = "L0"


def kpaths(section, tag):
    """Same keys as sections.paths(), pointing at kokoro/ for <section>_<tag>; the script stays the original one."""
    from sections import paths
    src = paths(section, VIDEO)
    sid = f"{section}_{tag}"
    return {
        "id": sid,
        "section": section,
        "script": src["script"],
        "src_html": src["html"],
        "sfx": src["sfx"],
        "timeline": KROOT / "timelines" / f"{sid}.json",
        "timeline_js": KROOT / "slides" / f"timeline_{sid}.js",
        "html": KROOT / "slides" / f"{sid}.html",
        "wav": KROOT / "audio" / f"{sid}.wav",
        "mix": KROOT / "audio" / f"{sid}_mix.wav",
        "mp4": KROOT / "out" / f"{sid}.mp4",
        "units": KROOT / "audio" / "units" / sid,
        "preview": KROOT / "preview",
        "seg": KROOT / "out" / "_seg",
    }
