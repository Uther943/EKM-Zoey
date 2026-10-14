"""Audition chapter-card transition sounds without touching the film.

  python library/transition/transition.py [--bgm] [--video L0] soft_v1 [soft_v2 ...]

Each name is an entry in presets.json next to this file. Writes only into library/transition/preview/:
  current.wav       copy of the video's current build/audio/sfx_ch2.wav (A/B reference, written once)
  <name>.wav        the candidate alone
  <name>_ch2.wav    candidate + first ~10 s of ch2 narration (build/audio/ch2.wav, read only)
  <name>_ch2_bgm.wav  with --bgm: also the film's music (build/bgm/full_bgm_mix.wav, read only)
Narration and music are read from videos/<video>/ (--video, default L0).
Self-contained on purpose: does not import sfx.py and never writes outside preview/.
"""
import json
import pathlib
import shutil
import sys
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
OUT = HERE / "preview"
SR = 48000
PREVIEW_SECS = 10.0

rng = np.random.default_rng(7)


def filt(x, kind, f):
    return sosfilt(butter(4, f, kind, fs=SR, output="sos"), x)


def stereo(m, pan=0.0):
    return np.stack([m * np.sqrt(0.5 * (1 - pan)), m * np.sqrt(0.5 * (1 + pan))])


def reverb(x, secs, wet, tail):
    n = int(secs * SR)
    it = np.arange(n) / SR
    ir = np.stack([filt(rng.standard_normal(n), "lowpass", 5000) * np.exp(-it / tail) for _ in range(2)])
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
    y = np.stack([fftconvolve(x[c], ir[c])[: x.shape[1]] for c in range(2)])
    return x + y * wet


def onset(t, t0, attack, decay):
    """Linear attack from t0, then exponential decay."""
    tt = t - t0
    return np.where(tt >= 0, np.clip(tt / attack, 0, 1) * np.exp(-np.clip(tt, 0, None) / decay), 0.0)


def air(t, p, hit):
    """Band-limited noise swelling up to the hit, then released smoothly (no hard gate).
    Optional "bright" band: the noise crossfades from "band" to "bright" as it rises (filter-opening sweep)."""
    rise = np.clip(t / hit, 0, 1)
    release = np.exp(-np.clip(t - hit, 0, None) / p["release"])
    band = lambda lo, hi: filt(filt(rng.standard_normal(len(t)), "highpass", lo), "lowpass", hi)
    n = band(*p["band"])
    if p.get("bright"):
        n = n * (1 - rise) + band(*p["bright"]) * rise
    m = n * rise ** p.get("curve", 2) * release * p["level"]
    return np.stack([m, np.roll(m, int(0.0006 * SR))])


def pad(t, p, length):
    e = np.clip(t / p["attack"], 0, 1) ** 2 * np.clip((length - t) / p["fade_out"], 0, 1)
    out = np.zeros((2, len(t)))
    for i, f in enumerate(p["freqs"]):
        for ch, det in ((0, -0.8), (1, 0.8)):
            out[ch] += np.sin(2 * np.pi * (f + det) * t + i)
    return out * e * p["level"] / max(1, len(p["freqs"]))


def chime(t, p, hit):
    """Notes from hit, staggered. "partials": [[multiple, amp, decay], ...] (default: fundamental + weak 2x);
    "spread": alternating L/R pan."""
    partials = p.get("partials") or [[1, 1, p["decay"]], [2, p.get("partial2", 0), 1 / (1 / 0.3 + 1 / p["decay"])]]
    spread = p.get("spread", 0.2)
    out = np.zeros((2, len(t)))
    for i, f in enumerate(p["freqs"]):
        t0 = hit + i * p["stagger"]
        tt = np.clip(t - t0, 0, None)
        m = sum(a * np.sin(2 * np.pi * f * mul * tt) * np.exp(-tt / dec) for mul, a, dec in partials)
        m = m * (t >= t0) * np.clip(tt / p["attack"], 0, 1)
        out += stereo(m * p["level"], -spread if i % 2 == 0 else spread)
    return out


def reverse_swell(t, p, hit, chime_p, rv):
    """The chime's reverb tail played backwards, ending exactly at the hit (classic 'reverse cymbal' lead-in)."""
    n = int(2.5 * SR)
    tt = np.arange(n) / SR
    wet = reverb(chime(tt, chime_p, 0.0), rv["secs"], 1.0, rv["tail"])[:, : int(p["len"] * SR)][:, ::-1]
    wet = wet * np.linspace(0, 1, wet.shape[1]) ** 2 * np.clip((wet.shape[1] - np.arange(wet.shape[1])) / (0.02 * SR), 0, 1)
    wet = wet / np.abs(wet).max() * p["level"]
    out = np.zeros((2, len(t)))
    a = int(hit * SR) - wet.shape[1]
    out[:, max(a, 0): int(hit * SR)] = wet[:, max(-a, 0):]
    return out


