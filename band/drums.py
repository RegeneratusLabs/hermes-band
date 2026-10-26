"""Drum patterns on a 16-step-per-bar grid.

Each pattern maps a drum voice to a list of (step, velocity) hits, where step
runs 0..15 per bar and velocity is 0..1 of the part's peak. Written out longhand
because a drummer's feel is in the velocity numbers, not the grid.
"""
from __future__ import annotations

from . import gm


def _s(pattern: str, base: float = 1.0) -> list[tuple[int, float]]:
    """'x...x...x...x...' -> hits. 'x'=1.0, 'o'=0.62, '.'=rest, '>'=1.15."""
    out = []
    for i, c in enumerate(pattern):
        if c == "x":
            out.append((i, base))
        elif c == "o":
            out.append((i, base * 0.6))
        elif c == ">":
            out.append((i, base * 1.18))
        elif c == "-":
            out.append((i, base * 0.42))
    return out


# Soft folk / lo-fi: side stick backbeat, shaker eighths, felt kick.
FOLK_SOFT = {
    gm.KICK:  _s("x.......o.......", 0.72),
    gm.STICK: _s("....>.......>...", 0.60),
    gm.SHAKER: _s("o.o.x.o.o.o.x.o.", 0.30),
}

# Slightly fuller — adds a real snare and pedal hat.
FOLK_FULL = {
    gm.KICK:  _s("x.....o.x.......", 0.80),
    gm.STICK: _s("....>.......>...", 0.55),
    gm.SNARE: _s("............-...", 0.34),
    gm.SHAKER: _s("o.o.x.o.o.o.x.o.", 0.32),
    gm.HH_PEDAL: _s("..o...o...o...o.", 0.26),
}

# Four-on-the-floor electronic bed, for tech/explainer videos.
PULSE = {
    gm.KICK:  _s("x...x...x...x...", 0.86),
    gm.CLAP:  _s("....x.......x...", 0.44),
    gm.HH:    _s("--o---o---o---o-", 0.24),
    gm.HH_OPEN: _s("......o.......o.", 0.20),
}

# No drums, just a heartbeat kick and brush-ish shaker. Intimate.
HEARTBEAT = {
    gm.KICK:  _s("x.......x.......", 0.56),
    gm.SHAKER: _s("..o...o...o...o.", 0.22),
}

BOOM_BAP = {
    gm.KICK:  _s("x.....x...x.....", 0.88),
    gm.SNARE: _s("....>.......>...", 0.78),
    gm.HH:    _s("x-o-x-o-x-o-x-o-", 0.30),
}

PATTERNS = {
    "folk_soft": FOLK_SOFT,
    "folk_full": FOLK_FULL,
    "pulse": PULSE,
    "heartbeat": HEARTBEAT,
    "boom_bap": BOOM_BAP,
}

# Per-voice microtiming offset in ticks (drummers are never on the grid).
FEEL_OFFSET = {
    gm.KICK: 0,
    gm.STICK: 4,
    gm.SNARE: 6,
    gm.CLAP: 5,
    gm.SHAKER: -3,
    gm.HH: -2,
    gm.HH_PEDAL: 3,
    gm.HH_OPEN: 2,
}


def fill_bar(pattern: dict, bar: int, n_bars: int) -> dict:
    """A one-bar turnaround fill on the last bar of a section."""
    out = {k: list(v) for k, v in pattern.items()}
    out.pop(gm.SHAKER, None)
    out.pop(gm.HH, None)
    out[gm.SNARE] = _s(".......-x-xooooo", 0.70)
    out[gm.KICK] = _s("x.......o.......", 0.74)
    return out
