"""Generate narration audio + timeline from a section script.

  python tts.py                  -> L0 intro: videos/L0/source/scripts/intro.json
                                    -> build/timelines/intro.json + timeline_intro.js, build/audio/intro.wav
  python tts.py --section ch1    -> same for ch1;  add --video L1 for another video

One mp3 per unit (edge-tts, with word boundaries), decoded to WAV, concatenated with fixed gaps.
A unit's "en"/"zh" may contain " | " to split one spoken sentence into several subtitle parts;
each part is timed from the word boundaries so the subtitle switches exactly when that phrase is spoken.
Every unit also stores its word times, so slides can cue on a spoken word ("u0@across").
A unit may set "pause_after" (seconds), or "hold": {"after": "<word>", "seconds": n} to keep the slide
on screen until n seconds after that word (e.g. for a longer animation). Units marked "list": true are
enumeration items and follow the previous line with a short gap.
Synthesized clips are cached in library/tts_cache/ (key = voice + rate + text), so unchanged lines are reused
as-is and never re-requested from the service.
"""
import argparse
import asyncio
import hashlib
import json
import shutil
import subprocess
import wave

import edge_tts
import edge_tts.communicate as edge_comm
import imageio_ffmpeg
from aiohttp import WSServerHandshakeError
from edge_tts.constants import TRUSTED_CLIENT_TOKEN
import numpy as np

from sections import LIBRARY, add_section_arg, paths

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SR = 24000
TAIL = 1.5
# every section (the Intro too, since 2026-10-10) uses the same tight pacing:
# clip silence trimmed, title appears together with the content, short gaps between enumeration items.
PACING = dict(gap=0.45, gap_list=0.15, gap_slide=0.8, lead=0.5, trim=True)
TRIM_LEAD, TRIM_TAIL, TRIM_THRESH = 0.05, 0.12, 0.01  # keep 50 ms before / 120 ms after the speech
CACHE = LIBRARY / "tts_cache"   # shared by every video
# since 2026-10-10 the legacy synthesis host answers 403 in many regions (edge-tts issue #490);
# Edge's own Read Aloud now uses api.msedgeservices.com with the same token. Try it first, fall back to the legacy host.
TTS_HOSTS = [
    f"wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}",
    edge_comm.WSS_URL,
]


def cache_key(text, voice, rate):
    return hashlib.sha1(f"{voice}|{rate}|{text}".encode("utf-8")).hexdigest()[:16]


def to_wav(src, dst):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", src,
                    "-ac", "1", "-ar", str(SR), "-sample_fmt", "s16", dst], check=True)


def read_pcm(path):
    with wave.open(path, "rb") as w:
        return w.readframes(w.getnframes())


def silence(sec):
    return bytes(2 * int(round(sec * SR)))


def trim(pcm):
    """Cut edge-tts's built-in silence (~0.2 s before, ~0.9 s after). Returns (pcm, seconds cut at the start)."""
    x = np.frombuffer(pcm, np.int16)
    loud = np.where(np.abs(x.astype(np.int32)) > TRIM_THRESH * 32768)[0]
    if not len(loud):
        return pcm, 0.0
    a = max(0, loud[0] - int(TRIM_LEAD * SR))
    b = min(len(x), loud[-1] + int(TRIM_TAIL * SR))
    return x[a:b].tobytes(), a / SR


def split_parts(s):
    return [p.strip() for p in s.split("|")]


def join_parts(parts):
    """Re-join subtitle parts into the spoken sentence; a part ending in an unspaced dash ("asset—") joins without a space."""
    out = ""
    for p in parts:
        glued = out.endswith("—") and not out.endswith(" —")
        out += p if not out or glued else " " + p
    return out


