"""Synthesize a background music bed for a section and duck it under the narration.

D major, I-V-vi-IV; the tempo is fitted so S1 -> S3 is exactly 12 bars (~100 BPM), so the
section changes and the crash land on downbeats:
  S0  soft pad swell under the chapter-card sfx
  S1  pad + 8th-note pluck arpeggio + soft kick on 1 and 3
  S2  builds: 8th bass pulse (pumped by the kick), claps on 2 and 4, four-on-the-floor, brighter pad, hats later
  S3  riser + crash on the downbeat, fullest bars, final D chord + chime when the last line ends, fade out
The narration envelope drives a sidechain duck (music ~18 dB under speech, ~10 dB under in pauses)
and the music gets a wide dip at 1-4 kHz so it stays out of the voice's clarity range.

All paths below are inside videos/<video>/ (--video, default L0); music source files live in library/music/.

  python bgm.py --section closing
    -> build/bgm/bgm_closing.wav           music stem (not ducked)
    -> build/bgm/closing_bgm_mix.wav       build/audio/closing_mix.wav + ducked music (48 kHz stereo)
    -> output/trials/bac_closing.mp4       video stream copied from output/closing.mp4 with that mix

  python bgm.py --section closing --track "library/music/<file>.mp3" --tag 2
    -> same, but the music is the supplied track re-cut by bars (TRACKS) so its chorus lands on S3;
       outputs bgm2_closing.wav / closing_bgm2_mix.wav / output/trials/bac2_closing.mp4

  python bgm.py --full --tag v2
    -> whole film with the synthesized score (compose_film: A major, 146.7 BPM, IV-V-vi-I like the morrix track,
       a layer added per chapter, breakdowns under the chapter cards, biggest chorus on the closing's final page);
       outputs build/bgm/bgm_full_v2.wav, full_v2_bgm_mix.wav and output/full_v2.mp4

  python bgm.py --full --track "library/music/<file>.mp3" --style remix --tag v3
    -> whole film, original track only (no effects): its bars re-arranged per chapter (remix_track) -> output/full_v3.mp4

  python bgm.py --full --track "library/music/<file>.mp3"
    -> whole film: joins output/<id>.mp4 in video.json order (video copied), lays one music bed under all of it
       (body bars looped, chorus on the closing's final page, a short muffle at every chapter card) over each
       section's build/audio/<id>_mix.wav; outputs build/bgm/bgm_full.wav, full_bgm_mix.wav and output/full.mp4
"""
import argparse
import json
import pathlib
import subprocess
import wave

import imageio_ffmpeg
import numpy as np
from scipy.signal import butter, resample_poly, sosfiltfilt

from sections import add_section_arg, paths
from sfx import SR, filt, reverb

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
GAP_DB = -10.0      # music level vs speech level in the pauses
DUCK_DB = -8.0      # extra cut while speaking -> about -18 dB under the voice
MID_CUT_DB = -4.0   # 1-4 kHz dip on the music
PEAK_LIMIT_DB = -1.0
FADE_OUT = 1.7      # music fades to silence over the last seconds

rng = np.random.default_rng(11)

# chord -> (bass midi, pad/arp midi notes)
CHORDS = {
    "D": (38, [62, 66, 69, 74]),
    "A": (45, [61, 64, 69, 73]),
    "Bm": (47, [62, 66, 71, 74]),
    "G": (43, [62, 67, 71, 74]),
    "Em": (40, [64, 67, 71, 76]),
}
# (bar, chord, length in bars); bars 0-5 = S1, 6-11 = S2, 12-13 = S3, 14 = final chord
PROG = [(0, "D", 1), (1, "A", 1), (2, "Bm", 1), (3, "G", 1), (4, "D", 1), (5, "A", 1),
        (6, "D", 1), (7, "A", 1), (8, "Bm", 1), (9, "G", 1), (10, "Em", 1), (11, "A", 1),
        (12, "D", 1), (13, "G", 0.5), (13.5, "A", 0.5)]
ARP = [0, 1, 2, 3, 1, 2, 3, 2]


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def secs(d):
    return np.arange(int(d * SR)) / SR


def pan2(m, pan=0.0):
    return np.stack([m * np.sqrt(0.5 * (1 - pan)), m * np.sqrt(0.5 * (1 + pan))])


class Bus:
    def __init__(self, n):
        self.x = np.zeros((2, n))

    def add(self, t0, sig, pan=0.0):
        if sig.ndim == 1:
            sig = pan2(sig, pan)
        a = int(round(t0 * SR))
        if a < 0:                                   # starts before 0 s: keep only the audible part
            sig, a = sig[:, -a:], 0
        b = min(self.x.shape[1], a + sig.shape[1])
        if b > a:
            self.x[:, a:b] += sig[:, : b - a]


# ---- instruments -------------------------------------------------------------

def pad_note(f, d, att=0.35, rel=0.7, amp=1.0):
    """Detuned stack of soft harmonics, one detune per channel for width."""
    x = secs(d + rel)
    env = np.clip(x / att, 0, 1) * np.clip((d + rel - x) / rel, 0, 1) * amp
    out = np.zeros((2, len(x)))
    for ch, det in ((0, -0.0035), (1, 0.0035)):
        for k in (1, 2, 3, 4, 5):
            out[ch] += np.sin(2 * np.pi * f * k * (1 + det) * x + 1.7 * k + ch) / k ** 1.4
    return out * env


def pluck(f, amp, tau=0.35):
    x = secs(0.9)
    s = sum(np.sin(2 * np.pi * f * k * x) * a * np.exp(-x / (tau * td)) for k, a, td in ((1, 1.0, 1.0), (2, 0.4, 0.45), (3, 0.18, 0.25)))
    return s * np.clip(x / 0.003, 0, 1) * amp


def kick(amp):
    x = secs(0.45)
    f = 45 + 75 * np.exp(-x / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x / 0.17)
    click = filt(rng.standard_normal(len(x)), "highpass", 2500) * np.exp(-x / 0.004) * 0.25
    return np.tanh((body + click) * 1.5) * amp


