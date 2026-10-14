"""Mix the Kokoro narration with the section's existing transition sfx (audio/sfx_<section>.wav) -> 48 kHz stereo."""
import wave

import numpy as np
from scipy.signal import resample_poly

SR = 48000


def _read(path):
    with wave.open(str(path), "rb") as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x.reshape(-1, ch).T, sr


def build(P):
    voice, vsr = _read(P["wav"])
    voice = resample_poly(voice[0], SR, vsr)
    mix = np.stack([voice, voice])
    if P["sfx"].exists():
        sfx, ssr = _read(P["sfx"])
        if ssr != SR:
            raise SystemExit(f"{P['sfx']} is {ssr} Hz")
        n = min(mix.shape[1], sfx.shape[1])
        mix[:, :n] += sfx[:, :n]
    else:
        print(f"no {P['sfx'].name}: narration only (run python sfx.py --section {P['section']})")
    mix = np.clip(mix, -1, 1)
    with wave.open(str(P["mix"]), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix.T * 32767).astype(np.int16).tobytes())
    print(f"{P['mix']}  ({mix.shape[1] / SR:.2f}s, peak {20 * np.log10(np.abs(mix).max() + 1e-12):.1f} dBFS)")
