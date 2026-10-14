"""Synthesize the opening sound effect and mix it under the narration.

Layers (timed to the title card): airy riser 0-1.0s -> deep impact + sub drop at 1.0s
(title appears) -> bell shimmer with a ping at 1.4s (red rule) -> low pad, all with a
synthetic reverb tail, faded out before the first narration line.

  python sfx.py                  -> intro opening: build/audio/sfx_intro.wav + build/audio/intro_mix.wav (48 kHz stereo)
  python sfx.py --section ch1    -> chapter-card transition (TR_FILE, chosen in library/transition/): build/audio/sfx_ch1.wav + ch1_mix.wav

A script may also list point cues, e.g. "sfx": [{"kind": "ding", "at": "u0@across+2.5", "pitch": 1568}];
"at" uses the same unit / word grammar as the slides' data-at, resolved against the section's timeline.
"""
import argparse
import json
import re
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt

from sections import LIBRARY, add_section_arg, paths

SR = 48000
LEN = 4.8          # sfx length; narration starts at 5.6s
HIT = 1.0          # impact time = title fades in
PEAK_DB = -6.0     # sfx peak level
TR_FILE = LIBRARY / "transition" / "orig_low_v1.wav"   # chapter card sound (2.6 s, -12 dBFS), see library/transition/
DING_PEAK_DB = -14.0  # point cue when a light dot reaches a node: lighter still
DING_LEN = 1.2

rng = np.random.default_rng(7)
t = np.arange(int(LEN * SR)) / SR


def filt(x, kind, f):
    return sosfilt(butter(4, f, kind, fs=SR, output="sos"), x)


def env_exp(t0, tau):
    e = np.where(t >= t0, np.exp(-(t - t0) / tau), 0.0)
    return e


def stereo(m, pan=0.0):
    return np.stack([m * np.sqrt(0.5 * (1 - pan)), m * np.sqrt(0.5 * (1 + pan))])


def riser():
    p = np.clip(t / HIT, 0, 1)
    gate = (t < HIT) * np.clip((HIT - t) / 0.02, 0, 1)
    n = rng.standard_normal(len(t))
    dark, bright = filt(filt(n, "highpass", 250), "lowpass", 900), filt(n, "highpass", 1500)
    noise = (dark * (1 - p) + bright * p) * p ** 2.2
    f = 180 * (1400 / 180) ** p                      # exponential pitch sweep
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.12 * p ** 3
    m = (noise * 0.5 + tone) * gate
    # sweep from left to right with a small Haas offset for width
    pan = -0.6 + 1.2 * p
    l, r = m * np.sqrt(0.5 * (1 - pan)), m * np.sqrt(0.5 * (1 + pan))
    return np.stack([l, np.roll(r, int(0.0006 * SR))])


def impact():
    tt = np.clip(t - HIT, 0, None)
    f = 38 + 34 * np.exp(-tt / 0.12)                 # 72 Hz -> 38 Hz drop
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(HIT, 0.6)
    body = filt(rng.standard_normal(len(t)), "lowpass", 1400) * env_exp(HIT, 0.09) * 0.5
    click = filt(rng.standard_normal(len(t)), "highpass", 3500) * env_exp(HIT, 0.012) * 0.35
    return stereo(np.tanh(sub * 1.6) * 0.9) + stereo(body) + stereo(click)


def bell(f0, t0, tau, amp, pan):
    tt = np.clip(t - t0, 0, None)
    out = np.zeros((2, len(t)))
    for k, (mul, a) in enumerate([(1, 1.0), (2.0, 0.35), (3.01, 0.15)]):
        for ch, det in ((0, -1.5), (1, 1.5)):
            ph = 2 * np.pi * (f0 * mul + det) * tt + 0.002 * np.sin(2 * np.pi * 5 * tt)
            out[ch] += np.sin(ph) * a
    attack = np.clip(tt / 0.004, 0, 1)
    out *= env_exp(t0, tau) * attack * amp
    out[0] *= np.sqrt(0.5 * (1 - pan)); out[1] *= np.sqrt(0.5 * (1 + pan))
    return out


def shimmer():
    notes = [(880.0, 1.4, -0.3), (1318.5, 1.1, 0.3), (1760.0, 0.9, -0.1), (2217.5, 0.7, 0.4)]
    s = sum(bell(f, HIT + 0.02 * i, tau, 0.05, pan) for i, (f, tau, pan) in enumerate(notes))
    s += bell(2637.0, 1.42, 0.8, 0.045, 0.5)        # ping on the red rule
    s += bell(3520.0, 1.62, 0.6, 0.03, -0.5)
    return s