def clap(amp):
    x = secs(0.35)
    n = filt(filt(rng.standard_normal(len(x)), "highpass", 1100), "lowpass", 6000)
    env = sum(np.where(x >= o, np.exp(-(x - o) / 0.008), 0) for o in (0, 0.011, 0.022)) * 0.6 + np.where(x >= 0.03, np.exp(-(x - 0.03) / 0.09), 0)
    return n * env * amp


def hat(amp):
    x = secs(0.12)
    return filt(rng.standard_normal(len(x)), "highpass", 7500) * np.exp(-x / 0.025) * amp


def bass_note(f, d, amp):
    x = secs(d)
    s = sum(np.sin(2 * np.pi * f * k * x) / k for k in range(1, 7))
    env = np.clip(x / 0.006, 0, 1) * (0.55 + 0.45 * np.exp(-x / 0.08)) * np.clip((d - x) / 0.03, 0, 1)
    return s * env * amp


def crash(amp, d=3.0):
    x = secs(d)
    env = np.exp(-x / 0.9) * np.clip(x / 0.002, 0, 1)
    return np.stack([filt(rng.standard_normal(len(x)), "highpass", 3800) * env for _ in range(2)]) * amp


def riser(d, amp):
    x = secs(d)
    p = x / d
    n = rng.standard_normal(len(x))
    s = (filt(n, "bandpass", [500, 2500]) * (1 - p) + filt(n, "highpass", 3000) * p) * p ** 2.5
    s = s * np.clip((d - x) / 0.01, 0, 1)
    return np.stack([s, np.roll(s, int(0.0007 * SR))]) * amp


# ---- arrangement ---------------------------------------------------------------

def compose(tl, n):
    sl = {s["id"]: s for s in tl["slides"]}
    T1, T3 = sl["S1"]["start"], sl["S3"]["start"]
    bar = (T3 - T1) / 12
    beat, eighth = bar / 4, bar / 8
    end = n / SR
    at = lambda b: T1 + b * bar
    print(f"tempo {60 / beat:.1f} BPM, bar {bar:.3f}s, final chord at {at(14):.2f}s (last line ends {tl['units'][-1]['end']:.2f}s)")

    B = {k: Bus(n) for k in ("pad_dark", "pad_bright", "arp", "bass", "kick", "perc", "fx")}

    # S0: soft D swell under the chapter card
    for m in CHORDS["D"][1][:3]:
        B["pad_dark"].add(0.8, pad_note(midi(m), T1 - 0.8, att=2.2, amp=0.6))
    B["pad_dark"].add(0.8, pad_note(midi(50), T1 - 0.8, att=2.2, amp=0.5))

    for b, name, length in PROG:
        t0, d = at(b), length * bar
        root, notes = CHORDS[name]
        pad = B["pad_dark" if b < 6 else "pad_bright"]
        for m in notes:
            pad.add(t0, pad_note(midi(m), d, amp=0.55))
        pad.add(t0, pad_note(midi(root + 12), d, amp=0.5))
        # arp: fades in over the first bar, a touch louder from S2
        for i in range(int(round(length * 8))):
            ramp = min(1.0, 0.45 + 0.55 * (b + i / 8))
            amp = (0.22 if b < 6 else 0.27) * ramp * (1.0 if i % 2 == 0 else 0.75)
            B["arp"].add(t0 + i * eighth, pluck(midi(notes[ARP[i]] + 12), amp), pan=(-0.35, 0.35)[i % 2])
        beats = int(round(length * 4))
        for k in range(beats):
            tb = t0 + k * beat
            pre_drop = b == 11 and k >= 2           # leave room for the riser into S3
            if b < 6:
                if k % 2 == 0:
                    B["kick"].add(tb, kick(0.55))
            elif not pre_drop:
                B["kick"].add(tb, kick(0.7))
                if k % 2 == 1:
                    B["perc"].add(tb, clap(0.35), pan=0.1)
            if b >= 10 and not pre_drop:
                B["perc"].add(tb + eighth, hat(0.16 if b < 12 else 0.22), pan=0.3)
        if b >= 6:
            for i in range(int(round(length * 8))):
                if b == 11 and i >= 4:
                    break
                B["bass"].add(t0 + i * eighth, bass_note(midi(root), eighth * 0.85, 0.32))

    # riser into S3, crash on its downbeat
    B["fx"].add(T3 - 1.6, riser(1.6, 0.35))
    B["fx"].add(T3, crash(0.22))

    # final chord + chime when the last line ends, ringing out into the fade
    tf = at(14)
    hold = end - tf
    for m in CHORDS["D"][1]:
        B["pad_bright"].add(tf, pad_note(midi(m), hold, att=0.05, rel=0.01, amp=0.6))
    B["pad_bright"].add(tf, pad_note(midi(50), hold, att=0.05, rel=0.01, amp=0.6))
    B["bass"].add(tf, bass_note(midi(38), hold, 0.3))
    B["kick"].add(tf, kick(0.75))
    B["fx"].add(tf, crash(0.2))
    for i, m in enumerate([74, 78, 81, 86]):
        B["arp"].add(tf + 0.05 * i, pluck(midi(m), 0.25, tau=1.2), pan=(-0.3, -0.1, 0.1, 0.3)[i])

    # sidechain pump on bass/pads from the kick (S2 onward)
    t = np.arange(n) / SR
    pump = np.ones(n)
    for k in range(int((tf - at(6)) / beat) + 1):
        tb = at(6) + k * beat
        a = int(tb * SR)
        seg = t[a:a + int(beat * SR)] - tb
        pump[a:a + len(seg)] = 1 - 0.35 * np.exp(-seg / 0.12)

    dark = np.stack([filt(c, "lowpass", 1400) for c in B["pad_dark"].x])
    bright = np.stack([filt(c, "lowpass", 3200) for c in B["pad_bright"].x])
    pads = (dark + bright) * pump
    arp = np.stack([filt(c, "lowpass", 6000) for c in B["arp"].x])
    d3, d2 = int(3 * eighth * SR), int(2 * eighth * SR)
    arp[0, d3:] += arp[1, :-d3] * 0.3                       # ping-pong echo
    arp[1, d2:] += arp[0, :-d2] * 0.3
    bass = np.stack([filt(c, "lowpass", 450) for c in B["bass"].x]) * pump

    send = pads * 0.35 + arp * 0.3 + B["perc"].x * 0.25 + B["fx"].x * 0.3
    wet = reverb(send, secs=2.4, wet=1.0) - send
    music = pads + arp + bass + B["kick"].x + B["perc"].x + B["fx"].x + wet * 0.8

    music = voice_dip(np.stack([filt(c, "highpass", 35) for c in music]))
    music *= np.clip((end - t) / FADE_OUT, 0, 1)
    music = np.tanh(music / np.abs(music).max() * 1.3)
    return music, T1, tl["units"][-1]["end"]