async def synth(text, voice, rate, out):
    """Save mp3 and return [(seconds, char_pos, word)] for every spoken word (from the cache when possible)."""
    key = CACHE / cache_key(text, voice, rate)
    if key.with_suffix(".mp3").exists() and key.with_suffix(".json").exists():
        shutil.copyfile(key.with_suffix(".mp3"), out)
        words = [tuple(w) for w in json.loads(key.with_suffix(".json").read_text(encoding="utf-8"))]
    else:
        for k, host in enumerate(TTS_HOSTS):
            edge_comm.WSS_URL = host
            words, audio = [], bytearray()
            try:
                async for ch in edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary").stream():
                    if ch["type"] == "audio":
                        audio.extend(ch["data"])
                    elif ch["type"] == "WordBoundary":
                        words.append((ch["offset"] / 1e7, ch["text"]))
                break
            except WSServerHandshakeError as e:
                if e.status != 403 or k == len(TTS_HOSTS) - 1:
                    raise
        with open(out, "wb") as f:
            f.write(audio)
        CACHE.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, key.with_suffix(".mp3"))
        key.with_suffix(".json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    pos, cur = [], 0
    for sec, w in words:
        k = text.find(w, cur)
        if k < 0:
            continue
        pos.append((sec, k, w))
        cur = k + len(w)
    return pos


def part_times(parts, words, start, end):
    """Start time of each subtitle part = time of its first spoken word."""
    full, starts, c = join_parts(parts), [], 0
    for p in parts:
        k = full.find(p, c)
        starts.append(k)
        c = k + len(p)
    times = []
    for k in starts:
        w = next((sec for sec, pos, _ in words if pos >= k), None)
        times.append(start if not times else start + (w if w is not None else 0))
    return [(times[i], times[i + 1] if i + 1 < len(times) else end) for i in range(len(times))]


async def main(section, video):
    P = paths(section, video)
    script = json.loads(P["script"].read_text(encoding="utf-8"))
    sec = P["id"]
    tmp = P["units"]
    tmp.mkdir(parents=True, exist_ok=True)
    pace = dict(PACING)
    pace["lead"] = script.get("lead_slide", pace["lead"])

    pcm = bytearray()
    t = 0.0

    def add(chunk):
        nonlocal t
        pcm.extend(chunk)
        t = len(pcm) / 2 / SR

    add(silence(script["title_card_seconds"]))
    slides = {"S0": {"start": 0.0, "end": t}}
    units, subs = [], []
    prev_slide, last_gap = "S0", pace["gap"]
    for i, u in enumerate(script["units"]):
        if u["slide"] != prev_slide:
            if prev_slide != "S0":
                add(silence(max(0.0, pace["gap_slide"] - last_gap)))
                slides[prev_slide]["end"] = t
            slides[u["slide"]] = {"start": t}
            add(silence(pace["lead"]))
            prev_slide = u["slide"]
        en_parts, zh_parts = split_parts(u["en"]), split_parts(u["zh"])
        if len(en_parts) != len(zh_parts):
            raise SystemExit(f"unit {i}: {len(en_parts)} en parts vs {len(zh_parts)} zh parts")
        spoken = join_parts(en_parts)
        mp3, wav = tmp / f"{i:02d}.mp3", tmp / f"{i:02d}.wav"
        words = await synth(spoken, script["voice"], script["rate"], str(mp3))
        to_wav(str(mp3), str(wav))
        clip, cut = trim(read_pcm(str(wav))) if pace["trim"] else (read_pcm(str(wav)), 0.0)
        words = [(max(0.0, s - cut), k, w) for s, k, w in words]
        start = t
        add(clip)
        end = t
        units.append({"i": i, "slide": u["slide"], "start": round(start, 3), "end": round(end, 3),
                      "en": spoken, "zh": "".join(zh_parts),
                      "words": [[round(start + s, 3), w] for s, _, w in words]})
        for (a, b), en, zh in zip(part_times(en_parts, words, start, end), en_parts, zh_parts):
            subs.append({"i": len(subs), "unit": i, "slide": u["slide"], "start": round(a, 3), "end": round(b, 3),
                         "en": en, "zh": zh})
        nxt = script["units"][i + 1] if i + 1 < len(script["units"]) else None
        last_gap = pace["gap_list"] if nxt and nxt["slide"] == u["slide"] and nxt.get("list") else pace["gap"]
        extra = u.get("pause_after", 0)
        if "hold" in u:  # keep the slide on screen until N s after a spoken word
            wt = next(start + s for s, _, w in words if w.lower() == u["hold"]["after"].lower())
            extra = max(extra, wt + u["hold"]["seconds"] - (end + last_gap))
        add(silence(last_gap + extra))
        last_gap += extra
        print(f"[{i:02d}] {start:6.2f}-{end:6.2f}  {spoken}")
    add(silence(TAIL))
    slides[prev_slide]["end"] = t

    with wave.open(str(P["wav"]), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(pcm))

    timeline = {"section": sec, "duration": round(t, 3),
                "slides": [dict(id=s["id"], title=s["title"], **{k: round(v, 3) for k, v in slides[s["id"]].items()})
                           for s in script["slides"]],
                "units": units, "subs": subs}
    P["timeline"].parent.mkdir(parents=True, exist_ok=True)
    P["timeline"].write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    # also expose to the HTML page without needing a server
    P["timeline_js"].write_text("window.TIMELINE = " + json.dumps(timeline, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"total {t:.2f}s -> {P['wav']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    add_section_arg(ap)
    a = ap.parse_args()
    asyncio.run(main(a.section, a.video))
