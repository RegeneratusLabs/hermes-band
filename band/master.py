"""Mastering: EQ, glue saturation, peak control, EBU R128 loudness.

Deliberately small. The artistic decisions live here; the final loudness target
is handed to ffmpeg's loudnorm because a hand-rolled true-peak limiter is worse
than the one that ships with ffmpeg.
"""
from __future__ import annotations

import os
import subprocess
import wave

import numpy as np

SR = 44100


def read_wav(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        sw = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw != 2:
        raise ValueError(f"expected 16-bit wav, got {sw * 8}-bit")
    a = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    a = a.reshape(-1, nch)
    if nch == 1:
        a = np.repeat(a, 2, axis=1)
    return a, sr


def write_wav(path: str, audio: np.ndarray, sr: int = SR) -> str:
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(audio.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


def _freq_response(audio: np.ndarray, sr: int, curve) -> np.ndarray:
    """Apply a static magnitude curve. curve(freqs) -> gain multiplier."""
    squeeze = audio.ndim == 1
    a = audio[:, None] if squeeze else audio
    n = a.shape[0]
    nfft = 1 << (n - 1).bit_length()
    f = np.fft.rfftfreq(nfft, 1 / sr)
    g = curve(f)
    out = np.empty_like(a)
    for ch in range(a.shape[1]):
        X = np.fft.rfft(a[:, ch], nfft)
        out[:, ch] = np.fft.irfft(X * g, nfft)[:n]
    return out[:, 0] if squeeze else out


def hp_filter(audio, sr=SR, hz=32.0, order=4):
    return _freq_response(audio, sr,
                          lambda f: 1 / np.sqrt(1 + (hz / np.maximum(f, 1e-9)) ** (2 * order)))


def tilt_eq(audio, sr=SR, low_gain_db=0.0, mid_gain_db=0.0, high_gain_db=0.0,
            low_hz=180.0, high_hz=4200.0, mud_db=0.0, mud_hz=320.0):
    """Three-band tilt plus an optional mud scoop — the two moves that fix every
    home-rendered mix: things get thick at 300Hz and dull above 5k."""
    def curve(f):
        g = np.ones_like(f)
        g *= 10 ** (low_gain_db / 20) * (1 / (1 + (f / low_hz) ** 2)) \
            + (1 - 1 / (1 + (f / low_hz) ** 2))
        g *= 10 ** (high_gain_db / 20) * ((f / high_hz) ** 2 / (1 + (f / high_hz) ** 2)) \
            + (1 - (f / high_hz) ** 2 / (1 + (f / high_hz) ** 2))
        g *= 10 ** (mid_gain_db / 20)
        if mud_db:
            width = 1.6
            bell = np.exp(-0.5 * (np.log2(np.maximum(f, 1) / mud_hz) / width) ** 2)
            g *= 10 ** ((mud_db / 20) * bell)
        return g
    return _freq_response(audio, sr, curve)


def saturate(audio, drive=1.6, mix=0.35):
    """Soft tanh glue. Adds harmonics that make samples feel like one performance."""
    shaped = np.tanh(audio * drive) / np.tanh(drive)
    return audio * (1 - mix) + shaped * mix


def dc_block(audio):
    return audio - audio.mean(axis=0, keepdims=True)


def peak_db(audio) -> float:
    p = float(np.max(np.abs(audio))) + 1e-12
    return 20 * np.log10(p)


def normalize_peak(audio, target_db=-3.0):
    gain = 10 ** (target_db / 20) / (np.max(np.abs(audio)) + 1e-12)
    return audio * gain


def fade(audio, sr=SR, fade_in=0.05, fade_out=1.2):
    a = audio.copy()
    fi = min(int(sr * fade_in), len(a))
    if fi > 0:
        a[:fi] *= np.linspace(0, 1, fi)[:, None] ** 1.5
    fo = min(int(sr * fade_out), len(a))
    if fo > 0:
        a[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    return a


def loudnorm(src: str, dst: str, lufs: float = -14.0, tp: float = -1.0,
             codec: str = "pcm_s16le") -> dict:
    """Two-pass EBU R128 normalisation. -14 LUFS for social, -16 for VO beds."""
    probe = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", src,
        "-af", f"loudnorm=I={lufs}:TP={tp}:LRA=11:print_format=json",
        "-f", "null", "-",
    ]
    r = subprocess.run(probe, capture_output=True, text=True)
    import json
    blob = r.stderr[r.stderr.rfind("{"):]
    try:
        m = json.loads(blob[: blob.rfind("}") + 1])
    except Exception:
        m = {}
    af = f"loudnorm=I={lufs}:TP={tp}:LRA=11"
    if m:
        af += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
               f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
               f":offset={m['target_offset']}:linear=true")
    # ffmpeg refuses to write over the file it is reading
    out = dst if os.path.abspath(dst) != os.path.abspath(src) else dst + ".tmp.wav"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", src,
           "-af", af, "-ar", "44100", "-c:a", codec, out]
    subprocess.run(cmd, check=True)
    if out != dst:
        os.replace(out, dst)
    return m


def trim(audio, sr=SR, seconds: float | None = None):
    if seconds is None:
        return audio
    n = min(len(audio), int(sr * seconds))
    return audio[:n]
