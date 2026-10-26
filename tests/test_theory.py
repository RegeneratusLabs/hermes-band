"""Music theory: pitch math, roman numerals, voice leading.

These are the parts that must be exactly right — a wrong voicing or a misparsed
numeral produces music that is subtly, unfixably wrong downstream.
"""
from __future__ import annotations

import pytest

from band import theory


def test_note_roundtrip():
    # midi_to_note spells sharps only, so round-trip the sharp names
    for name in ["C4", "D4", "F#3", "A#2", "A4", "E1", "G9"]:
        assert theory.midi_to_note(theory.note_to_midi(name)) == name


def test_flats_are_accepted_but_spelled_as_sharps():
    assert theory.note_to_midi("Bb2") == theory.note_to_midi("A#2")
    assert theory.midi_to_note(theory.note_to_midi("Bb2")) == "A#2"


def test_note_values():
    assert theory.note_to_midi("C4") == 60
    assert theory.note_to_midi("A4") == 69
    assert theory.note_to_midi("C#4") == 61
    assert theory.note_to_midi("Db4") == 61
    assert theory.note_to_midi("C3") == 48


def test_concert_pitch():
    assert theory.midi_to_freq(69) == pytest.approx(440.0)
    assert theory.midi_to_freq(81) == pytest.approx(880.0)
    assert theory.midi_to_freq(60) == pytest.approx(261.63, abs=0.01)


def test_d_major_scale():
    k = theory.Key("D", "major")
    # range is inclusive at both ends, so stop one semitone short of the octave
    pcs = [p % 12 for p in k.scale_pitches(62, 73)]
    assert pcs == [2, 4, 6, 7, 9, 11, 1]          # D E F# G A B C#


def test_scale_pitches_are_inclusive_of_both_bounds():
    k = theory.Key("D", "major")
    ps = k.scale_pitches(62, 74)
    assert ps[0] == 62 and ps[-1] == 74            # D4 and D5, both present


def test_relative_minor_shares_its_notes():
    # A minor and C major are the same set of pitch classes
    a_min = {p % 12 for p in theory.Key("A", "minor").scale_pitches(57, 68)}
    c_maj = {p % 12 for p in theory.Key("C", "major").scale_pitches(48, 59)}
    assert a_min == c_maj


@pytest.mark.parametrize("sym,degree,acc,quality", [
    ("I", 1, 0, ""),
    ("vi", 6, 0, "m"),
    ("V7", 5, 0, "7"),
    ("bVII", 7, -1, ""),
    ("#iv", 4, 1, "m"),
    ("Imaj7", 1, 0, "maj7"),
    ("ii7", 2, 0, "7"),
])
def test_parse_roman(sym, degree, acc, quality):
    assert theory.parse_roman(sym) == (degree, acc, quality)


def test_bad_roman_raises():
    with pytest.raises(ValueError):
        theory.parse_roman("H")


def test_chord_quality_pcs():
    k = theory.Key("D", "major")
    assert sorted(theory.chord_pcs(k, "I")) == [2, 6, 9]        # D F# A
    assert sorted(theory.chord_pcs(k, "V")) == [1, 4, 9]        # A C# E
    assert sorted(theory.chord_pcs(k, "vi")) == [2, 6, 11]      # B D F#
    assert sorted(theory.chord_pcs(k, "IV")) == [2, 7, 11]      # G B D
    assert sorted(theory.chord_pcs(k, "V7")) == [1, 4, 7, 9]    # A C# E G


def test_chord_roots():
    k = theory.Key("D", "major")
    assert theory.chord_root(k, "I") == 2
    assert theory.chord_root(k, "bVII") == 0                    # C in D major
    assert theory.chord_root(k, "vi") == 11


def test_voice_leading_stays_in_register():
    k = theory.Key("D", "major")
    prev = None
    for sym in ["I", "V", "vi", "IV"] * 2:
        v = theory.voice_lead(k, sym, prev, low=55, high=79, n_voices=4)
        assert len(v) == 4
        assert min(v) >= 55 and max(v) <= 79
        assert v == sorted(v)
        prev = v


def test_first_voicing_puts_root_in_bass():
    k = theory.Key("D", "major")
    v = theory.voice_lead(k, "I", None, low=55, high=79, n_voices=4)
    assert v[0] % 12 == theory.chord_root(k, "I")


def test_voice_leading_keeps_common_tones():
    """I -> V shares the note A. A good voicing keeps it rather than jumping."""
    k = theory.Key("D", "major")
    a = theory.voice_lead(k, "I", None, low=55, high=79, n_voices=4)
    b = theory.voice_lead(k, "V", a, low=55, high=79, n_voices=4)
    shared = {p % 12 for p in a} & {p % 12 for p in b}
    assert shared == {9}                               # A held across the change
    total_motion = sum(abs(y - x) for x, y in zip(a, b))
    assert total_motion <= 14                          # average under 3.5 semitones/voice


def test_voicing_keeps_the_root_present():
    k = theory.Key("D", "major")
    prev = None
    for sym in ["I", "V", "vi", "IV"]:
        v = theory.voice_lead(k, sym, prev, low=55, high=79, n_voices=4)
        assert theory.chord_root(k, sym) in [p % 12 for p in v]
        prev = v