def pad():
    e = np.clip(t / 0.9, 0, 1) ** 2 * np.clip((4.4 - t) / 1.6, 0, 1)
    m = sum(np.sin(2 * np.pi * f * t + i) * a for i, (f, a) in enumerate([(55, 1.0), (82.41, 0.7), (110, 0.5), (164.8, 0.25)]))
    m = filt(m, "lowpass", 900) * e * 0.10
    return np.stack([m, np.roll(m, int(0.004 * SR))])


def reverb(x, secs=2.4, wet=0.28):
    n = int(secs * SR)
    it = np.arange(n) / SR
    ir = np.stack([filt(rng.standard_normal(n), "lowpass", 6000) * np.exp(-it / 0.55) for _ in range(2)])
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
    y = np.stack([fftconvolve(x[c], ir[c])[: x.shape[1]] for c in range(2)])
    return x + y * wet


def opening():
    dry = riser() + impact() + pad()
    sfx = reverb(dry, wet=0.22) + reverb(shimmer(), wet=0.45)
    sfx *= np.clip((LEN - t) / 0.8, 0, 1)            # clean fade before narration
    sfx = np.tanh(sfx * 1.2)
    return sfx * 10 ** (PEAK_DB / 20) / np.abs(sfx).max()


def transition():
    """Chapter card sound, auditioned and chosen in library/transition/ (48 kHz stereo wav, used as is)."""
    with wave.open(str(TR_FILE), "rb") as w:
        if (w.getframerate(), w.getnchannels()) != (SR, 2):
            raise SystemExit(f"{TR_FILE} must be {SR} Hz stereo")
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x.reshape(-1, 2).T


def ding(f0, pan=0.0):
    """Crisp short bell: fast attack, ~0.3 s decay, a few bright partials and a light reverb."""
    n = int(DING_LEN * SR)
    tt = np.arange(n) / SR
    out = np.zeros((2, n))
    for mul, a, tau in ((1.0, 1.0, 0.30), (2.76, 0.32, 0.12), (5.40, 0.12, 0.05)):
        for ch, det in ((0, -1.2), (1, 1.2)):
            out[ch] += np.sin(2 * np.pi * (f0 * mul + det) * tt) * a * np.exp(-tt / tau)
    out *= np.clip(tt / 0.003, 0, 1)
    click = filt(rng.standard_normal(n), "highpass", 6000)[:n] * np.exp(-tt / 0.004) * 0.15
    out += np.stack([click, click])
    out[0] *= np.sqrt(0.5 * (1 - pan)); out[1] *= np.sqrt(0.5 * (1 + pan))
    k = int(2.4 * SR)
    wet = reverb(np.pad(out, ((0, 0), (0, k))), secs=1.2, wet=0.25)
    wet *= np.clip((wet.shape[1] / SR - np.arange(wet.shape[1]) / SR) / 0.3, 0, 1)
    return wet * 10 ** (DING_PEAK_DB / 20) / np.abs(wet).max()


def resolve_at(spec, tl):
    """Same grammar as the pages' data-at for unit cues: u<n>[@word][f<frac>][+/-offsets]."""
    m = re.fullmatch(r"u(\d+)(?:@([A-Za-z'-]+))?(?:f([\d.]+))?((?:[+-][\d.]+)*)", spec)
    if not m:
        raise SystemExit(f"bad sfx at: {spec}")
    u = tl["units"][int(m[1])]
    if m[2]:
        t0 = next((a for a, w in u["words"] if w.lower() == m[2].lower()), None)
        if t0 is None:
            raise SystemExit(f'word "{m[2]}" not spoken in {spec}')
    else:
        t0 = u["start"] + (u["end"] - u["start"]) * float(m[3] or 0)
    return t0 + sum(float(x) for x in re.findall(r"[+-][\d.]+", m[4]))


def main(section, video):
    P = paths(section, video)
    sfx = opening() if P["id"] == "intro" else transition()
    script = json.loads(P["script"].read_text(encoding="utf-8"))
    tl = json.loads(P["timeline"].read_text(encoding="utf-8"))
    cues = [(resolve_at(c["at"], tl), ding(c.get("pitch", 1760), c.get("pan", 0.0))) for c in script.get("sfx", []) if c["kind"] == "ding"]
    with wave.open(str(P["wav"]), "rb") as w:
        src_sr = w.getframerate()
        voice = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    voice = resample_poly(voice, SR, src_sr)
    mix = np.stack([voice, voice])
    mix[:, : sfx.shape[1]] += sfx
    for at, cue in cues:
        a = int(round(at * SR)); b = min(mix.shape[1], a + cue.shape[1])
        mix[:, a:b] += cue[:, : b - a]
        print(f"ding at {at:.2f}s")
    mix = np.clip(mix, -1, 1)

    def write(path, x):
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((x.T * 32767).astype(np.int16).tobytes())
        print(path)

    write(P["sfx"], sfx)
    write(P["mix"], mix)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    add_section_arg(ap)
    a = ap.parse_args()
    main(a.section, a.video)
