"""The composer: turns a progression + parts into a MIDI performance.

Roles are the vocabulary. Each one knows how a real instrument plays its part —
where the thumb goes, how long a fingerpicked note rings, how far behind the beat
a snare sits. That knowledge, not the notes, is what separates this from a
MIDI file someone typed into a piano roll.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import drums as dr
from . import gm, theory
from .midi import DIV, Song

E = DIV // 2          # one eighth note in ticks

# Fingerpicking patterns: (eighth-slot, palette index).
# Palette index 0 is the bass note, 1..n the upper voicing bottom-to-top.
PATTERNS = {
    "folk":   [(0, 0), (2, 1), (4, 2), (6, 1), (0 + 0, 0), (10, 2), (12, 3), (14, 1)],
    "travis": [(0, 0), (2, 2), (4, 1), (6, 3), (8, 0), (10, 3), (12, 1), (14, 2)],
    "sparse": [(0, 0), (4, 2), (8, 0), (12, 3)],
    "arp_up": [(0, 1), (2, 2), (4, 3), (6, 4), (8, 0), (10, 4), (12, 3), (14, 2)],
    "rolling": [(0, 0), (2, 1), (3, 2), (4, 1), (6, 3), (8, 0), (10, 2), (11, 3), (12, 2), (14, 1)],
    "oompah": [(0, 0), (2, 5), (4, 0), (6, 5), (8, 0), (10, 5), (12, 0), (14, 5)],
}
# fix the folk pattern (index 4 belongs at slot 8)
PATTERNS["folk"] = [(0, 0), (2, 1), (4, 2), (6, 1), (8, 0), (10, 2), (12, 3), (14, 1)]


@dataclass
class Part:
    inst: str
    role: str
    start_bar: int = 0
    end_bar: int | None = None
    gain: float = 1.0
    octave: int = 0
    pattern: str = "folk"
    swing: float = 0.0
    jitter: int = 3
    register: tuple[int, int] | None = None
    voices: int = 4
    rootless: bool = False
    howl: float = 0.0          # extra velocity variation 0..1
    extra: dict = field(default_factory=dict)


@dataclass
class Ctx:
    key: theory.Key
    bar: int
    chord: str
    voicing: list[int]
    bass: int
    rng: random.Random
    level: float
    next_chord: str | None = None
    bars_into_section: int = 0
    section_len: int = 4


def _slot(s: float) -> int:
    return int(round(s * E))


def _swing(slot: int, amount: float) -> int:
    """Delay odd eighth notes. amount 0..0.6 of an eighth."""
    if amount and slot % 2 == 1:
        return _slot(slot) + int(E * amount)
    return _slot(slot)


def _bass_note(key, chord, low=40, high=52):
    root = theory.chord_root(key, chord)
    while root < low:
        root += 12
    while root > high:
        root -= 12
    return root


# --------------------------------------------------------------- role library

def role_fingerpick(p: Part, c: Ctx) -> list[tuple]:
    out = []
    pal = [c.bass] + sorted(c.voicing)
    pat = PATTERNS.get(p.pattern, PATTERNS["folk"])
    for k, (slot, idx) in enumerate(pat):
        if idx >= len(pal):
            idx = len(pal) - 1
        pitch = pal[idx] + 12 * p.octave
        tick = _swing(slot, p.swing) + c.rng.randint(-p.jitter, p.jitter)
        if idx == 0:                                   # thumb
            vel = 92 + c.rng.randint(-4, 4)
            dur = int(E * c.rng.choice([2.4, 2.8, 3.2]))
        else:
            vel = (78 if k % 2 == 0 else 68) + c.rng.randint(-5, 5)
            dur = int(E * c.rng.choice([1.4, 1.8, 2.2]))
        vel = vel * p.gain * c.level * (1 + p.howl * c.rng.uniform(-0.18, 0.18))
        out.append((tick, pitch, vel, dur))
    return out


def role_strum(p: Part, c: Ctx) -> list[tuple]:
    beats = p.extra.get("beats", [0, 4])
    out = []
    for b in beats:
        base = _slot(b) + c.rng.randint(-p.jitter, p.jitter)
        span = p.extra.get("spread", 7)
        direction = p.extra.get("dir", "down")
        notes = sorted(c.voicing)
        if direction == "up":
            notes = notes[::-1]
        for i, pitch in enumerate(notes):
            vel = (86 - i * 3) * p.gain * c.level
            out.append((base + i * span, pitch + 12 * p.octave, vel,
                        int(E * p.extra.get("ring", 3.2))))
    return out


def role_block(p: Part, c: Ctx) -> list[tuple]:
    bar_ticks = 4 * DIV
    dur = int(bar_ticks * p.extra.get("hold", 0.96))
    vel = (70 * p.gain) * c.level
    return [(_slot(0) + c.rng.randint(-p.jitter, p.jitter),
             v + 12 * p.octave, vel + c.rng.randint(-3, 3), dur)
            for v in sorted(c.voicing)]


def role_bass_root5(p: Part, c: Ctx) -> list[tuple]:
    out = []
    root = c.bass + 12 * p.octave
    fifth = root + 7
    for slot, pitch, acc in ((0, root, 1.0), (4, fifth, 0.78)):
        if p.extra.get("quarters"):
            for q in range(0, 8, 2):
                pitch_q = root if q in (0, 4) else fifth
                out.append((_slot(q) + c.rng.randint(-2, 2), pitch_q,
                            (84 if q == 0 else 66) * p.gain * c.level, int(E * 1.7)))
            return out
        tick = _slot(slot) + c.rng.randint(-2, 2)
        vel = 96 * acc * p.gain * c.level
        out.append((tick, pitch, vel, int(E * 3.4)))
    return out


def role_bass_walk(p: Part, c: Ctx) -> list[tuple]:
    out = []
    root = c.bass + 12 * p.octave
    out.append((_slot(0) + c.rng.randint(-2, 2), root, 98 * p.gain * c.level, int(E * 3.2)))
    out.append((_slot(3), root + 7, 74 * p.gain * c.level, int(E * 1.4)))
    out.append((_slot(4), root + 12, 82 * p.gain * c.level, int(E * 1.6)))
    if c.next_chord:
        nxt = _bass_note(c.key, c.next_chord, 40, 52) + 12 * p.octave
        approach = nxt + (1 if nxt >= root else -1)
        out.append((_slot(6), approach, 78 * p.gain * c.level, int(E * 1.6)))
    return out


def role_arp(p: Part, c: Ctx) -> list[tuple]:
    pal = [c.bass] + sorted(c.voicing)
    pat = PATTERNS.get(p.pattern, PATTERNS["arp_up"])
    out = []
    for k, (slot, idx) in enumerate(pat):
        if idx >= len(pal):
            idx = len(pal) - 1
        pitch = pal[idx] + 12 * p.octave
        if pitch < (p.register[0] if p.register else 0):
            pitch += 12
        vel = (72 + 8 * (k % 2)) * p.gain * c.level
        out.append((_swing(slot, p.swing) + c.rng.randint(-p.jitter, p.jitter),
                    pitch, vel, int(E * 1.6)))
    return out


def role_sparkle(p: Part, c: Ctx) -> list[tuple]:
    pcs = sorted(c.voicing)
    high = [x for x in pcs if x >= 67] or [pcs[-1]]
    out = []
    slots = p.extra.get("slots", [3, 11])
    for slot in slots:
        if c.rng.random() < 0.12:
            continue
        pitch = c.rng.choice(high) + 12
        out.append((_slot(slot) + c.rng.randint(-4, 4), pitch,
                    (74 + c.rng.randint(-6, 8)) * p.gain * c.level, int(E * 2.2)))
    return out


RHYTHMS = [
    [(0, 2), (2, 2), (4, 2), (6, 2)],
    [(0, 3), (3, 1), (4, 1), (6, 3)],
    [(0, 1), (1, 1), (2, 2), (4, 4)],
    [(0, 2), (3, 1), (4, 1), (6, 2)],
    [(0, 4), (4, 2), (6, 2)],
    [(0, 1), (2, 1), (3, 1), (4, 2), (6, 2)],
    [(0, 1), (2, 1), (4, 1), (5, 1), (6, 2)],
]


def role_melody(p: Part, c: Ctx) -> list[tuple]:
    lo, hi = p.register or (69, 84)
    scale = c.key.scale_pitches(lo, hi)
    if not scale:
        return []
    chord_pcs = {(x % 12) for x in c.voicing}
    rhythm = RHYTHMS[c.bar % len(RHYTHMS)]
    prev = p.extra.get("_prev")
    idx = len(scale) // 2 if prev is None else min(
        range(len(scale)), key=lambda i: abs(scale[i] - prev))
    out = []
    direction = p.extra.get("dir", 1)
    for k, (slot, length) in enumerate(rhythm):
        strong = slot in (0, 4)
        # prefer chord tones on strong beats
        if strong and chord_pcs:
            cands = [i for i in range(max(0, idx - 3), min(len(scale), idx + 4))
                     if scale[i] % 12 in chord_pcs]
            if cands:
                idx = c.rng.choice(cands)
        else:
            idx += direction * c.rng.choice([0, 1, 1, 2, -1, -1, -2])
            if c.rng.random() < 0.22:
                direction *= -1
        idx = max(0, min(len(scale) - 1, idx))
        pitch = scale[idx] + 12 * p.octave
        vel = (80 if strong else 68) + c.rng.randint(-6, 6)
        out.append((_slot(slot) + c.rng.randint(-5, 5), pitch,
                    vel * p.gain * c.level, int(E * length * 0.92)))
    p.extra["_prev"] = scale[idx]
    return out


def role_drums(p: Part, c: Ctx) -> list[tuple]:
    name = p.extra.get("pattern", "folk_soft")
    pat = dr.PATTERNS[name]
    if p.extra.get("fill") and c.bars_into_section == c.section_len - 1:
        pat = dr.fill_bar(pat, c.bar, c.section_len)
    out = []
    for voice, hits in pat.items():
        off = dr.FEEL_OFFSET.get(voice, 0)
        for step, v in hits:
            tick = int(step * DIV / 4) + off + c.rng.randint(-2, 2)
            vel = 127 * v * p.gain * c.level * (1 + c.rng.uniform(-0.07, 0.07))
            out.append((tick, voice, vel, int(DIV / 4 * 0.9)))
    return out


# ----------------------------------------------------------------- funk

# The off-sixteenths of every beat: the "e" and "a". Landing here, not on the
# downbeat, is what makes a guitar scratch rather than strum.
FUNK_GRID = [1, 3, 5, 7, 9, 11, 13, 15]

# (16th step, semitones above the root, velocity, length in 16ths)
SLAP = [
    (0,   0, 100, 3.0),   # thumb, hard on the one
    (2,   0,  34, 0.5),   # ghost
    (3,  12,  62, 1.0),
    (4,   0,  90, 2.0),
    (6,  12, 106, 1.2),   # pop
    (7,   0,  32, 0.5),   # ghost
    (8,   0,  94, 2.2),
    (10,  7,  98, 1.0),
    (11, 12,  58, 0.9),
    (13,  0,  34, 0.5),   # ghost
    (14, 12, 104, 1.4),   # pop
]


def role_funk_guitar(p: Part, c: Ctx) -> list[tuple]:
    """Chicken scratch. Muting the strings IS the part — short, quiet, and on
    the off-sixteenths, with the odd accent that lets a chord ring."""
    out = []
    grid = p.extra.get("grid", FUNK_GRID)
    accents = p.extra.get("accents", [3, 11])
    top = sorted(c.voicing)[-3:]        # upper voices; the low end belongs to the bass
    for step in grid:
        tick = int(step * DIV / 4) + c.rng.randint(-4, 4)
        accented = step in accents
        vel = (68 if accented else 46) + c.rng.randint(-5, 5)
        vel *= p.gain * c.level
        dur = int(DIV / 4 * (1.4 if accented else 0.55))
        for n in (top if accented else top[:2]):
            out.append((tick, n + 12 * p.octave, vel, dur))
    return out


def role_slap_bass(p: Part, c: Ctx) -> list[tuple]:
    """Syncopated slap: thumb on the root, pops an octave up, ghosts between."""
    out = []
    root = c.bass + 12 * p.octave
    for step, interval, vel, length in SLAP:
        tick = int(step * DIV / 4) + c.rng.randint(-3, 3)
        dur = max(1, int(DIV / 4 * length))
        out.append((tick, root + interval, vel * p.gain * c.level, dur))
    return out


def role_stab(p: Part, c: Ctx) -> list[tuple]:
    """Short chord hits. The space between them matters more than the hits."""
    steps = p.extra.get("steps", [2, 6, 10, 14])
    length = p.extra.get("len16", 1.4)
    base = p.extra.get("vel", 86)
    dur = max(1, int(DIV / 4 * length))
    out = []
    for i, step in enumerate(steps):
        tick = int(step * DIV / 4) + c.rng.randint(-3, 3)
        vel = (base + (6 if i == 0 else 0)) * p.gain * c.level
        for n in sorted(c.voicing):
            out.append((tick, n + 12 * p.octave, vel + c.rng.randint(-3, 3), dur))
    return out


ROLES = {
    "fingerpick": role_fingerpick,
    "strum": role_strum,
    "block": role_block,
    "bass_root5": role_bass_root5,
    "bass_walk": role_bass_walk,
    "arp": role_arp,
    "sparkle": role_sparkle,
    "melody": role_melody,
    "drums": role_drums,
    "funk_guitar": role_funk_guitar,
    "slap_bass": role_slap_bass,
    "stab": role_stab,
}


# ----------------------------------------------------------------- arrangement

class Arrangement:
    def __init__(self, bpm: float, key: str, mode: str, progression: list[str],
                 bars: int, sections=None, seed: int = 0, beats_per_bar: int = 4):
        self.bpm = float(bpm)
        self.key = theory.Key(key, mode)
        self.progression = progression
        self.bars = bars
        self.beats_per_bar = beats_per_bar
        self.seed = seed
        self.parts: list[Part] = []
        self.sections = sections or [(0, bars, 1.0)]
        self._voicings: dict = {}

    def duration(self) -> float:
        """Exact musical length in seconds, before reverb tail."""
        return self.bars * self.beats_per_bar * 60.0 / self.bpm

    def add(self, **kw) -> Part:
        p = Part(**kw)
        self.parts.append(p)
        return p

    # -- helpers
    def chord_at(self, bar: int) -> str:
        return self.progression[bar % len(self.progression)]

    def level_at(self, bar: int) -> float:
        for a, b, lvl in self.sections:
            if a <= bar < b:
                return lvl
        return self.sections[-1][2]

    def section_of(self, bar: int):
        for a, b, lvl in self.sections:
            if a <= bar < b:
                return a, b, lvl
        return self.sections[-1]

    def _chain(self, low, high, voices, rootless):
        """Voice-lead one continuous chain across every bar, once."""
        key = (low, high, voices, rootless)
        if key in self._voicings:
            return self._voicings[key]
        prev, chain = None, []
        for bar in range(self.bars):
            v = theory.voice_lead(self.key, self.chord_at(bar), prev,
                                  low=low, high=high, n_voices=voices,
                                  rootless=rootless)
            chain.append(v)
            prev = v
        self._voicings[key] = chain
        return chain

    def voicing_for(self, p: Part, bar: int) -> list[int]:
        if p.role == "drums":
            return []
        low, high = p.register or (55, 79)
        chain = self._chain(low, high, p.voices, p.rootless)
        return chain[bar]

    def bass_for(self, p: Part, bar: int) -> int:
        return _bass_note(self.key, self.chord_at(bar),
                          *(p.extra.get("bass_reg", (40, 52))))

    # -- render
    def build(self, only: int | None = None) -> Song:
        song = Song(self.bpm)
        chans = [c for c in range(16) if c != gm.DRUM_CHANNEL]
        items = list(enumerate(self.parts))
        if only is not None:
            items = [(only, self.parts[only])]
        for pi, p in items:
            ins = gm.drums() if p.role == "drums" else gm.Instrument.get(p.inst)
            is_drum = p.role == "drums"
            track = song.track(
                name=f"{p.inst}.{p.role}",
                channel=gm.DRUM_CHANNEL if is_drum else chans[pi % len(chans)],
                program=ins.program, volume=ins.volume,
                pan=ins.pan, reverb_send=ins.reverb,
            )
            rng = random.Random(hash((self.seed, pi, p.inst, p.role)) & 0xFFFFFFFF)
            end_bar = self.bars if p.end_bar is None else min(p.end_bar, self.bars)
            for bar in range(max(0, p.start_bar), end_bar):
                sec_a, sec_b, level = self.section_of(bar)
                ctx = Ctx(
                    key=self.key, bar=bar, chord=self.chord_at(bar),
                    voicing=self.voicing_for(p, bar),
                    bass=self.bass_for(p, bar) if p.role != "drums" else 36,
                    rng=rng, level=level,
                    next_chord=self.chord_at(bar + 1),
                    bars_into_section=bar - sec_a, section_len=sec_b - sec_a,
                )
                for tick, pitch, vel, dur in ROLES[p.role](p, ctx):
                    if vel <= 0:
                        continue
                    track.note(bar * 4 * DIV + tick, pitch, vel, dur)
        return song


def render_to(song: Song, mid_path: str) -> str:
    return song.write(mid_path)
