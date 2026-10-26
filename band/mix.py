"""The mixer: per-instrument stems, shaped and panned, then summed.

Mixing a soundfont's summed output is why so much MIDI music sounds flat — every
instrument gets the same EQ and the same reverb because they've already been
added together. Rendering one stem per part and mixing them gives each instrument
its own place in the frequency spectrum and the stereo field.
"""
from __future__ import annotations

import numpy as np

from . import master, reverb

# Per-instrument mix profile.
#   hp/lp      high- and low-pass corners in Hz
#   low/pres/air  shelf and bell gains in dB
#   level      fader in dB (relative to the sum)
#   pan        -1 left .. +1 right
#   send       reverb send, 0..2
DEFAULT = dict(hp=60, lp=16000, low=0.0, pres=0.0, air=0.0,
               level=0.0, pan=0.0, send=1.0, mud=0.0)

PROFILES = {
    "piano":      dict(hp=55, lp=15000, pres=1.5, level=-2.0, pan=-0.1, send=1.0),
    "rhodes":     dict(hp=90, lp=11000, pres=1.0, level=-3.0, pan=0.28, send=1.1),
    "vibes":      dict(hp=300, lp=14000, pres=2.0, level=-6.0, pan=0.45, send=1.3),
    "nylon":      dict(hp=100, lp=10000, pres=2.5, air=1.0, level=-1.5, pan=-0.30, send=1.0),
    "steel":      dict(hp=95, lp=11000, pres=3.0, air=1.5, level=-1.0, pan=-0.34, send=0.95),
    "steel2":     dict(hp=140, lp=13000, pres=3.0, air=2.0, level=-6.0, pan=0.52, send=1.4),
    "clean_elec": dict(hp=120, lp=9000, pres=2.0, level=-3.0, pan=0.40, send=1.1),
    "upright":    dict(hp=32, lp=2400, low=2.5, level=-2.0, pan=0.0, send=0.25),
    "fingerbass": dict(hp=30, lp=2600, low=2.0, mud=-1.5, level=-3.0, pan=0.0, send=0.25),
    "cello":      dict(hp=70, lp=7000, low=1.0, level=-4.0, pan=-0.2, send=1.2),
    "strings":    dict(hp=190, lp=9000, mud=-1.5, level=2.0, pan=-0.10, send=1.7),
    "strings_hi": dict(hp=280, lp=11000, level=-11.0, pan=0.25, send=1.9),
    "choir":      dict(hp=160, lp=8000, level=-9.0, pan=0.0, send=1.8),
    "flute":      dict(hp=240, lp=12000, pres=1.5, level=-5.0, pan=0.15, send=1.3),
    "kalimba":    dict(hp=350, lp=16000, pres=2.5, air=2.0, level=8.0, pan=0.62, send=1.5),
    "warm_pad":   dict(hp=150, lp=8000, level=-9.0, pan=0.0, send=1.6),
    "glass_pad":  dict(hp=300, lp=12000, level=-10.0, pan=0.35, send=1.8),
    "drums":      dict(hp=38, lp=15000, pres=2.0, level=6.0, pan=0.0, send=0.5, mud=-1.0),
}


def profile(inst: str, **override) -> dict:
    p = dict(DEFAULT)
    p.update(PROFILES.get(inst, {}))
    p.update({k: v for k, v in override.items() if v is not None})
    return p


def shape(audio: np.ndarray, sr: int, p: dict) -> np.ndarray:
    """Apply one instrument's EQ. Runs before panning, so it's mono-safe."""
    hp, lp = p["hp"], p["lp"]
    low, pres, air, mud = p["low"], p["pres"], p["air"], p["mud"]
    if not (low or pres or air or mud):
        return master._freq_response(audio, sr, lambda f: _hp_lp(f, hp, lp))
    mud_hz, pres_hz, air_hz = 330.0, 3800.0, 9500.0
    low_hz = 120.0

    def curve(f):
        g = _hp_lp(f, hp, lp)
        if low:                                    # low shelf
            g *= 10 ** ((low / 20) * (1 / (1 + (f / low_hz) ** 2)))
        if mud:                                    # bell cut around 330Hz
            g *= 10 ** ((mud / 20) * np.exp(-0.5 * (np.log2(np.maximum(f, 1) / mud_hz) / 1.5) ** 2))
        if pres:                                   # presence bell
            g *= 10 ** ((pres / 20) * np.exp(-0.5 * (np.log2(np.maximum(f, 1) / pres_hz) / 1.2) ** 2))
        if air:                                    # air shelf
            g *= 10 ** ((air / 20) * ((f / air_hz) ** 2 / (1 + (f / air_hz) ** 2)))
        return g
    return master._freq_response(audio, sr, curve)


