"""Join finished sections into one video, in story order.

  python concat.py            -> videos/L0/output/full.mp4 from every output/<id>.mp4 in video.json's order
  python concat.py --check    -> only list sections and total duration
  python concat.py --skip ch3 -> leave sections out (comma-separated ids)
  python concat.py --video L1 -> another video under videos/

All sections are rendered with identical encoder settings, so streams are copied (no re-encode).
"""
import argparse
import re
import subprocess
import sys

import imageio_ffmpeg

from sections import DEFAULT_VIDEO, limit, order, paths

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def duration(mp4):
    out = subprocess.run([FFMPEG, "-hide_banner", "-i", str(mp4)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def main(check_only, skip=(), video=DEFAULT_VIDEO):
    parts, total = [], 0.0
    for sid in order(video):
        if sid in skip:
            print(f"  {sid:8s} (skipped)")
            continue
        mp4 = paths(sid, video)["mp4"]
        if not mp4.exists():
            print(f"  {sid:8s} (missing)")
            continue
        d = duration(mp4)
        total += d
        parts.append(mp4)
        print(f"  {sid:8s} {d:6.1f}s")
    cap = limit(video)
    print(f"  total    {total:6.1f}s = {int(total // 60)}:{total % 60:04.1f}  (limit {cap // 60}:{cap % 60:02d})")
    if total > cap:
        print(f"WARNING: over {cap // 60}:{cap % 60:02d}")
    if check_only or not parts:
        return
    out = paths(None, video)["output"]
    lst = out / "_full_list.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    dst = out / "full.mp4"
    r = subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", "-movflags", "+faststart", str(dst)])
    lst.unlink(missing_ok=True)
    if r.returncode:
        sys.exit("concat failed")
    print(f"-> {dst}  ({duration(dst):.1f}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=DEFAULT_VIDEO, help=f"video id under videos/ (default {DEFAULT_VIDEO})")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--skip", default="", help="comma-separated section ids to leave out, e.g. ch3")
    a = ap.parse_args()
    main(a.check, {x.strip() for x in a.skip.split(",") if x.strip()}, a.video)
