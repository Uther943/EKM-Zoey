"""Assemble the Kokoro lines into one narration track + timeline, with the same pacing rules as tts.py."""
import json
import wave

import numpy as np

from tts import PACING, SR, TAIL, join_parts, part_times, read_pcm, silence, split_parts, trim

from .voice import synth_all, word_times

SPEECH_RMS_DB = -20.0   # match the edge-tts narration level (audio/<section>.wav speech RMS is about -20 dBFS)


def level_match(pcm):
    """Scale the narration so its speech RMS (10 ms frames above -40 dBFS) hits SPEECH_RMS_DB."""
    x = np.frombuffer(bytes(pcm), np.int16).astype(np.float64) / 32768
    fr = x[: len(x) // 240 * 240].reshape(-1, 240)
    r = np.sqrt((fr ** 2).mean(axis=1))
    rms = np.sqrt((r[r > 0.01] ** 2).mean())
    g = 10 ** (SPEECH_RMS_DB / 20) / rms
    g = min(g, 0.97 / np.abs(x).max())
    print(f"level: {20 * np.log10(g):+.1f} dB -> speech RMS {20 * np.log10(rms * g):.1f} dBFS, peak {20 * np.log10(np.abs(x).max() * g):.1f} dBFS")
    return (np.clip(x * g, -1, 1) * 32767).astype(np.int16).tobytes()


def build(P):
    script = json.loads(P["script"].read_text(encoding="utf-8"))
    pace = dict(PACING)
    pace["lead"] = script.get("lead_slide", pace["lead"])
    spoken_all = [join_parts(split_parts(u["en"])) for u in script["units"]]
    wavs = [P["units"] / f"{i:02d}.wav" for i in range(len(spoken_all))]
    infos = synth_all(spoken_all, wavs)

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
        spoken = spoken_all[i]
        with wave.open(str(wavs[i]), "rb") as w:
            if w.getframerate() != SR or w.getnchannels() != 1:
                raise SystemExit(f"{wavs[i]}: expected {SR} Hz mono")
        clip, cut = trim(read_pcm(str(wavs[i]))) if pace["trim"] else (read_pcm(str(wavs[i])), 0.0)
        words = [(max(0.0, s - cut), k, w) for s, k, w in word_times(infos[i])]
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

    P["wav"].parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(P["wav"]), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(level_match(pcm))

    timeline = {"section": P["id"], "duration": round(t, 3),
                "slides": [dict(id=s["id"], title=s["title"], **{k: round(v, 3) for k, v in slides[s["id"]].items()})
                           for s in script["slides"]],
                "units": units, "subs": subs}
    for path in (P["timeline"], P["timeline_js"]):
        path.parent.mkdir(parents=True, exist_ok=True)
    P["timeline"].write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    P["timeline_js"].write_text("window.TIMELINE = " + json.dumps(timeline, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"total {t:.2f}s -> {P['wav']}")
    return timeline
