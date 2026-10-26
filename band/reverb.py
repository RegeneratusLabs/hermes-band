"""Convolution reverb from a synthesised impulse response.

Rendering with fluidsynth's built-in Freeverb sounds like a 2003 soundcard.
A real IR — exponential decay, frequency-dependent tail, early reflections,
decorrelated stereo — is what makes a GM render sit in a room instead of a void.
Built from noise with numpy, convolved with FFT. No sample libraries needed.
"""
from __future__ import annotations

import numpy as np

SR = 44100


def _fft_conv(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    n = len(x) + len(h) - 1
    nfft = 1 << (n - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)
    return y[:n]


def _band(x: np.ndarray, sr: int, lo: float, hi: float) -> np.ndarray:
    """Soft band-split in the frequency domain. 0 outside, 1 inside."""
    n = len(x)
    nfft = 1 << (n - 1).bit_length()
    X = np.fft.rfft(x, nfft)
    f = np.fft.rfftfreq(nfft, 1 / sr)
    m = np.ones_like(f)
    if lo > 0:
        m *= 1 / (1 + (lo / np.maximum(f, 1e-9)) ** 4)
    if hi < sr / 2:
        m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, nfft)[:n]


def make_ir(rt60: float = 1.9, predelay: float = 0.018,
            seed: int = 0, sr: int = SR, size: float = 1.0,
            bright: float = 1.0) -> np.ndarray:
    """Stereo IR, shape (n, 2). `size` scales the room, `bright` the tail air."""
    total = predelay + rt60 * 1.15 * size
    n = int(sr * total)
    t = np.arange(n) / sr
    t_rel = np.clip(t - predelay, 0, None)

    decay = np.exp(-6.9078 * t_rel / (rt60 * size))
    decay[: int(sr * predelay)] = 0.0

    rng = np.random.default_rng(seed)
    chans = []
    for ch in range(2):
        noise = rng.standard_normal(n)
        # Split the noise and decay the highs faster than the lows — real rooms
        # eat treble first, and this is the single biggest realism cue.
        low = _band(noise, sr, 0, 2600)
        high = _band(noise, sr, 2600, sr / 2) * bright
        body = low * decay + high * (decay ** 2.3)
        # early reflections: discrete taps in the first 70ms
        for _ in range(14):
            d = predelay + rng.uniform(0.004, 0.072)
            i = int(sr * d)
            if i < n:
                body[i] += rng.uniform(-0.55, 0.55) * (1 - d / 0.09)
        chans.append(body)

    ir = np.stack(chans, axis=1)
    ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True)) + 1e-12
    return ir * 0.09


def apply_reverb(dry: np.ndarray, ir: np.ndarray, wet: float = 0.30,
                 hp_hz: float = 240.0, sr: int = SR) -> np.ndarray:
    """`dry` is (n, 2). Returns (n + tail, 2) with the reverb ringing out."""
    out = []
    for ch in range(dry.shape[1]):
        w = _fft_conv(dry[:, ch], ir[:, ch])
        w = _band(w, sr, hp_hz, sr / 2)      # keep low end of the send out
        out.append(w)
    wet_sig = np.stack(out, axis=1)
    n = wet_sig.shape[0]
    mix = np.zeros((n, dry.shape[1]))
    mix[: dry.shape[0]] += dry * (1 - wet * 0.55)
    mix += wet_sig * wet * 1.9
    return mix


def room(size=1.0, rt60=1.9, wet=0.30, bright=1.0):
    """Convenience: a named room configuration."""
    return dict(size=size, rt60=rt60, wet=wet, bright=bright)
