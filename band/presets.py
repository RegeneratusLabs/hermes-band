"""Three complete arrangements, ready to render.

They exist as starting points and as proof that the engine covers more than one
idiom. Copy them, bend them, or ignore them and write your own.
"""
from __future__ import annotations

from .compose import Arrangement


def bed() -> Arrangement:
    """Warm fingerpicked folk. Sparse and mid-forward, leaves 1-4 kHz clear for
    a voice, so it works as a bed under narration. 32.0 s at 90 BPM."""
    a = Arrangement(
        bpm=90, key="D", mode="major", bars=12, seed=11,
        progression=["I", "V", "vi", "IV"],       # three times round
        sections=[(0, 2, 0.74), (2, 4, 0.86), (4, 8, 0.98),
                  (8, 11, 1.0), (11, 12, 0.84)],
    )
    a.add(inst="steel", role="fingerpick", pattern="folk",
          register=(55, 79), voices=4, jitter=4, howl=0.4,
          extra={"mix": {"pan": -0.20}})
    a.add(inst="fingerbass", role="bass_root5", start_bar=2,
          register=(40, 52), gain=0.9, jitter=2)
    a.add(inst="drums", role="drums", start_bar=4, gain=0.82,
          extra={"pattern": "folk_soft", "fill": False})
    a.add(inst="steel2", role="arp", pattern="sparse", start_bar=6,
          register=(71, 86), gain=0.62, jitter=5,
          extra={"mix": {"pan": 0.42}})
    a.add(inst="strings", role="block", start_bar=8,
          register=(57, 79), voices=4, gain=0.5, jitter=6)
    return a


def full_band() -> Arrangement:
    """Melody, walking bass, kit, strings, sparkle. 34.3 s at 84 BPM."""
    a = Arrangement(
        bpm=84, key="D", mode="major", bars=12, seed=23,
        progression=["I", "V", "vi", "IV", "I", "V", "IV", "V",
                     "vi", "IV", "V", "I"],
        sections=[(0, 2, 0.78), (2, 4, 0.88), (4, 8, 1.0),
                  (8, 11, 0.97), (11, 12, 0.86)],
    )
    a.add(inst="steel", role="fingerpick", pattern="travis",
          register=(55, 79), jitter=4, howl=0.45)
    a.add(inst="fingerbass", role="bass_walk", register=(40, 52), jitter=2)
    a.add(inst="drums", role="drums", start_bar=2, gain=0.9,
          extra={"pattern": "folk_full", "fill": True})
    a.add(inst="strings", role="block", start_bar=4, register=(57, 81),
          voices=4, gain=0.52, jitter=6)
    a.add(inst="kalimba", role="sparkle", start_bar=8, register=(72, 91),
          gain=0.5, jitter=6, extra={"slots": [3, 7, 11, 14]})
    a.add(inst="nylon", role="melody", start_bar=0, register=(64, 81),
          gain=0.95, jitter=6, voices=3,
          extra={"dir": 1, "rest_bars": [1, 6],
                 "mix": {"pan": 0.16, "level": 5.5, "pres": 3.5, "send": 1.2}})
    return a


def pulse() -> Arrangement:
    """Minor-key electronic bed. 17.1 s at 112 BPM."""
    a = Arrangement(
        bpm=112, key="A", mode="minor", bars=8, seed=31,
        progression=["i", "VI", "III", "VII"],
        sections=[(0, 2, 0.70), (2, 4, 0.88), (4, 7, 1.0), (7, 8, 0.8)],
    )
    a.add(inst="warm_pad", role="block", register=(52, 76), voices=4,
          gain=0.9, jitter=3,
          extra={"hold": 1.0,
                 "mix": {"hp": 210, "lp": 13000, "pres": 3.0,
                         "level": -3.0, "send": 1.4}})
    a.add(inst="fingerbass", role="bass_root5", register=(33, 45), gain=0.95,
          jitter=1, extra={"quarters": True,
                           "mix": {"hp": 28, "lp": 1800, "level": -1.0,
                                   "send": 0.15}})
    a.add(inst="drums", role="drums", start_bar=1, gain=0.95,
          extra={"pattern": "pulse", "fill": True,
                 "mix": {"hp": 46, "mud": -2.5, "pres": 4.0, "level": 5.0}})
    a.add(inst="glass_pad", role="arp", pattern="arp_up", start_bar=3,
          register=(64, 88), gain=0.7, jitter=3, swing=0.06,
          extra={"mix": {"hp": 260, "level": -1.0, "pres": 3.0,
                         "air": 2.0, "send": 1.6}})
    a.add(inst="rhodes", role="melody", start_bar=2, register=(60, 79),
          gain=0.85, jitter=4,
          extra={"dir": -1, "mix": {"pan": 0.10, "level": 2.0, "send": 1.4}})
    return a


def funk() -> Arrangement:
    """E dorian. The one is everything; everything else is off the beat.
    36.9 s at 104 BPM."""
    a = Arrangement(
        bpm=104, key="E", mode="dorian", bars=16, seed=41,
        progression=["im7", "im7", "im7", "im7",
                     "IV7", "IV7", "im7", "im7",
                     "iim7", "iim7", "im7", "im7",
                     "IV7", "IV7", "IV7", "im7"],
        sections=[(0, 4, 0.72), (4, 8, 0.88), (8, 12, 1.0),
                  (12, 14, 0.95), (14, 16, 0.86)],
    )
    # the engine room. Funk is kick-and-bass forward, but 54% of the energy down
    # there turns to mud, so both get pulled back and cleaned up.
    a.add(inst="drums", role="drums", gain=1.0,
          extra={"pattern": "funk", "fill": False,
                 "mix": {"level": 1.0, "hp": 42, "mud": -2.5}})
    a.add(inst="fingerbass", role="slap_bass", register=(33, 45), jitter=2,
          extra={"mix": {"low": 0.5, "hp": 42, "mud": -2.0, "level": -4.0}})
    # the scratch — muted guitar eating the off-sixteenths
    a.add(inst="muted_gtr", role="funk_guitar", register=(52, 76),
          gain=0.95, jitter=3,
          extra={"mix": {"pan": -0.28, "level": 2.0}})
    # clav stabs coming in, then brass answering later
    a.add(inst="clav", role="stab", start_bar=2, register=(55, 79), gain=0.9,
          jitter=2, extra={"steps": [2, 6, 10, 14], "len16": 1.2})
    a.add(inst="brass", role="stab", start_bar=8, register=(52, 74), gain=0.62,
          jitter=2, extra={"steps": [3, 11], "len16": 2.4, "vel": 78,
                           "mix": {"level": 2.0, "send": 1.4}})
    return a


# name -> (arrangement factory, room)
PRESETS = {
    "bed": (bed, "room"),
    "band": (full_band, "hall"),
    "pulse": (pulse, "close"),
    "funk": (funk, "close"),
}
