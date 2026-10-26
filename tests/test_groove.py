"""Rhythm intent. Funk is a timing problem, not a note problem.

These tests assert *where* notes land and how hard, because a funk groove that
is technically playing the right chords but lands on the wrong sixteenths is
worse than no groove at all.
"""
from __future__ import annotations

from band import drums as dr
from band import gm, presets
from band.compose import Arrangement
from band.midi import DIV

BAR = 4 * DIV
STEP = DIV // 4          # one sixteenth


def notes(song, track_index=0, bar=0):
    out = []
    for tick, _, payload in sorted(song.tracks[track_index].events):
        if (payload[0] & 0xF0) == 0x90 and payload[2] > 0:
            if bar is None or 0 <= tick < BAR * (bar + 1):
                out.append((tick, payload[1], payload[2]))
    return out


def steps_of(events):
    """Round each tick to its 16th-note step, allowing for humanisation."""
    return sorted({int(round(t / STEP)) % 16 for t, _, _ in events})


def by_velocity(pattern):
    return {step: v for step, v in pattern}


# ------------------------------------------------------------------ patterns

def test_every_pattern_fits_sixteen_steps():
    for name, pattern in dr.PATTERNS.items():
        for voice, hits in pattern.items():
            steps = [s for s, _ in hits]
            assert min(steps) >= 0 and max(steps) <= 15, f"{name}/{voice} escapes the bar"


def test_funk_kick_lands_hard_on_the_one():
    kick = by_velocity(dr.FUNK[gm.KICK])
    assert 0 in kick, "no kick on the downbeat — that's not funk"
    assert kick[0] == max(kick.values()), "the one must be the hardest kick in the bar"


def test_funk_kick_is_syncopated_not_four_on_the_floor():
    steps = [s for s, _ in dr.FUNK[gm.KICK]]
    assert 0 in steps
    assert steps != [0, 4, 8, 12], "four-on-the-floor is disco, not funk"
    assert len(steps) >= 3


def test_funk_snare_has_backbeats_and_ghosts():
    snare = by_velocity(dr.FUNK[gm.SNARE])
    assert 4 in snare and 12 in snare, "backbeat missing"
    ghosts = [s for s, v in snare.items() if v < max(snare.values()) * 0.6]
    assert len(ghosts) >= 4, "ghost notes are the feel; without them it's a metronome"
    assert max(snare.values()) > min(snare.values()) * 2


def test_funk_hats_are_sixteenths():
    hats = steps_of([(s * STEP, gm.HH, 80) for s, _ in dr.FUNK[gm.HH]])
    assert hats == list(range(16)) or len(hats) >= 12


# --------------------------------------------------------------------- roles

def one_bar(role, **kw):
    a = Arrangement(bpm=104, key="E", mode="dorian", bars=1,
                    progression=["im7"], sections=[(0, 1, 1.0)], seed=3)
    inst = kw.pop("inst", "muted_gtr")
    register = kw.pop("register", (52, 76))
    a.add(inst=inst, role=role, register=register, **kw)
    return notes(a.build())


def test_funk_guitar_sits_on_the_off_sixteenths():
    """"e" and "a" of each beat. On the beat it's a strum, not a scratch."""
    steps = steps_of(one_bar("funk_guitar"))
    assert steps, "no notes"
    assert all(s % 2 == 1 for s in steps), f"scratch landed on a beat: {steps}"


def test_funk_guitar_notes_are_short_and_quiet():
    ev = one_bar("funk_guitar")
    assert max(v for _, _, v in ev) < 90, "scratch should not be a full strum"


def test_slap_bass_has_ghost_notes():
    ev = one_bar("slap_bass", inst="fingerbass", register=(33, 45))
    assert any(v < 50 for _, _, v in ev), "no ghost notes — this will sound stiff"
    assert max(v for _, _, v in ev) > 80


def test_slap_bass_covers_octaves():
    ev = one_bar("slap_bass", inst="fingerbass", register=(33, 45))
    pitches = {p for _, p, _ in ev}
    assert len(pitches) >= 3, "slap needs root, octave and fifth at least"


def test_stab_leaves_space():
    ev = one_bar("stab", inst="clav", extra={"steps": [2, 6, 10, 14]})
    steps = steps_of(ev)
    assert len(steps) == 4, "stabs are meant to be sparse"
    assert 0 not in steps, "a stab on the one fights the kick"


# -------------------------------------------------------------------- preset

def test_funk_preset_is_structurally_sound():
    a = presets.funk()
    assert a.key.mode == "dorian"
    assert a.bars == 16
    song = a.build()
    assert len(song.tracks) == len(a.parts)
    for i in range(len(a.parts)):
        assert notes(song, i, bar=None), f"{a.parts[i].inst} produced nothing"


def test_funk_preset_stages_its_entrances():
    """Nothing should arrive all at once — that's the clearest machine tell."""
    a = presets.funk()
    starts = {p.inst: p.start_bar for p in a.parts}
    assert starts["drums"] == 0 and starts["fingerbass"] == 0
    assert starts["clav"] > 0
    assert starts["brass"] > starts["clav"]


def test_funk_preset_stays_in_its_lane_harmonically():
    """E dorian: Em7 and A7 must be the plain diatonic chords, not borrowed."""
    from band import theory
    a = presets.funk()
    assert sorted(theory.chord_pcs(a.key, "im7")) == [2, 4, 7, 11]    # E G B D
    assert sorted(theory.chord_pcs(a.key, "IV7")) == [1, 4, 7, 9]     # A C# E G