def voice_dip(music):
    """Wide dip at 1-4 kHz so the music stays out of the voice's clarity range."""
    band = sosfiltfilt(butter(2, [1000, 4000], "bandpass", fs=SR, output="sos"), music, axis=1)
    return music - (1 - 10 ** (MID_CUT_DB / 20)) * band


# ---- supplied track, re-edited by bars -------------------------------------------

# measured bar grid per supplied track: first downbeat, bar length, the bar pieces to play
# (bar index ranges, None = file start / end) and the bar that should land on S3's first beat
TRACKS = {
    "morrixbackgroundmusic-minimal-momentum-chorus-tech-corporate-511750": {
        "d0": 1.139, "bar": 1.636,           # 146.7 BPM
        # intro + D0 | body D1-D6 three times (last from D3, the bars closest to D7) | pre-chorus D7, chorus D8-9, final hit D10, tail
        "pieces": [(None, 1), (1, 7), (1, 7), (3, 7), (7, None)],
        "s3_bar": 8,
    },
}
SPLICE_XF = 0.04      # crossfade at each splice
SPLICE_SEARCH = 0.02  # +- window to line the incoming bar up with the outgoing one
TRACK_FADE = 0.5


def decode(path):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64).reshape(-1, 2).T


def best_shift(src, a, b):
    """Shift (samples) of the incoming position b that best matches the audio continuing from a."""
    w, r = int(0.08 * SR), int(SPLICE_SEARCH * SR)
    ref = src[:, a:a + w].sum(axis=0)
    scores = [np.dot(ref, src[:, b + d:b + d + w].sum(axis=0)) /
              (np.linalg.norm(src[:, b + d:b + d + w].sum(axis=0)) + 1e-9) for d in range(-r, r + 1)]
    return int(np.argmax(scores)) - r


def splice(src, cfg, pieces, target_bar):
    """Join the given bar pieces of the track (crossfaded splices); returns the audio and where target_bar lands in it."""
    bar_at = lambda k: int(round((cfg["d0"] + k * cfg["bar"]) * SR))
    pieces = [(0 if a is None else bar_at(a), src.shape[1] if b is None else bar_at(b)) for a, b in pieces]
    xf = int(SPLICE_XF * SR)
    fade_in, fade_out = np.sin(np.linspace(0, np.pi / 2, xf)), np.cos(np.linspace(0, np.pi / 2, xf))
    tgt = bar_at(target_bar)
    out = [src[:, pieces[0][0]:pieces[0][1]]]
    n_out, pos = out[0].shape[1], None
    for (_, prev_end), (a, b) in zip(pieces, pieces[1:]):
        if a == prev_end:                                   # contiguous in the original: no splice
            seg = src[:, a:b]
        else:
            a += best_shift(src, prev_end, a)
            joint = src[:, prev_end:prev_end + xf] * fade_out + src[:, a:a + xf] * fade_in
            seg = np.concatenate([joint, src[:, a + xf:b]], axis=1)
        if a <= tgt < b:
            pos = n_out + (tgt - a)
        out.append(seg)
        n_out += seg.shape[1]
    return np.concatenate(out, axis=1), pos


def place(out, pos, t_target, n):
    """Put the edited track on an n-sample timeline so sample pos lands at t_target; fade out at the end."""
    offset = int(round(t_target * SR)) - pos
    music = np.zeros((2, n))
    seg = out[:, max(0, -offset): n - offset]
    music[:, max(0, offset): max(0, offset) + seg.shape[1]] = seg
    t = np.arange(n) / SR
    music *= np.clip((n / SR - t) / TRACK_FADE, 0, 1)
    return music, offset


def edit_track(path, tl, n):
    """Re-cut the supplied track by bars so its chorus lands on S3, then place it on the section timeline."""
    cfg = TRACKS[pathlib.Path(path).stem]
    out, s3_pos = splice(decode(path), cfg, cfg["pieces"], cfg["s3_bar"])
    sl = {s["id"]: s for s in tl["slides"]}
    music, offset = place(out, s3_pos, sl["S3"]["start"], n)
    print(f"track starts at {offset / SR:.2f}s, chorus (bar {cfg['s3_bar']}) at {(offset + s3_pos) / SR:.3f}s "
          f"(S3 {sl['S3']['start']:.3f}s), final hit at {(offset + s3_pos + 2 * cfg['bar'] * SR) / SR:.2f}s")
    return voice_dip(music), sl["S1"]["start"], tl["units"][-1]["end"]


# ---- ducking + mix ---------------------------------------------------------------

def read_wav(path):
    with wave.open(str(path), "rb") as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x.reshape(-1, ch).T, sr


def write_wav(path, x):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1).T * 32767).astype(np.int16).tobytes())
    print(path)


