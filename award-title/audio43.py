"""Synthesized award-show score for the 43 s nomination video (D major, 120 BPM, 1 beat = 0.5 s).

Everything is additive / filtered-noise synthesis in numpy + scipy; cue times match nominations.py.
"""
import wave

import numpy as np
from scipy import signal

SR = 48000
rng = np.random.default_rng(11)

NOTE = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(name):
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((NOTE[n] + 12 * (o + 1) - 69) / 12)


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def adsr(n, a, d, s, r, sus_level):
    t = np.arange(n) / SR
    dur = n / SR
    env = np.where(t < a, t / max(a, 1e-4),
                   np.where(t < a + d, 1 - (1 - sus_level) * (t - a) / max(d, 1e-4), sus_level))
    rel = np.clip((dur - t) / max(r, 1e-4), 0, 1)
    return env * rel


def additive(f0, dur, amp_fn, vib_rate=5.0, vib_depth=0.0, vib_delay=0.2, nmax=40, phase_seed=0):
    """Harmonic additive tone. amp_fn(k, t) -> amplitude of harmonic k (array over t)."""
    t = tt(dur)
    vib = 1 + vib_depth * np.sin(2 * np.pi * vib_rate * t) * np.clip((t - vib_delay) / 0.3, 0, 1)
    ph = 2 * np.pi * np.cumsum(f0 * vib) / SR
    r = np.random.default_rng(phase_seed)
    out = np.zeros_like(t)
    for k in range(1, nmax + 1):
        if k * f0 > 16000:
            break
        out += amp_fn(k, t) * np.sin(k * ph + r.uniform(0, 6.28))
    return out


def brass(f0, dur, vel=1.0, seed=0):
    n = int(dur * SR)
    t = tt(dur)
    bright = np.clip(0.45 + 0.45 * np.minimum(t / 0.06, 1) - 0.12 * np.clip((t - 0.1) / 0.5, 0, 1), 0, 1) * (0.7 + 0.3 * vel)
    tone = additive(f0, dur, lambda k, t: bright ** (k - 1) / k ** 0.7, vib_rate=5.2, vib_depth=0.003, nmax=24,
                    phase_seed=seed)
    return tone * adsr(n, 0.035, 0.2, 0.8, 0.12, 0.8) * vel


def strings(f0, dur, vel=1.0, seed=0, attack=0.25):
    n = int(dur * SR)
    out = np.zeros(n)
    for j, det in enumerate((-0.004, 0.0, 0.0045)):
        out += additive(f0 * (1 + det), dur, lambda k, t: 1.0 / k ** 1.25, vib_rate=5.5 + j * 0.3,
                        vib_depth=0.0035, vib_delay=0.1, nmax=30, phase_seed=seed + j)
    return out / 3 * adsr(n, attack, 0.3, 0.9, 0.3, 0.9) * vel


def choir(f0, dur, vel=1.0, seed=0):
    """'Ahh' vowel: harmonic amplitudes shaped by formant peaks."""
    formants = [(800, 80, 1.0), (1150, 90, 0.55), (2900, 120, 0.22), (3900, 130, 0.12)]

    def amp(k, t):
        fk = k * f0
        a = sum(g * np.exp(-((fk - F) / (B * 2.2)) ** 2) for F, B, g in formants) + 0.25 / k
        return a

    n = int(dur * SR)
    out = np.zeros(n)
    for j, det in enumerate((-0.006, -0.002, 0.002, 0.006)):
        out += additive(f0 * (1 + det), dur, amp, vib_rate=4.8 + 0.4 * j, vib_depth=0.006, vib_delay=0.3, nmax=40,
                        phase_seed=seed + 7 * j)
    return out / 4 * adsr(n, 0.5, 0.3, 0.9, 0.6, 0.9) * vel


def timpani(f0, vel=1.0, dur=2.5):
    t = tt(dur)
    out = sum(np.sin(2 * np.pi * f0 * r * t) * np.exp(-t / (0.9 / r)) * a
              for r, a in [(1, 1.0), (1.504, 0.5), (1.742, 0.3), (2.0, 0.25), (2.245, 0.15)])
    thump = rng.standard_normal(len(t)) * np.exp(-t / 0.015)
    thump = signal.lfilter(*signal.butter(2, 400 / (SR / 2)), thump)
    return (out * (1 - np.exp(-t / 0.002)) + thump * 2.0) * vel


def timp_roll(f0, dur, v0, v1):
    out = np.zeros(int((dur + 2.5) * SR))
    hits = np.arange(0, dur, 1 / 14)
    for i, h in enumerate(hits):
        v = v0 + (v1 - v0) * (h / dur) ** 1.5
        v *= rng.uniform(0.85, 1.0)
        s = timpani(f0, v, 1.2)
        k = int(h * SR)
        out[k:k + len(s)] += s
    return out


