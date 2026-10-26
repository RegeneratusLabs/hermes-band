"""Music theory: notes, scales, roman-numeral chords, voice leading.

No dependencies. All pitch math is integer MIDI note numbers.
"""
from __future__ import annotations

PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
PC_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Semitone offsets from the tonic.
SCALES = {
    "major":            [0, 2, 4, 5, 7, 9, 11],
    "ionian":           [0, 2, 4, 5, 7, 9, 11],
    "minor":            [0, 2, 3, 5, 7, 8, 10],
    "aeolian":          [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor":   [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor":    [0, 2, 3, 5, 7, 9, 11],
    "dorian":           [0, 2, 3, 5, 7, 9, 10],
    "phrygian":         [0, 1, 3, 5, 7, 8, 10],
    "lydian":           [0, 2, 4, 6, 7, 9, 11],
    "mixolydian":       [0, 2, 4, 5, 7, 9, 10],
    "locrian":          [0, 1, 3, 5, 6, 8, 10],
    "major_pentatonic": [0, 2, 4, 7, 9],
    "minor_pentatonic": [0, 3, 5, 7, 10],
    "blues":            [0, 3, 5, 6, 7, 10],
}

# Chord quality -> semitone stack above the root.
QUALITIES = {
    "":      [0, 4, 7],
    "maj":   [0, 4, 7],
    "min":   [0, 3, 7],
    "m":     [0, 3, 7],
    "dim":   [0, 3, 6],
    "aug":   [0, 4, 8],
    "sus2":  [0, 2, 7],
    "sus4":  [0, 5, 7],
    "5":     [0, 7],
    "6":     [0, 4, 7, 9],
    "m6":    [0, 3, 7, 9],
    "7":     [0, 4, 7, 10],
    "maj7":  [0, 4, 7, 11],
    "m7":    [0, 3, 7, 10],
    "mmaj7": [0, 3, 7, 11],
    "dim7":  [0, 3, 6, 9],
    "m7b5":  [0, 3, 6, 10],
    "add9":  [0, 4, 7, 14],
    "madd9": [0, 3, 7, 14],
    "9":     [0, 4, 7, 10, 14],
    "maj9":  [0, 4, 7, 11, 14],
    "m9":    [0, 3, 7, 10, 14],
}


def note_to_midi(name: str) -> int:
    """'D4' -> 62, 'F#3' -> 54, 'Bb2' -> 46. C4 = 60."""
    s = name.strip()
    i = 1
    if len(s) > 1 and s[1] in "#b":
        i = 2
    pc = PC[s[0].upper()]
    if i == 2:
        pc += 1 if s[1] == "#" else -1
    octave = int(s[i:])
    return pc + 12 * (octave + 1)


def midi_to_note(n: int) -> str:
    return f"{PC_NAMES[n % 12]}{n // 12 - 1}"


def midi_to_freq(n) -> float:
    import math
    return 440.0 * 2.0 ** ((n - 69) / 12.0)


class Key:
    """A tonic + mode, and the diatonic vocabulary that comes from it."""

    def __init__(self, tonic: str, mode: str = "major"):
        self.tonic_midi = note_to_midi(tonic if tonic[-1].isdigit() else tonic + "4")
        self.tonic_pc = self.tonic_midi % 12
        if mode not in SCALES:
            raise ValueError(f"unknown mode {mode!r}; try one of {sorted(SCALES)}")
        self.mode = mode
        self.intervals = SCALES[mode]

    def degree_pitch(self, degree: int, accidental: int = 0) -> int:
        """Scale degree 1..7 (or 8) -> pitch class. Accidental in semitones."""
        n = len(self.intervals)
        d = (degree - 1) % n
        octave_lift = 12 * ((degree - 1) // n)
        return (self.tonic_pc + self.intervals[d] + accidental + octave_lift) % 12

    def scale_pitches(self, low: int, high: int) -> list[int]:
        """Every pitch of the scale inside [low, high]."""
        out, n = [], len(self.intervals)
        for oct_base in range(-1, 11):
            for iv in self.intervals:
                p = self.tonic_pc + iv + 12 * oct_base
                if low <= p <= high:
                    out.append(p)
        return sorted(set(out))

    def diatonic_chord_pcs(self, degree: int, sizes: int = 3) -> list[int]:
        """Stack scale degrees (1-3-5-7...) to get the key's own chord."""
        n = len(self.intervals)
        return [self.degree_pitch(degree + 2 * k) for k in range(sizes)]


ROMAN_BASE = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}


def parse_roman(sym: str):
    """'bVII7' -> (degree=7, accidental=-1, quality='7', diatonic_minor=True).

    Case carries quality when no explicit suffix is given:
    uppercase = major triad, lowercase = minor triad.
    """
    s = sym.strip()
    acc = 0
    while s and s[0] in "#b":
        acc += 1 if s[0] == "#" else -1
        s = s[1:]
    core = s.rstrip("°+oø")
    dim = "°" in s or s.endswith("o")
    aug = "+" in s
    half = "ø" in s
    if half:
        core = core.rstrip("ø")
    letters = "".join(c for c in core if c.isalpha() and c.upper() in "IV")
    suffix = core[len(letters):]
    upper = letters.isupper()
    degree = ROMAN_BASE.get(letters.upper())
    if degree is None:
        raise ValueError(f"bad roman numeral {sym!r}")
    if suffix:
        quality = suffix
    elif dim:
        quality = "dim7" if "7" in s else "dim"
    elif half:
        quality = "m7b5"
    elif aug:
        quality = "aug"
    else:
        quality = "" if upper else "m"
    return degree, acc, quality


def chord_pcs(key: Key, sym: str) -> list[int]:
    degree, acc, quality = parse_roman(sym)
    if quality not in QUALITIES:
        raise ValueError(f"unknown quality {quality!r} in {sym!r}")
    root = key.degree_pitch(degree, acc)
    return sorted({(root + iv) % 12 for iv in QUALITIES[quality]})


def chord_root(key: Key, sym: str) -> int:
    degree, acc, _ = parse_roman(sym)
    return key.degree_pitch(degree, acc)


# ---------------------------------------------------------------- voice leading

def voice_lead(key: Key, sym: str, prev: list[int] | None,
               low: int = 55, high: int = 79, n_voices: int = 4,
               rootless: bool = False) -> list[int]:
    """Pick the inversion/octave placement that moves least from `prev`.

    This is the difference between a chord progression that sounds composed and
    one that sounds like a MIDI demo: keep common tones, step the rest.
    """
    pcs = chord_pcs(key, sym)
    root = chord_root(key, sym)
    if rootless and len(pcs) > 3:
        pcs = [p for p in pcs if p != root]
    if len(pcs) > n_voices:
        pcs = pcs[:n_voices]
    best, best_score = None, None
    for inv in range(len(pcs)):
        rotated = pcs[inv:] + pcs[:inv]
        for base_oct in range(2, 7):
            voicing = []
            for j, pc in enumerate(rotated):
                target = 12 * base_oct + pc
                # stack each subsequent voice above the previous one, close position
                while voicing and target <= voicing[-1]:
                    target += 12
                voicing.append(target)
            # pad to the required voice count by doubling — root first, upwards
            while len(voicing) < n_voices:
                done = False
                root_voices = [v for v in voicing if v % 12 == root]
                for v in root_voices + sorted(voicing, reverse=True):
                    if v + 12 <= high:
                        voicing.append(v + 12)
                        done = True
                        break
                if not done:
                    for v in sorted(voicing):
                        if v - 12 >= low:
                            voicing.insert(0, v - 12)
                            done = True
                            break
                if not done:
                    break
            voicing = sorted(voicing)
            if min(voicing) < low or max(voicing) > high:
                continue
            score = 0.0
            if voicing[0] % 12 == root:                    # root in the bass = clear harmony
                score -= 3.0
            if root not in [v % 12 for v in voicing]:      # don't voice out the root
                score += 7.0
            score += 0.02 * (max(voicing) - min(voicing))  # prefer a tight, warm spread
            if prev:
                score += sum(abs(a - min(prev, key=lambda p: abs(p - a))) for a in voicing)
                score += 0.35 * sum(abs(a - b) for a, b in zip(sorted(voicing), sorted(prev)))
            else:
                score += 0.5 * abs(min(voicing) - low)     # open near the bottom of the window
                score += 4.0 * inv                         # first chord: root position
            if best_score is None or score < best_score:
                best, best_score = voicing, score
    return best or [root + 12 * 4]