def speech_activity(voice, n, hop=0.01, win=0.05, lookahead=0.06, hold=0.25):
    """Smoothed 0..1 speech envelope per sample (attack 80 ms, release 400 ms) plus the speech RMS."""
    h, w = int(hop * SR), int(win * SR)
    frames = np.array([np.sqrt(np.mean(voice[i:i + w] ** 2) + 1e-12) for i in range(0, n, h)])
    loud = frames[frames > 10 ** (-45 / 20)]
    speech_rms = np.sqrt(np.mean(loud ** 2))
    active = (frames > speech_rms * 10 ** (-20 / 20)).astype(float)
    k = int(hold / hop)
    held = np.array([active[max(0, i - k): i + 1].max() for i in range(len(active))])
    held = np.roll(held, -int(lookahead / hop)); held[-int(lookahead / hop):] = 0
    a_att, a_rel = 1 - np.exp(-hop / 0.08), 1 - np.exp(-hop / 0.4)
    env, e = np.zeros(len(held)), 0.0
    for i, v in enumerate(held):
        e += (a_att if v > e else a_rel) * (v - e)
        env[i] = e
    return np.interp(np.arange(n) / SR, np.arange(len(env)) * hop, env), speech_rms


def db(x):
    return 20 * np.log10(x + 1e-12)


def main(section, track=None, tag="", video=None):
    P = paths(section, video)
    sid = P["id"]
    tl = json.loads(P["timeline"].read_text(encoding="utf-8"))
    mix, sr = read_wav(P["mix"])
    if sr != SR:
        raise SystemExit(f"{P['mix']} is {sr} Hz, run sfx.py first")
    n = mix.shape[1]
    vraw, vsr = read_wav(P["wav"])
    voice = resample_poly(vraw.mean(axis=0), SR, vsr)[:n]
    voice = np.pad(voice, (0, n - len(voice)))

    music, t_start, t_last = edit_track(track, tl, n) if track else compose(tl, n)
    env, speech_rms = speech_activity(voice, n)

    # base level: music RMS over the narrated part = speech RMS + GAP_DB, then duck while speaking
    a, b = int(t_start * SR), int(t_last * SR)
    music_rms = np.sqrt(np.mean(music[:, a:b] ** 2))
    base = music * (speech_rms * 10 ** (GAP_DB / 20) / music_rms)
    ducked = base * 10 ** (DUCK_DB * env / 20)

    out = mix + ducked
    peak, lim = np.abs(out).max(), 10 ** (PEAK_LIMIT_DB / 20)
    if peak > lim:
        out *= lim / peak

    on = (env > 0.9)[a:b]
    off = (env < 0.1)[a:b]
    rms = lambda x, m: np.sqrt(np.mean(x[:, a:b][:, m] ** 2))
    print(f"music vs speech: {db(rms(ducked, on) / speech_rms):.1f} dB while speaking, "
          f"{db(rms(ducked, off) / speech_rms):.1f} dB in pauses")
    print(f"duration {n / SR:.3f}s, peak {db(np.abs(out).max()):.1f} dBFS")

    P["bgm"].mkdir(parents=True, exist_ok=True)
    write_wav(P["bgm"] / f"bgm{tag}_{sid}.wav", base / np.abs(base).max() * 10 ** (-3 / 20))
    mix_path = P["bgm"] / f"{sid}_bgm{tag}_mix.wav"
    write_wav(mix_path, out)

    P["trials"].mkdir(parents=True, exist_ok=True)
    dst = P["trials"] / f"bac{tag}_{sid}.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(P["mp4"]), "-i", str(mix_path),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(dst)], check=True)
    print(dst)


# ---- whole film v2: a synthesized score that builds chapter by chapter to the closing -----------------
# Reference (morrix track, measured): A major, 146.7 BPM, bass D -> E -> F# -> A (IV-V-vi-I), 8th-note plucks,
# four-on-the-floor in the chorus. Same key, tempo, progression and groove; the hook is our own.

FILM_BPM = 146.7
FILM_CHORDS = [  # (bass midi, voicing) for D, E, F#m, A
    (38, [62, 66, 69, 74]), (40, [64, 68, 71, 76]), (42, [61, 66, 69, 73]), (45, [64, 69, 73, 76])]
# hook over one 4-bar cycle: (bar, eighth, midi, length in eighths)
HOOK = [(0, 0, 74, 2), (0, 2, 73, 1), (0, 3, 74, 1), (0, 4, 76, 2), (0, 6, 74, 1), (0, 7, 73, 1),
        (1, 0, 71, 2), (1, 2, 68, 1), (1, 3, 71, 1), (1, 4, 76, 3), (1, 7, 74, 1),
        (2, 0, 73, 2), (2, 2, 69, 1), (2, 3, 73, 1), (2, 4, 78, 2), (2, 6, 76, 1), (2, 7, 73, 1),
        (3, 0, 76, 3), (3, 3, 73, 1), (3, 4, 69, 4)]
CARD = 3.5    # chapter card length
# master level per section in dB: intro, ch1, ch2, ch3, (ch4 start, ch4 end), closing, final page
FILM_GAIN_DB = [-7.0, -5.5, -4.5, -3.0, (-2.0, -0.5), 0.0, 1.5]


def snare(amp):
    x = secs(0.25)
    body = np.sin(2 * np.pi * 190 * x) * np.exp(-x / 0.05)
    noise = filt(rng.standard_normal(len(x)), "bandpass", [1500, 9000]) * np.exp(-x / 0.07)
    return np.tanh((body * 0.6 + noise) * 1.4) * amp


def saw_pad(f, d, amp, att=0.25, rel=0.5):
    """Brighter string-like pad (more harmonics, slow vibrato) for the later chapters."""
    x = secs(d + rel)
    env = np.clip(x / att, 0, 1) * np.clip((d + rel - x) / rel, 0, 1) * amp
    vib = 1 + 0.002 * np.sin(2 * np.pi * 5.2 * x)
    out = np.zeros((2, len(x)))
    for ch, det in ((0, -0.004), (1, 0.004)):
        for k in range(1, 9):
            out[ch] += np.sin(2 * np.pi * f * k * (1 + det) * vib * x + k * (1.3 + ch)) / k
    return out * env


def lead(f, d, amp):
    """Bright plucked lead with a touch of vibrato for the hook."""
    x = secs(d + 0.35)
    vib = 1 + 0.003 * np.sin(2 * np.pi * 5.5 * x) * np.clip(x / 0.25, 0, 1)
    s = sum(np.sin(2 * np.pi * f * k * vib * x) / k ** 1.1 for k in range(1, 7))
    env = np.clip(x / 0.004, 0, 1) * (0.45 + 0.55 * np.exp(-x / 0.18)) * np.clip((d + 0.35 - x) / 0.35, 0, 1)
    return s * env * amp