def noise(dur):
    return rng.standard_normal(int(dur * SR))


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f / (SR / 2), "high", output="sos"), x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f / (SR / 2), "low", output="sos"), x)


def cymbal(dur=4.0, vel=1.0):
    t = tt(dur)
    x = hp(noise(dur), 3500, 4) * (np.exp(-t / 1.3) * 0.8 + np.exp(-t / 0.08) * 0.6)
    ring = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f in (3120, 4470, 5310, 6720)) * 0.04 * np.exp(-t / 1.5)
    return (x + ring) * (1 - np.exp(-t / 0.002)) * vel


def swell(dur, vel=1.0):
    """Reverse-cymbal style rise ending at dur."""
    t = tt(dur)
    return hp(noise(dur), 2500, 4) * (t / dur) ** 3 * vel


def sweep_noise(dur, f0, f1, env):
    """Noise through a moving band (STFT mask): whooshes and risers."""
    x = noise(dur)
    f, tseg, Z = signal.stft(x, SR, nperseg=2048)
    fc = f0 * (f1 / f0) ** np.clip(tseg / dur, 0, 1)
    mask = np.exp(-(np.log((f[:, None] + 1) / fc[None, :]) / 0.45) ** 2)
    _, y = signal.istft(Z * mask, SR, nperseg=2048)
    y = y[: len(x)]
    if len(y) < len(x):
        y = np.pad(y, (0, len(x) - len(y)))
    return y / (np.abs(y).max() + 1e-9) * env(tt(dur))


def whoosh(dur=0.8, vel=1.0):
    return sweep_noise(dur, 300, 5000, lambda t: np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2) * vel


def riser(dur, vel=1.0):
    return sweep_noise(dur, 200, 7000, lambda t: (t / dur) ** 2.5) * vel


def impact(vel=1.0, dur=3.0):
    t = tt(dur)
    boom = np.sin(2 * np.pi * np.cumsum(36 + 60 * np.exp(-t / 0.10)) / SR) * np.exp(-t / 1.1)
    crack = lp(noise(dur), 2500) * np.exp(-t / 0.05)
    return (boom * 0.9 + crack * 0.5) * (1 - np.exp(-t / 0.003)) * vel


CHORDS = {  # voicings (bass, mid, upper)
    "D": (["D2", "D3"], ["A3", "D4", "F#4"], ["A4", "D5", "F#5"]),
    "Bm": (["B1", "B2"], ["F#3", "B3", "D4"], ["F#4", "B4", "D5"]),
    "G": (["G1", "G2"], ["G3", "B3", "D4"], ["G4", "B4", "D5"]),
    "A": (["A1", "A2"], ["E3", "A3", "C#4"], ["E4", "A4", "C#5"]),
    "Dsus": (["D2", "D3"], ["A3", "D4", "G4"], ["A4", "D5", "G5"]),
}


class Mix:
    def __init__(self, dur):
        self.n = int(dur * SR) + SR * 4
        self.L = np.zeros(self.n)
        self.R = np.zeros(self.n)

    def add(self, x, at, gain=1.0, pan=0.5):
        k = int(at * SR)
        if k >= self.n:
            return
        x = x[: self.n - k]
        self.L[k:k + len(x)] += x * gain * np.sqrt(1 - pan)
        self.R[k:k + len(x)] += x * gain * np.sqrt(pan)