def epiano(t, p):
    """Soft Rhodes-like notes (1:1 FM with a gently decaying index), one after another starting at "start".
    Small index = round, mellow tone; soft attack, two-stage decay so the tail lingers briefly then fades."""
    out = np.zeros((2, len(t)))
    for i, f in enumerate(p["notes"]):
        t0 = p["start"] + i * p["gap"]
        tt = np.clip(t - t0, 0, None)
        idx = p["index"] * np.exp(-tt / p["index_decay"])
        env = (np.clip(tt / p["attack"], 0, 1) ** 2
               * (0.6 * np.exp(-tt / p["decay"]) + 0.4 * np.exp(-tt / p["tail"]))) * (t >= t0)
        pan = p.get("spread", 0.0) * (-1 if i % 2 == 0 else 1)
        for ch, det in ((0, -p.get("detune", 0.0)), (1, p.get("detune", 0.0))):
            ph = 2 * np.pi * (f + det) * tt
            out[ch] += np.sin(ph + idx * np.sin(ph)) * env * p["level"] * np.sqrt(0.5 * (1 + (pan if ch else -pan)))
    return out


def thump(t, p, hit):
    tt = np.clip(t - hit, 0, None)
    f = p["to"] + (p["from"] - p["to"]) * np.exp(-tt / 0.08)
    m = np.sin(2 * np.pi * np.cumsum(f) / SR) * onset(t, hit, p["attack"], p["decay"]) * p["level"]
    if p.get("body"):  # short low-passed noise burst: makes the hit tight instead of boomy
        b = p["body"]
        m = m + filt(rng.standard_normal(len(t)), "lowpass", b["lowpass"]) * onset(t, hit, 0.002, b["decay"]) * b["level"]
    return stereo(m)


def synth(p):
    length, hit = p["length"], p["hit"]
    t = np.arange(int(length * SR)) / SR
    x = np.zeros((2, len(t)))
    if p.get("air"):
        x += air(t, p["air"], hit)
    if p.get("pad"):
        x += pad(t, p["pad"], length)
    if p.get("chime") and p["chime"]["freqs"]:
        x += chime(t, p["chime"], hit)
    if p.get("thump"):
        x += thump(t, p["thump"], hit)
    if p.get("epiano"):
        x += epiano(t, p["epiano"])
    r = p["reverb"]
    if p.get("reverse") and p.get("chime"):
        x += reverse_swell(t, p["reverse"], hit, p["chime"], r)
    x = reverb(x, r["secs"], r["wet"], r["tail"])
    if p.get("lowpass"):
        x = np.stack([filt(c, "lowpass", p["lowpass"]) for c in x])
    if p.get("saturate"):
        x = np.tanh(x * p["saturate"])
    x *= np.clip((length - t) / 0.5, 0, 1)
    return x * 10 ** (p["peak_db"] / 20) / np.abs(x).max()


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    x = x.reshape(-1, ch).T
    if sr != SR:
        x = np.stack([resample_poly(c, SR, sr) for c in x])
    return x if ch == 2 else np.vstack([x, x])


def write_wav(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1).T * 32767).astype(np.int16).tobytes())
    print(f"  {path.relative_to(ROOT)}  {x.shape[1] / SR:.2f}s")


def stats(name, x):
    spec = np.abs(np.fft.rfft(x.mean(axis=0))) ** 2
    f = np.fft.rfftfreq(x.shape[1], 1 / SR)
    hi = spec[f > 4000].sum() / spec.sum() * 100
    print(f"  {name:<12} peak {20 * np.log10(np.abs(x).max()):6.1f} dBFS   energy > 4 kHz {hi:5.2f}%")


def film_music(n, video):
    """The film's own (already ducked) music under the first n samples of ch2: full_bgm_mix.wav minus build/audio/ch2_mix.wav.
    Read only; the limiter in bgm.py did not touch this stretch (residual is uncorrelated with the voice at gain 1.0)."""
    from concat import duration
    from sections import order, paths
    ids = order(video)
    t0 = sum(duration(paths(s, video)["mp4"]) for s in ids[: ids.index("ch2")])
    a = int(round(t0 * SR))
    P = paths("ch2", video)
    full = read_wav(P["bgm"] / "full_bgm_mix.wav")[:, a: a + n]
    return full, full - read_wav(P["mix"])[:, :n]


def main(names, bgm=False, video=None):
    from sections import paths
    P = paths("ch2", video)
    presets = json.loads((HERE / "presets.json").read_text(encoding="utf-8"))
    missing = [n for n in names if n not in presets]
    if not names or missing:
        raise SystemExit(f"unknown preset(s) {missing}; available: {', '.join(presets)}")
    OUT.mkdir(exist_ok=True)
    cur = OUT / "current.wav"
    if not cur.exists():
        shutil.copyfile(P["sfx"], cur)
        print(f"  {cur.relative_to(ROOT)}  (copy of {P['sfx'].relative_to(ROOT)})")
    voice = read_wav(P["wav"])[:, : int(PREVIEW_SECS * SR)]
    if bgm:
        film, music = film_music(voice.shape[1], video)
        write_wav(OUT / "current_ch2_bgm.wav", film)          # exactly what the film plays now
    print("stats:")
    stats("current", read_wav(cur))
    for n in names:
        sfx = synth(presets[n])
        stats(n, sfx)
        write_wav(OUT / f"{n}.wav", sfx)
        mix = voice.copy()
        mix[:, : sfx.shape[1]] += sfx
        write_wav(OUT / f"{n}_ch2.wav", mix)
        if bgm:
            write_wav(OUT / f"{n}_ch2_bgm.wav", mix + music)


if __name__ == "__main__":
    args = sys.argv[1:]
    video = None
    if "--video" in args:
        i = args.index("--video")
        video = args[i + 1]
        del args[i:i + 2]
    main([a for a in args if a != "--bgm"], bgm="--bgm" in args, video=video)