def boom(amp):
    x = secs(2.0)
    f = 34 + 50 * np.exp(-x / 0.08)
    return np.tanh(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x / 0.7) * 1.8) * amp


def compose_film(starts, t_s3, n):
    """One score for the whole film: every chapter adds a layer, chapter cards are breakdowns, the closing's
    final page gets the biggest chorus. starts = section start times (intro first, closing last)."""
    bar = 240 / FILM_BPM
    beat, e8, e16 = bar / 4, bar / 8, bar / 16
    end = n / SR
    K0 = int(np.ceil(t_s3 / bar))                # bar index of the closing's final page
    T = lambda k: t_s3 + (k - K0) * bar          # bar 0 starts at or just before 0 s
    n_bars = int((end - T(0)) / bar) + 1
    print(f"tempo {FILM_BPM} BPM, bar {bar:.3f}s, {n_bars} bars, grid starts at {T(0):.3f}s, final page = bar {K0} at {T(K0):.3f}s")

    sec_of = lambda t: int(np.searchsorted(starts, t, side="right") - 1)
    # breakdown bars under every chapter card (not the intro's title card); first content bar after each
    breakdown, reentry = set(), set()
    for s0 in starts[1:]:
        kb = int(np.floor((s0 - T(0)) / bar))
        kc = int(np.ceil((s0 + CARD - 0.25 * bar - T(0)) / bar))
        breakdown.update(range(kb, kc))
        reentry.add(kc)
    ch4 = (starts[-2], starts[-1])

    B = {k: Bus(n) for k in ("pad_dark", "pad_bright", "strings", "arp", "bass", "lead", "kick", "perc", "fx")}
    for b in B.values():
        b.x = b.x.astype(np.float32)
    cache = {}
    hit = lambda name, f: cache.setdefault(name, f())
    K, CL, SN, HT = (hit("kick", lambda: kick(1.0)), hit("clap", lambda: clap(1.0)), hit("snare", lambda: snare(1.0)), hit("hat", lambda: hat(1.0)))
    kicks = []

    for k in range(n_bars):
        t0 = T(k)
        if t0 >= end or k > K0 + 3:
            break
        root, notes = FILM_CHORDS[(k - K0) % 4]
        L = sec_of(max(0.0, t0 + bar / 2))       # 0 intro .. 5 closing
        final_page = k >= K0
        if final_page:
            L = 6
        bd = k in breakdown and not final_page
        pre_s3 = K0 - 2 <= k < K0
        last_bar = k == K0 + 3                   # resolves on A: final chord, held to the end

        # pads (always), brighter from chapter 2
        if last_bar:
            d = end - t0
            for m in notes + [root + 12]:
                B["pad_bright"].add(t0, pad_note(midi(m), d - 0.6, att=0.02, rel=0.6, amp=0.7))
            B["bass"].add(t0, bass_note(midi(root - 12), d - 0.3, 0.4))
            B["kick"].add(t0, K * 0.85); B["fx"].add(t0, crash(0.3, 3.5))
            for i, m in enumerate([81, 85, 88, 93]):
                B["arp"].add(t0 + 0.06 * i, pluck(midi(m), 0.3, tau=1.3), pan=(-0.3, -0.1, 0.1, 0.3)[i])
            continue
        pad = B["pad_dark" if L < 2 else "pad_bright"]
        for m in notes:
            pad.add(t0, pad_note(midi(m), bar, amp=0.5 if L < 5 else 0.6))
        pad.add(t0, pad_note(midi(root + 12), bar, amp=0.45))

        # strings from chapter 4, growing through it
        if L >= 4:
            g = 0.35 + 0.65 * np.clip((t0 - ch4[0]) / (ch4[1] - ch4[0]), 0, 1) if L == 4 else 1.0
            for m in notes[1:] + [notes[-1] + 12]:
                B["strings"].add(t0, saw_pad(midi(m), bar, 0.07 * g * (1.25 if L == 6 else 1.0)))

        # 8th-note pluck arp (half level in breakdowns), counter arp an octave up from chapter 3
        intro_fade = np.clip(t0 / 6.0, 0.3, 1.0)
        for i in range(8):
            amp = (0.17 + 0.015 * min(L, 5)) * (1.0 if i % 2 == 0 else 0.75) * (0.55 if bd else 1.0) * intro_fade
            B["arp"].add(t0 + i * e8, pluck(midi(notes[ARP[i]] + 12), amp), pan=(-0.35, 0.35)[i % 2])
            if L >= 3 and not bd:
                B["arp"].add(t0 + i * e8 + e16, pluck(midi(notes[ARP[7 - i]] + 24), 0.06 + 0.01 * (L - 3), tau=0.2), pan=(0.5, -0.5)[i % 2])

        if bd:
            continue

        # drums
        phrase_end = (k - K0) % 8 == 7
        for j in range(4):
            tb = t0 + j * beat
            if pre_s3:
                break
            four = L >= 3
            if four or j % 2 == 0:
                B["kick"].add(tb, K * (0.45 + 0.06 * min(L, 6)))
                kicks.append(tb)
            if L >= 1 and j % 2 == 1:
                B["perc"].add(tb, CL * (0.28 + 0.03 * L), pan=0.1)
                if L >= 5:
                    B["perc"].add(tb, SN * 0.3, pan=-0.1)
            if L >= 2:
                B["perc"].add(tb + e8, HT * (0.12 + 0.015 * L), pan=0.3)
            if L >= 3:
                for h in (1, 3):
                    B["perc"].add(tb + h * e16, HT * 0.05, pan=-0.3)
        if phrase_end and L >= 3 and not pre_s3:   # snare fill on the last beat of every 8 bars
            for i in range(4):
                B["perc"].add(t0 + 3 * beat + i * e16, SN * (0.16 + 0.06 * i), pan=0.05)
        if k in reentry:
            B["fx"].add(t0, crash(0.18 + 0.02 * L, 2.5))
        if pre_s3:                               # snare roll + riser into the final page
            sub = 4 if k == K0 - 2 else 8
            for i in range(4 * sub):
                B["perc"].add(t0 + i * beat / sub, SN * (0.08 + 0.3 * (i / (4 * sub)) ** 1.5 + (0.15 if k == K0 - 1 else 0)))
        if k == K0:
            B["fx"].add(t0, crash(0.38, 3.5)); B["fx"].add(t0, boom(0.6))

        # bass: 8th pulse from chapter 1, octave bounce from chapter 4
        if L >= 1 and not (pre_s3 and k == K0 - 1):
            for i in range(8):
                m = root + (12 if L >= 4 and i % 2 == 1 else 0)
                B["bass"].add(t0 + i * e8, bass_note(midi(m), e8 * 0.85, 0.24 + 0.02 * min(L, 6)))

        # hook: sparse early on, every cycle in the closing, doubled an octave up at the climax
        cyc = (k - K0) % 4
        every = {0: 16, 1: 16, 2: 16, 3: 8, 4: 8}.get(L, 4)
        if (k - K0) % every < 4 and not pre_s3:
            amp = {0: 0.09, 1: 0.1, 2: 0.11, 3: 0.12, 4: 0.14, 5: 0.2, 6: 0.24}[L]
            for cb, e, m, ln in HOOK:
                if cb == cyc:
                    B["lead"].add(t0 + e * e8, lead(midi(m), ln * e8 * 0.92, amp), pan=0.05)
                    if L >= 5:
                        B["lead"].add(t0 + e * e8, lead(midi(m + 12), ln * e8 * 0.92, amp * 0.45), pan=-0.15)

    # risers into every chapter's content (and into the final page)
    for s0 in starts[1:]:
        kc = int(np.ceil((s0 + CARD - 0.25 * bar - T(0)) / bar))
        d = T(kc) - max(s0 - 0.3, T(kc) - 5.0)
        B["fx"].add(T(kc) - d, riser(d, 0.22))
    B["fx"].add(T(K0) - 2 * bar, riser(2 * bar, 0.32))

    # sidechain pump on pads / strings / bass from the kicks (chapter 3 on)
    pump = np.ones(n, np.float32)
    seg = np.arange(int(beat * SR)) / SR
    curve = (1 - 0.3 * np.exp(-seg / 0.12)).astype(np.float32)
    for tb in kicks:
        if sec_of(tb) >= 3:
            a = int(tb * SR); m = min(len(curve), n - a)
            if m > 0:
                pump[a:a + m] = np.minimum(pump[a:a + m], curve[:m])

    lp = lambda bus, f: np.stack([filt(c, "lowpass", f) for c in bus.x]).astype(np.float32)
    pads = (lp(B["pad_dark"], 1400) + lp(B["pad_bright"], 3200)) * pump
    strings = lp(B["strings"], 5200) * pump
    arp = lp(B["arp"], 6500)
    d3, d2 = int(3 * e8 * SR), int(2 * e8 * SR)
    arp[0, d3:] += arp[1, :-d3] * 0.25                       # ping-pong echo
    arp[1, d2:] += arp[0, :-d2] * 0.25
    bass = lp(B["bass"], 450) * pump
    leadx = lp(B["lead"], 7000)
    send = pads * 0.3 + strings * 0.35 + arp * 0.3 + leadx * 0.35 + B["perc"].x * 0.2 + B["fx"].x * 0.3
    from scipy.signal import oaconvolve                    # overlap-add: long reverb without one giant FFT
    nir = int(2.4 * SR)
    ir = np.stack([filt(rng.standard_normal(nir), "lowpass", 6000) * np.exp(-np.arange(nir) / SR / 0.55) for _ in range(2)])
    ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
    wet = np.stack([oaconvolve(send[c], ir[c])[:n] for c in range(2)]).astype(np.float32)
    music = pads + strings + arp + bass + leadx + B["kick"].x + B["perc"].x + B["fx"].x + wet * 0.7
    del B, pads, strings, arp, bass, leadx, send, wet

    music = np.stack([filt(c, "highpass", 35) for c in music])
    t = np.arange(n) / SR
    # master level rises chapter by chapter (ramped over each chapter card), chapter 4 climbs through, the final page peaks
    pts = [(0, FILM_GAIN_DB[0])]
    for i, s0 in enumerate(starts[1:], 1):
        pts += [(s0, pts[-1][1]), (s0 + CARD, FILM_GAIN_DB[i][0] if isinstance(FILM_GAIN_DB[i], tuple) else FILM_GAIN_DB[i])]
        if isinstance(FILM_GAIN_DB[i], tuple):
            pts.append(((starts[i + 1] if i + 1 < len(starts) else end), FILM_GAIN_DB[i][1]))
    pts = [p for p in pts if p[0] < T(K0) - 2 * bar] + [(T(K0) - 2 * bar, FILM_GAIN_DB[-2]), (T(K0), FILM_GAIN_DB[-1]), (end, FILM_GAIN_DB[-1])]
    gx, gy = zip(*pts)
    music *= 10 ** (np.interp(t, gx, gy) / 20)
    music *= np.clip(t / 2.0, 0, 1) * np.clip((end - t) / 0.6, 0, 1)
    music = np.tanh(music / np.abs(music).max() * 1.3)
    ref = np.sqrt(np.mean(music ** 2))
    for i, s0 in enumerate(starts):
        a, b = int(s0 * SR), int((starts[i + 1] if i + 1 < len(starts) else end) * SR)
        print(f"  music level section {i}: {db(np.sqrt(np.mean(music[:, a:b] ** 2)) / ref):+.1f} dB")
    a = int(T(K0) * SR)
    print(f"  final page (from {T(K0):.2f}s): {db(np.sqrt(np.mean(music[:, a:a + int(3 * bar * SR)] ** 2)) / ref):+.1f} dB")
    return music