def _hp_lp(f, hp, lp):
    g = 1 / np.sqrt(1 + (hp / np.maximum(f, 1e-9)) ** 4)
    g *= 1 / np.sqrt(1 + (f / lp) ** 4)
    return g


def exciter(audio: np.ndarray, sr: int, amount=0.14) -> np.ndarray:
    """Cheap harmonic exciter: distort a high-passed copy and add it back.

    Soundfont samples have no top-end sparkle at low velocities. This buys it
    back without a sample library or an expensive plugin.
    """
    if amount <= 0:
        return audio
    hi = master._freq_response(audio, sr, lambda f: _hp_lp(f, 2600.0, sr / 2))
    hi = np.tanh(hi * 3.0) / 3.0
    return audio + hi * amount


def pan(mono: np.ndarray, p: float) -> np.ndarray:
    """Constant-power pan. mono (n,) -> stereo (n,2)."""
    theta = (p + 1) * np.pi / 4
    return np.stack([mono * np.cos(theta), mono * np.sin(theta)], axis=1)


def db(x: float) -> float:
    return 10 ** (x / 20.0)


def mix_stems(stems: list[tuple[str, np.ndarray]], sr: int,
              rooms: dict | None = None, master_eq=True) -> np.ndarray:
    """stems: [(instrument_name, mono_or_stereo_audio, profile_overrides)]."""
    dry = None
    send = None
    for name, audio, overrides in stems:
        if audio.ndim == 2:
            audio = audio.mean(axis=1)
        p = profile(name, **(overrides or {}))
        audio = shape(audio, sr, p)
        audio = exciter(audio, sr, amount=p.get("air", 0) * 0.06)
        audio = audio * db(p["level"])
        st = pan(audio, p["pan"])
        if dry is None:
            n = len(st)
            dry = np.zeros((n, 2))
            send = np.zeros((n, 2))
        else:
            if len(st) > len(dry):                    # keep every tail
                pad = len(st) - len(dry)
                dry = np.pad(dry, ((0, pad), (0, 0)))
                send = np.pad(send, ((0, pad), (0, 0)))
            elif len(st) < len(dry):
                st = np.pad(st, ((0, len(dry) - len(st)), (0, 0)))
        dry += st
        send += st * p["send"]
    return dry, send


def balance(audio: np.ndarray, max_db: float = 3.0) -> np.ndarray:
    """Equalise L/R RMS. Summing left-leaning pans drifts the image; this pulls
    it back the way a mastering engineer would, without collapsing the width."""
    rl = float(np.sqrt((audio[:, 0] ** 2).mean()))
    rr = float(np.sqrt((audio[:, 1] ** 2).mean()))
    if rl <= 1e-9 or rr <= 1e-9:
        return audio
    d = 20 * np.log10(rl / rr)
    corr = float(np.clip(d / 2, -max_db, max_db))
    out = audio.copy()
    out[:, 0] *= 10 ** (-corr / 20)
    out[:, 1] *= 10 ** (corr / 20)
    return out


def finish(dry: np.ndarray, send: np.ndarray, sr: int, room: str = "room",
           seed: int = 0, trim_to: float | None = None,
           fade_in: float = 0.04, fade_out: float = 1.4,
           wet_level: float = 0.40) -> np.ndarray:
    from .renderer import ROOMS
    cfg = ROOMS.get(room, ROOMS["room"])
    ir = reverb.make_ir(rt60=cfg["rt60"], size=cfg["size"],
                        bright=cfg["bright"], seed=seed, sr=sr)
    wet = np.stack([reverb._fft_conv(send[:, ch], ir[:, ch]) for ch in range(2)], axis=1)
    wet = master._freq_response(wet, sr, lambda f: _hp_lp(f, 220.0, sr / 2))
    wet *= (np.abs(dry).max() * wet_level) / (np.abs(wet).max() + 1e-12)

    n = max(len(dry), len(wet))
    out = np.zeros((n, 2))
    out[: len(dry)] += dry
    out[: len(wet)] += wet
    out = master.trim(out, sr, trim_to)
    out = master.dc_block(out)
    out = master.hp_filter(out, sr, 30.0)
    out = master.tilt_eq(out, sr, low_gain_db=0.6, high_gain_db=3.4,
                         mud_db=-1.4, mud_hz=300.0)
    out = master.saturate(out, drive=1.4, mix=0.16)
    out = exciter(out, sr, amount=0.10)      # bus air — soundfonts have none
    out = balance(out)
    out = master.fade(out, sr, fade_in=fade_in, fade_out=fade_out)
    out = master.normalize_peak(out, -3.0)
    return out
