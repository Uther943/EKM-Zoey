"""Kokoro voice: per-line synthesis through the shared install, cached, with word times from phoneme timings."""
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

from . import KROOT

KOKORO_HOME = r"C:\Users\zengyi4\tts-tools\kokoro"
PYTHON = KOKORO_HOME + r"\.venv\Scripts\python.exe"
MODEL = KOKORO_HOME + r"\models\kokoro-v1.0.fp16.onnx"
VOICES = KOKORO_HOME + r"\models\voices-v1.0.bin"
WORKER = KROOT / "engine" / "synth_worker.py"
CACHE = KROOT / "cache"

VOICE = "af_bella"   # confident, workplace-presenter female voice
SPEED = 0.95
LANG = "en-us"
# phoneme overrides [from, to]; espeak already says Lenovo as lɛnˈoʊvoʊ, so nothing is needed yet
LEXICON = []
STRESS = "ˈˌ"
SKIP = set(" ,.;:!?—–-\"'“”()")


def cache_key(text):
    model = MODEL.rsplit("\\", 1)[-1]
    return hashlib.sha1(f"kokoro|{model}|{VOICE}|{SPEED}|{LANG}|{json.dumps(LEXICON)}|{text}".encode("utf-8")).hexdigest()[:16]


def synth_all(texts, out_wavs):
    """Synthesize every text to its WAV (cache first; one worker run for all misses). Returns the timing JSON per text."""
    CACHE.mkdir(parents=True, exist_ok=True)
    keys = [CACHE / cache_key(t) for t in texts]
    todo = [(t, k) for t, k in zip(texts, keys) if not (k.with_suffix(".wav").exists() and k.with_suffix(".json").exists())]
    if todo:
        job = {"model": MODEL, "voices": VOICES, "voice": VOICE, "speed": SPEED, "lang": LANG, "lexicon": LEXICON,
               "items": [{"text": t, "wav": str(k.with_suffix(".wav")), "json": str(k.with_suffix(".json"))} for t, k in todo]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(job, f, ensure_ascii=False)
        try:
            subprocess.run([PYTHON, str(WORKER), f.name], check=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        finally:
            os.unlink(f.name)
    out = []
    for k, wav in zip(keys, out_wavs):
        wav.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(k.with_suffix(".wav"), wav)
        out.append(json.loads(k.with_suffix(".json").read_text(encoding="utf-8")))
    return out


def word_times(info):
    """[(seconds, char_pos, word)] like tts.synth(): each word's own phonemes are matched against the spoken
    phoneme stream (stress marks, spaces and punctuation ignored); a word starts at its first matched phoneme."""
    stream = [(p, s) for p, s, _ in info["timings"] if p not in STRESS and p not in SKIP]
    seq_b = "".join(p for p, _ in stream)
    seq_a, owner = "", []
    for wi, (_, _, ph) in enumerate(info["words"]):
        for c in ph:
            if c not in STRESS and c not in SKIP:
                seq_a += c
                owner.append(wi)
    pos_map = {}
    for blk in difflib.SequenceMatcher(None, seq_a, seq_b, autojunk=False).get_matching_blocks():
        for j in range(blk.size):
            pos_map[blk.a + j] = blk.b + j
    hits = []
    for wi, (word, _, _) in enumerate(info["words"]):
        idx = [i for i, o in enumerate(owner) if o == wi]
        hit = next((pos_map[i] for i in idx if i in pos_map), None)
        hits.append(None if hit is None else stream[hit][1])
        if hit is None and len(word) > 1:   # "a" alone is ɐ but ə in context; that one is expected
            print(f"  warning: no phoneme match for '{word}', placed between its neighbours")
    out, last = [], 0.0
    for wi, (word, cpos, _) in enumerate(info["words"]):
        t = hits[wi]
        if t is None:
            nxt = next((h for h in hits[wi + 1:] if h is not None), last)
            t = (last + nxt) / 2
        t = max(t, last)
        out.append((round(t, 3), cpos, word))
        last = t
    return out