# ---- whole film v3: the supplied track re-cut by bars per chapter (original audio only, no effects) ------------

REMIX_DB = [-5.0, -4.0, -3.5, -3.0, (-2.0, -1.0), 0.0, 1.5]   # intro, ch1, ch2, ch3, (ch4 start, end), closing, final page
REMIX_LIFT_DB = -2.0                                          # the chorus lift at the start of ch1-ch4 (the closing's stays full)
REMIX_BODY_FROM = [1, 1, 3, 1, 4, 1]                          # body bar each section's loop starts on


def remix_track(path, starts, t_s3, n):
    """Arrange the track's own bars along the film: intro bar to open, 0 -> 7 under every chapter card, the chorus
    (8-9) as a lift when each chapter's content starts, the body (1-6) looped with a different start per chapter,
    a sparse 0-0-7 breather mid ch3, a chorus every 12 bars in ch4, body/chorus alternating in the closing, then
    7 -> chorus on the final page -> final hit and tail. Only bar re-cuts, crossfades and volume."""
    cfg = TRACKS[pathlib.Path(path).stem]
    bar, end = cfg["bar"], n / SR
    K0 = int(np.ceil(t_s3 / bar))
    T = lambda k: t_s3 + (k - K0) * bar
    sec_of = lambda t: int(np.searchsorted(starts, t, side="right") - 1)
    kidx = lambda t, f: int(f((t - T(0)) / bar))

    seq = {}
    lifts = set()
    for i, s0 in enumerate(starts[1:], 1):          # chapter cards and the chorus lift after them
        kb, kc = kidx(s0, np.floor), kidx(s0 + CARD - 0.25 * bar, np.ceil)
        for k in range(kb, kc):
            seq[k] = 7 if k == kc - 1 else 0
        seq[kc], seq[kc + 1] = 8, 9
        if i < len(starts) - 1:
            lifts.update((kc, kc + 1))
    seq[0] = 0
    seq[K0 - 1] = 7                                 # into the final page
    for k in range(K0, K0 + 6):                     # chorus 8-9, final hit 10, tail 11-13
        seq[k] = 8 + (k - K0)
    # ch3 breather in the middle of the chapter
    s3a, s3b = starts[3], starts[4]
    km = kidx((s3a + s3b) / 2, np.floor)
    for j, b in enumerate((0, 0, 7)):
        seq.setdefault(km + j, b)
    # fill the rest per section: body loop (ch4: chorus every 12 bars, closing: 6 body + 2 chorus)
    count = {}
    for k in range(0, K0 + 6):
        if k in seq:
            continue
        sec = sec_of(T(k) + bar / 2)
        j = count.get(sec, 0)
        count[sec] = j + 1
        if sec == 4 and j % 14 >= 12:
            seq[k] = 8 + (j % 14 - 12)
        elif sec == 5 and j % 8 >= 6:
            seq[k] = 8 + (j % 8 - 6)
        else:
            seq[k] = 1 + (REMIX_BODY_FROM[sec] - 1 + j) % 6
    order = [seq[k] for k in range(0, K0 + 6)]

    # contiguous source bars -> pieces; the first starts at the file start (pickup), the last runs to the file end
    pieces, a = [], order[0]
    for k in range(1, len(order) + 1):
        if k == len(order) or order[k] != order[k - 1] + 1:
            pieces.append((a, order[k - 1] + 1))
            if k < len(order):
                a = order[k]
    pieces[0] = (None, pieces[0][1])
    pieces[-1] = (pieces[-1][0], None)
    out, pos = splice(decode(path), cfg, pieces, cfg["s3_bar"])
    music, offset = place(out, pos, t_s3, n)
    print(f"{len(pieces)} pieces, {len(pieces) - 1 - sum(1 for x, y in zip(pieces, pieces[1:]) if x[1] == y[0])} splices, "
          f"track starts at {offset / SR:.2f}s, chorus at {(offset + pos) / SR:.3f}s (closing S3 {t_s3:.3f}s)")
    for i, s0 in enumerate(starts):
        k1 = kidx(s0, np.floor)
        k2 = kidx(starts[i + 1], np.floor) if i + 1 < len(starts) else K0 + 6
        print(f"  section {i} bars: " + "".join(str(b) if b < 10 else "abcd"[b - 10] for b in order[max(0, k1):k2]))

    # volume: a level per section (ramped over each chapter card), ch4 climbs, the final page peaks; lifts a bit lower
    t = np.arange(n) / SR
    pts = [(0.0, REMIX_DB[0])]
    for i, s0 in enumerate(starts[1:], 1):
        lv = REMIX_DB[i]
        pts += [(s0, pts[-1][1]), (s0 + CARD, lv[0] if isinstance(lv, tuple) else lv)]
        if isinstance(lv, tuple):
            pts.append((starts[i + 1], lv[1]))
    pts = [q for q in pts if q[0] < T(K0) - bar] + [(T(K0) - bar, REMIX_DB[-2]), (T(K0), REMIX_DB[-1]), (end, REMIX_DB[-1])]
    gx, gy = zip(*pts)
    g = np.interp(t, gx, gy)
    for k in lifts:
        a, b = T(k), T(k + 1)
        g += REMIX_LIFT_DB * np.clip(np.minimum((t - a + 0.08) / 0.08, (b + 0.08 - t) / 0.08), 0, 1)
    music *= 10 ** (g / 20)
    music *= np.clip(t / 0.5, 0, 1)
    ref = np.sqrt(np.mean(music ** 2))
    for i, s0 in enumerate(starts):
        a, b = int(s0 * SR), int((starts[i + 1] if i + 1 < len(starts) else end) * SR)
        print(f"  music level section {i}: {db(np.sqrt(np.mean(music[:, a:b] ** 2)) / ref):+.1f} dB")
    return voice_dip(music)


