"""File locations per video and section.

The project holds several videos (L0, L1, ...). Each lives in videos/<video>/:
  source/   hand-written material: scripts/<id>.json, slides/<id>.html
  build/    generated, can be rebuilt: timelines/, audio/, bgm/, preview/, _seg/
  output/   section MP4s and full.mp4 (trials/ for one-off experiments)
  video.json  {"order": [...]}: the section ids that make up the film, in story order

Shared by every video: the pipeline code (root), engine/ (slide engine + logo), library/ (music, transition sound, TTS cache).
Section ids are e.g. intro, ch1..ch4, closing; omit --section for the intro.
"""
import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
ENGINE = ROOT / "engine"
LIBRARY = ROOT / "library"
DEFAULT_VIDEO = "L0"


def video_dir(video=DEFAULT_VIDEO):
    return ROOT / "videos" / (video or DEFAULT_VIDEO)


def order(video=DEFAULT_VIDEO):
    return json.loads((video_dir(video) / "video.json").read_text(encoding="utf-8"))["order"]


def limit(video=DEFAULT_VIDEO):
    """Length cap of the film in seconds: video.json's optional limit_seconds, else 9 minutes."""
    return json.loads((video_dir(video) / "video.json").read_text(encoding="utf-8")).get("limit_seconds", 9 * 60)


def paths(section=None, video=DEFAULT_VIDEO):
    sid = section or "intro"
    V = video_dir(video)
    src, build, out = V / "source", V / "build", V / "output"
    return {
        "id": sid,
        "video": video or DEFAULT_VIDEO,
        "script": src / "scripts" / f"{sid}.json",
        "html": src / "slides" / f"{sid}.html",
        "timeline": build / "timelines" / f"{sid}.json",
        "timeline_js": build / "timelines" / f"timeline_{sid}.js",
        "units": build / "audio" / "units" / sid,
        "wav": build / "audio" / f"{sid}.wav",
        "sfx": build / "audio" / f"sfx_{sid}.wav",
        "mix": build / "audio" / f"{sid}_mix.wav",
        "mp4": out / f"{sid}.mp4",
        # per-video folders
        "bgm": build / "bgm",
        "preview": build / "preview",
        "seg": build / "_seg",
        "output": out,
        "trials": out / "trials",
    }


def add_section_arg(ap: argparse.ArgumentParser):
    ap.add_argument("--video", default=DEFAULT_VIDEO, help=f"video id under videos/ (default {DEFAULT_VIDEO})")
    ap.add_argument("--section", help="section id (e.g. ch1..ch4, closing); omit for the intro")