def render(path, dur=43.0):
    m = Mix(dur)
    bpm_beat = 0.5

    # ---------------- intro (0-7)
    m.add(lp(noise(0.6), 200) * np.linspace(0, 1, int(0.6 * SR)) ** 2, 0.0, 0.25)
    m.add(swell(0.5, 0.5), 0.0, 1.0)
    m.add(impact(1.0), 0.5, 0.9)
    m.add(cymbal(4, 0.9), 0.5, 0.5, 0.35)
    m.add(cymbal(4, 0.9), 0.52, 0.5, 0.65)
    # brass fanfare (beats from 0.5)
    fanfare = [("D4", 0, 1.0), ("A4", 1.0, 0.5), ("D5", 1.5, 0.5), ("F#5", 2.0, 1.0), ("E5", 3.0, 0.5),
               ("D5", 3.5, 0.5), ("A5", 4.0, 2.0)]
    for name, b, l in fanfare:
        f = hz(name)
        for o, p in ((1.0, 0.45), (0.5, 0.6)):
            m.add(brass(f * o, l * bpm_beat + 0.15, 1.0, seed=int(f)), 0.5 + b * bpm_beat, 0.10, p)
    for ch, b, l in (("D", 0, 2), ("G", 2, 2), ("A", 4, 2)):
        bass, mid, _ = CHORDS[ch]
        for nme in bass:
            m.add(brass(hz(nme), l * bpm_beat + 0.2, 0.8, seed=3), 0.5 + b * bpm_beat, 0.07, 0.5)
        for nme in mid:
            m.add(strings(hz(nme), l * bpm_beat + 0.4, 0.8, seed=5, attack=0.05), 0.5 + b * bpm_beat, 0.05, 0.5)
    m.add(timp_roll(hz("D2"), 1.6, 0.15, 1.0), 1.9, 0.30)
    m.add(riser(1.5, 1.0), 2.0, 0.22)
    for T, v in ((3.0, 0.4), (3.25, 0.45)):
        m.add(impact(v, 1.5), T, 0.5)
    m.add(impact(1.2), 3.5, 0.9)
    m.add(cymbal(4.5, 1.0), 3.5, 0.6, 0.4)
    m.add(cymbal(4.5, 1.0), 3.52, 0.6, 0.6)
    m.add(timpani(hz("D2"), 1.0), 3.5, 0.45)
    prog_intro = [("D", 3.5, 1.0), ("Bm", 4.5, 1.0), ("G", 5.5, 0.75), ("A", 6.25, 0.75)]
    for ch, at, l in prog_intro:
        bass, mid, up = CHORDS[ch]
        for nme in bass:
            m.add(strings(hz(nme), l + 0.5, 1.0, seed=11), at, 0.10, 0.5)
        for i, nme in enumerate(mid + up):
            m.add(strings(hz(nme), l + 0.5, 0.9, seed=13 + i), at, 0.055, 0.3 + 0.08 * i)
        for i, nme in enumerate(mid):
            m.add(choir(hz(nme), l + 0.6, 1.0, seed=17 + i), at, 0.05, 0.35 + 0.15 * i)
    m.add(brass(hz("A4"), 1.0, 0.9), 3.5, 0.08, 0.6)
    m.add(brass(hz("D5"), 1.0, 0.9), 3.5, 0.08, 0.4)

    # ---------------- nominations (7-37)
    progs = [["D", "Bm", "G", "A"], ["Bm", "G", "D", "A"], ["G", "D", "A", "Bm"], ["D", "A", "Bm", "G"],
             ["G", "A", "Bm", "A"]]
    for k in range(5):
        t0 = 7.0 + 6.0 * k
        inten = 0.6 + 0.15 * k
        bed = 1.9 * inten
        m.add(whoosh(0.8, 1.0), t0 - 0.55, 0.28, 0.3 if k % 2 else 0.7)
        m.add(impact(0.5, 1.5), t0, 0.35)
        m.add(cymbal(2.5, 0.5), t0, 0.25, 0.5)
        for c, ch in enumerate(progs[k]):
            at = t0 + 1.5 * c
            bass, mid, up = CHORDS[ch]
            # string ostinato in 8ths on the chord tones
            pattern = [mid[0], mid[1], mid[2], mid[1]] * 3
            for j, nme in enumerate(pattern[:6]):
                note = strings(hz(nme), 0.24, 0.9, seed=20 + j, attack=0.01)
                m.add(note, at + j * 0.25, 0.05 * bed, 0.35 + 0.1 * (j % 3))
            for nme in bass:
                m.add(strings(hz(nme), 1.7, 1.0, seed=30), at, 0.09 * bed, 0.5)
            m.add(timpani(hz(bass[0]) * 2 if hz(bass[0]) < 70 else hz(bass[0]), 0.6 * inten), at, 0.3)
            if k >= 1:
                for i, nme in enumerate(up):
                    m.add(strings(hz(nme), 1.7, 0.8, seed=40 + i), at, 0.035 * bed, 0.3 + 0.2 * i)
            if k >= 2:
                for i, nme in enumerate(mid):
                    m.add(choir(hz(nme), 1.8, 1.0, seed=50 + i), at, 0.04 * bed, 0.35 + 0.15 * i)
            if k >= 3:
                for i, nme in enumerate(mid[:2]):
                    m.add(brass(hz(nme), 1.5, 0.6, seed=60 + i), at, 0.04 * bed, 0.4 + 0.2 * i)
        m.add(riser(1.4, 1.0), t0 + 1.1, 0.18 * inten)
        m.add(swell(1.3, 1.0), t0 + 1.2, 0.35 * inten)
        m.add(impact(1.0 * inten + 0.2), t0 + 2.5, 0.85)
        m.add(cymbal(4.0, 1.0), t0 + 2.5, 0.45, 0.4)
        m.add(cymbal(4.0, 1.0), t0 + 2.52, 0.45, 0.6)
        m.add(brass(hz(CHORDS[progs[k][1]][1][1]), 0.7, 1.0), t0 + 2.5, 0.07, 0.5)
        m.add(sweep_noise(0.7, 6000, 1500, lambda t: np.exp(-t / 0.25)), t0 + 5.25, 0.12, 0.5)   # dissolve shimmer

    # ---------------- finale (37-43)
    t0 = 37.0
    m.add(whoosh(0.9, 1.0), t0 - 0.6, 0.32, 0.5)
    m.add(impact(1.2), t0, 0.9)
    m.add(cymbal(3.0, 1.0), t0, 0.5)
    m.add(timp_roll(hz("A1") * 2, 1.9, 0.2, 1.1), t0 + 0.1, 0.32)
    m.add(riser(1.9, 1.0), t0 + 0.1, 0.25)
    m.add(swell(2.0, 1.0), t0, 0.5)
    for ch, at, l in (("G", t0, 1.0), ("A", t0 + 1.0, 1.0)):
        bass, mid, up = CHORDS[ch]
        for nme in bass:
            m.add(strings(hz(nme), l + 0.3, 1.0, seed=70), at, 0.11, 0.5)
        for i, nme in enumerate(mid + up):
            m.add(strings(hz(nme), l + 0.3, 1.0, seed=71 + i), at, 0.05, 0.3 + 0.07 * i)
    T = t0 + 2.0
    m.add(impact(1.5, 4.0), T, 1.0)
    m.add(cymbal(5.0, 1.2), T, 0.7, 0.4)
    m.add(cymbal(5.0, 1.2), T + 0.02, 0.7, 0.6)
    m.add(timpani(hz("D2"), 1.3), T, 0.5)
    fanfare2 = [("A4", 0, 0.5), ("D5", 0.5, 0.5), ("F#5", 1.0, 1.0), ("A5", 2.0, 1.5), ("F#5", 3.5, 0.5),
                ("D6", 4.0, 3.5)]
    for name, b, l in fanfare2:
        f = hz(name)
        for o, p in ((1.0, 0.45), (0.5, 0.55)):
            m.add(brass(f * o, l * 0.5 + 0.2, 1.0, seed=int(f) + 1), T + b * 0.5, 0.10, p)
    end = 43.0
    for ch, at in (("D", T), ("G", T + 1.0), ("Dsus", T + 2.0), ("D", T + 2.75)):
        l = (end - at) if ch == "D" and at > T else 1.0 if ch != "Dsus" else 0.75
        bass, mid, up = CHORDS[ch]
        for nme in bass:
            m.add(strings(hz(nme), l + 0.4, 1.0, seed=80), at, 0.13, 0.5)
            m.add(brass(hz(nme) * 2, l + 0.2, 0.8, seed=81), at, 0.05, 0.5)
        for i, nme in enumerate(mid + up):
            m.add(strings(hz(nme), l + 0.4, 1.0, seed=82 + i), at, 0.06, 0.25 + 0.08 * i)
        for i, nme in enumerate(mid + up[:2]):
            m.add(choir(hz(nme), l + 0.6, 1.0, seed=90 + i), at, 0.05, 0.3 + 0.1 * i)
        for i, nme in enumerate(mid):
            m.add(brass(hz(nme), l + 0.2, 0.8, seed=95 + i), at, 0.045, 0.35 + 0.15 * i)
    m.add(timp_roll(hz("D2"), 1.2, 0.2, 0.6), 41.4, 0.22)

    # ---------------- reverb, master
    n_ir = int(SR * 3.0)
    tir = np.arange(n_ir) / SR

    def ir(seed):
        r = np.random.default_rng(seed).standard_normal(n_ir) * np.exp(-tir / 0.8)
        r[: int(SR * 0.015)] = 0
        return lp(r, 6000)

    L = m.L
    R = m.R
    wetL = signal.fftconvolve(L, ir(1))[: len(L)]
    wetR = signal.fftconvolve(R, ir(2))[: len(R)]
    g = (np.abs(L).max() + 1e-9) / (np.abs(wetL).max() + 1e-9) * 0.42
    L = L + wetL * g
    R = R + wetR * g
    n = int(dur * SR)
    L, R = L[:n], R[:n]
    t = np.arange(n) / SR
    fade = np.clip((dur - t) / 1.6, 0, 1) ** 1.5
    st = np.stack([L, R], -1) * fade[:, None]
    st = hp(st.T, 25).T
    peak = np.abs(st).max()
    st = np.tanh(st / peak * 1.6) / np.tanh(1.6) * 0.89
    pcm = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    import sys
    render(sys.argv[1] if len(sys.argv) > 1 else "audio43.wav")
