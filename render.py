"""Render a section's slide page to MP4 frame by frame.

  python render.py                                  -> L0 intro: videos/L0/source/slides/intro.html -> output/intro.mp4
  python render.py --section ch1 --workers 8        -> source/slides/ch1.html -> output/ch1.mp4 (parallel)
  python render.py --section ch1 --preview 3,12.5   -> build/preview/<id>_<t>.png
  (all of them take --video for another video; default L0)
  python render.py --section ch1 --remux            -> only replace the audio track
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

from sections import add_section_arg, paths

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
VIDEO_ARGS = ["-vf", "scale=in_range=pc:out_range=tv,format=yuv420p",
              "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-color_range", "tv"]


def open_page(p, html):
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    page.goto(pathlib.Path(html).as_uri())
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(300)
    return browser, page


def preview(P, times):
    out = P["preview"]
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser, page = open_page(p, P["html"])
        for t in times:
            page.evaluate(f"renderAt({t})")
            path = out / f"{P['id']}_{t:06.2f}.png"
            page.screenshot(path=str(path))
            print(path)
        browser.close()


def audio_track(P):
    """Narration mixed with sfx (sfx.py) if available, else the plain narration."""
    return P["mix"] if P["mix"].exists() else P["wav"]


def remux(P):
    """Swap in the current audio track without re-rendering the frames."""
    dst = P["mp4"]
    tmp = dst.with_suffix(".remux.mp4")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(dst), "-i", str(audio_track(P)),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(dst)
    print(f"remuxed audio -> {dst}")


def render_frames(html, first, last, dst, log=True):
    """Render frames [first, last) into a video-only file."""
    ff = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                           "-c:v", "mjpeg", "-i", "-", *VIDEO_ARGS, str(dst)], stdin=subprocess.PIPE)
    t0 = time.time()
    with sync_playwright() as p:
        browser, page = open_page(p, html)
        for i in range(first, last):
            page.evaluate(f"renderAt({i / FPS})")
            ff.stdin.write(page.screenshot(type="jpeg", quality=95))
            if log and (i - first) % 300 == 0:
                print(f"  frames {first}-{last}: {i - first}/{last - first}  {time.time() - t0:.0f}s", flush=True)
        browser.close()
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {dst}")
    return str(dst)


def render(P, limit=None, workers=1):
    tl = json.loads(P["timeline"].read_text(encoding="utf-8"))
    n = int(round((limit or tl["duration"]) * FPS))
    P["mp4"].parent.mkdir(parents=True, exist_ok=True)
    seg_dir = P["seg"]
    seg_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    bounds = [round(n * k / workers) for k in range(workers + 1)]
    segs = [seg_dir / f"{P['id']}_{k:02d}.mp4" for k in range(workers)]
    if workers == 1:
        render_frames(str(P["html"]), 0, n, segs[0])
    else:
        print(f"{n} frames on {workers} workers")
        with ProcessPoolExecutor(workers) as ex:
            futs = [ex.submit(render_frames, str(P["html"]), bounds[k], bounds[k + 1], segs[k], k == 0)
                    for k in range(workers)]
            for f in futs:
                f.result()
    lst = seg_dir / f"{P['id']}_list.txt"
    lst.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs), encoding="utf-8")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-i", str(audio_track(P)), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(P["mp4"])], check=True)
    for s in segs:
        s.unlink(missing_ok=True)
    lst.unlink(missing_ok=True)
    print(f"done -> {P['mp4']}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    add_section_arg(ap)
    ap.add_argument("--preview", help="comma-separated seconds")
    ap.add_argument("--limit", type=float, help="render only the first N seconds")
    ap.add_argument("--workers", type=int, default=1, help="parallel browser processes")
    ap.add_argument("--remux", action="store_true", help="only replace the audio track of the existing mp4")
    a = ap.parse_args()
    P = paths(a.section, a.video)
    if a.remux:
        remux(P)
    elif a.preview:
        preview(P, [float(x) for x in a.preview.split(",")])
    else:
        render(P, a.limit, a.workers)