# ---- whole film: one music bed under every section -------------------------------------

CARD_DIP = (0.4, 2.5, 3.5)   # music narrows from 0.4 s before a chapter card, stays narrow to 2.5 s, open again at 3.5 s
CARD_LP_HZ = 700
CARD_DB = -3.0


def card_dips(music, starts):
    """At every chapter card the music turns muffled and a little quieter, then opens up again."""
    t = np.arange(music.shape[1]) / SR
    w = np.zeros_like(t)
    pre, hold, end = CARD_DIP
    smooth = lambda x: x * x * (3 - 2 * x)
    for tb in starts:
        up = smooth(np.clip((t - (tb - pre)) / pre, 0, 1))
        down = 1 - smooth(np.clip((t - (tb + hold)) / (end - hold), 0, 1))
        w = np.maximum(w, np.minimum(up, down))
    lp = sosfiltfilt(butter(2, CARD_LP_HZ, "lowpass", fs=SR, output="sos"), music, axis=1)
    return (music * (1 - w) + lp * w) * 10 ** (CARD_DB * w / 20)


def full(track, skip, tag="", style="loop", video=None):
    from concat import duration
    from sections import order
    P = [paths(s, video) for s in order(video) if s not in skip]
    durs = [duration(p["mp4"]) for p in P]
    starts = np.concatenate([[0], np.cumsum(durs)[:-1]])
    n = int(round(sum(durs) * SR))
    mix, voice = np.zeros((2, n)), np.zeros(n)
    t_first = None
    for p, t0, d in zip(P, starts, durs):
        a, m = int(round(t0 * SR)), int(round(d * SR))
        x, sr = read_wav(p["mix"])                          # narration + sfx, never the section's own music
        if sr != SR:
            raise SystemExit(f"{p['mix']} is {sr} Hz, run sfx.py first")
        k = min(m, x.shape[1], n - a)
        mix[:, a:a + k] = x[:, :k]
        v, vsr = read_wav(p["wav"])
        v = resample_poly(v.mean(axis=0), SR, vsr)
        k = min(m, len(v), n - a)
        voice[a:a + k] = v[:k]
        tl = json.loads(p["timeline"].read_text(encoding="utf-8"))
        if t_first is None:
            t_first = t0 + tl["units"][0]["start"]
        t_last = t0 + tl["units"][-1]["end"]
        print(f"  {p['id']:8s} at {t0:7.2f}s  ({d:.2f}s)")
    t_s3 = starts[-1] + {s["id"]: s for s in tl["slides"]}["S3"]["start"]   # chorus on the closing's final page

    if track and style == "remix":
        music = remix_track(track, starts, t_s3, n)
    elif track:
        # intro bar | body bars 1-6 looped | the last r body bars (contiguous with bar 7) | bar 7 lead-in, chorus, final hit, tail
        cfg = TRACKS[pathlib.Path(track).stem]
        K = int((t_s3 - cfg["d0"] - 2 * cfg["bar"]) / cfg["bar"])
        q, r = divmod(K, 6)
        pieces = [(None, 1)] + [(1, 7)] * q + ([(7 - r, 7)] if r else []) + [(7, None)]
        out, pos = splice(decode(track), cfg, pieces, cfg["s3_bar"])
        music, offset = place(out, pos, t_s3, n)
        music *= np.clip((np.arange(n) / SR - max(0, offset / SR)) / 0.5, 0, 1)   # the loop may start mid-bar at 0 s: fade in
        print(f"{len(pieces)} pieces ({K} body bars), track starts at {offset / SR:.2f}s, "
              f"chorus at {(offset + pos) / SR:.3f}s (closing S3 {t_s3:.3f}s)")
        music = voice_dip(card_dips(music, starts[1:]))
    else:
        music = voice_dip(compose_film(starts, t_s3, n).astype(np.float64))

    env, speech_rms = speech_activity(voice, n)
    a, b = int(t_first * SR), int(t_last * SR)
    base = music * (speech_rms * 10 ** (GAP_DB / 20) / np.sqrt(np.mean(music[:, a:b] ** 2)))
    ducked = base * 10 ** (DUCK_DB * env / 20)
    out = mix + ducked
    peak, lim = np.abs(out).max(), 10 ** (PEAK_LIMIT_DB / 20)
    if peak > lim:
        out *= lim / peak
    on, off = (env > 0.9)[a:b], (env < 0.1)[a:b]
    rms = lambda x, m: np.sqrt(np.mean(x[:, a:b][:, m] ** 2))
    print(f"music vs speech: {db(rms(ducked, on) / speech_rms):.1f} dB while speaking, "
          f"{db(rms(ducked, off) / speech_rms):.1f} dB in pauses; duration {n / SR:.3f}s, peak {db(np.abs(out).max()):.1f} dBFS")

    bg, out_dir = P[0]["bgm"], P[0]["output"]
    bg.mkdir(parents=True, exist_ok=True)
    sfx_ = f"_{tag}" if tag else ""
    write_wav(bg / f"bgm_full{sfx_}.wav", base / np.abs(base).max() * 10 ** (-3 / 20))
    mix_path = bg / f"full{sfx_}_bgm_mix.wav"
    write_wav(mix_path, out)
    lst = out_dir / "_full_list.txt"
    lst.write_text("".join(f"file '{p['mp4'].as_posix()}'\n" for p in P), encoding="utf-8")
    dst = out_dir / f"full{sfx_}.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(mix_path),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(dst)], check=True)
    lst.unlink(missing_ok=True)
    print(f"-> {dst}  ({duration(dst):.1f}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    add_section_arg(ap)
    ap.add_argument("--track", help="use this music file (re-cut by bars, see TRACKS) instead of the synthesized bed")
    ap.add_argument("--tag", default="", help="output name tag, e.g. 2 -> bgm2_<id>.wav, <id>_bgm2_mix.wav, output/trials/bac2_<id>.mp4")
    ap.add_argument("--full", action="store_true", help="whole film: join the sections, one music bed under all of them -> output/full.mp4")
    ap.add_argument("--skip", default="", help="with --full: comma-separated section ids to leave out, e.g. ch3")
    ap.add_argument("--style", default="loop", choices=["loop", "remix"],
                    help="with --full --track: loop = body bars looped (v1), remix = the track's bars re-arranged per chapter (v3)")
    args = ap.parse_args()
    if args.full:
        full(args.track, {x.strip() for x in args.skip.split(",") if x.strip()}, args.tag, args.style, args.video)
    else:
        main(args.section or "closing", args.track, args.tag, args.video)
