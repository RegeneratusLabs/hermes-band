"""General MIDI instrument map with production defaults.

Program numbers are 0-indexed GM. Ranges are the register each instrument
actually sounds good in — staying inside them is half of not sounding like MIDI.
"""
from __future__ import annotations

from dataclasses import dataclass

# name: (gm_program, low, high, pan, reverb_send, volume)
INSTRUMENTS = {
    "piano":      (0,   36, 88, 64, 34, 92),
    "rhodes":     (4,   48, 86, 72, 40, 88),
    "vibes":      (11,  53, 89, 78, 55, 78),
    "nylon":      (24,  45, 81, 40, 42, 92),
    "steel":      (25,  45, 81, 44, 38, 94),
    "steel2":     (25,  52, 86, 90, 46, 84),
    "clean_elec": (27,  45, 84, 84, 45, 80),
    "upright":    (32,  28, 55, 64, 26, 96),
    "fingerbass": (33,  28, 57, 64, 22, 98),
    "cello":      (42,  36, 72, 58, 52, 84),
    "strings":    (48,  48, 84, 56, 66, 74),
    "strings_hi": (48,  60, 88, 50, 70, 68),
    "choir":      (52,  52, 79, 64, 72, 66),
    "flute":      (73,  60, 91, 70, 48, 76),
    "kalimba":    (108, 60, 91, 34, 52, 78),
    "warm_pad":   (89,  48, 84, 60, 74, 70),
    "glass_pad":  (90,  55, 89, 88, 78, 66),
    # funk section
    "clav":       (7,   48, 84, 70, 22, 92),
    "organ":      (16,  48, 84, 64, 40, 84),
    "muted_gtr":  (28,  45, 76, 40, 16, 88),
    "brass":      (61,  50, 79, 56, 30, 86),
}

DRUM_CHANNEL = 9

# GM percussion notes
KICK, KICK2 = 36, 35
STICK, SNARE, CLAP = 37, 38, 39
SNARE_E = 40
HH, HH_PEDAL, HH_OPEN = 42, 44, 46
CRASH, RIDE = 49, 51
TAMB, MARACAS, SHAKER = 54, 70, 82
CLAVES, TRIANGLE = 75, 81


@dataclass
class Instrument:
    name: str
    program: int
    low: int
    high: int
    pan: int
    reverb: int
    volume: int

    @classmethod
    def get(cls, name: str) -> "Instrument":
        if name not in INSTRUMENTS:
            raise KeyError(f"unknown instrument {name!r}; have {sorted(INSTRUMENTS)}")
        return cls(name, *INSTRUMENTS[name])


def drums(pan: int = 64, volume: int = 92, reverb: int = 26) -> Instrument:
    """Channel 10 ignores program changes; program 0 is fine."""
    return Instrument("drums", 0, 0, 127, pan, reverb, volume)
