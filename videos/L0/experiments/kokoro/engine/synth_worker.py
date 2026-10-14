"""Kokoro synthesis worker -- runs inside the shared venv (C:\\Users\\zengyi4\\tts-tools\\kokoro\\.venv).

  <venv python> synth_worker.py job.json

job.json: {"model", "voices", "voice", "speed", "lang", "lexicon": [[from_ph, to_ph], ...],
           "items": [{"text", "wav", "json"}, ...]}
The model is loaded once for all items. For every item it writes a 24 kHz 16-bit WAV and a JSON with
the phoneme string, per-phoneme timings (the v1.0 model reports durations) and every word's own
phonemes, so the caller can place words in time.
"""
import json
import re
import sys
from pathlib import Path

import onnxruntime as ort
ort.set_default_logger_severity(3)
import soundfile as sf
from kokoro_onnx import Kokoro

WORD = re.compile(r"[\w'’]+(?:-[\w'’]+)*|\+")


def main(job_path):
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    engine = Kokoro(job["model"], job["voices"])
    lang = job.get("lang", "en-us")
    for it in job["items"]:
        ph = engine.tokenizer.phonemize(it["text"], lang)
        for a, b in job.get("lexicon", []):
            ph = ph.replace(a, b)
        audio, sr, timings = engine.create_timed(ph, voice=job["voice"], speed=job["speed"], lang=lang, is_phonemes=True)
        Path(it["wav"]).parent.mkdir(parents=True, exist_ok=True)
        sf.write(it["wav"], audio, sr, subtype="PCM_16")
        words = [[m.group(), m.start(), engine.tokenizer.phonemize(m.group(), lang)] for m in WORD.finditer(it["text"])]
        Path(it["json"]).write_text(json.dumps({
            "phonemes": ph,
            "timings": [[t.phoneme, round(t.start, 4), round(t.end, 4)] for t in timings],
            "words": words,
            "seconds": round(len(audio) / sr, 4),
        }, ensure_ascii=False), encoding="utf-8")
        print(f"{len(audio) / sr:5.2f}s  {it['text']}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
