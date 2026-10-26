"""The composer: arrangements build into sane, deterministic performances."""
from __future__ import annotations

import random

import pytest

from band import presets
from band.compose import ROLES, Arrangement
from band.midi import DIV


def simple(**kw):
    kw.setdefault("bpm", 90)
    kw.setdefault("key", "D")
    kw.setdefault("mode", "major")
    kw.setdefault("progression", ["I", "V", "vi", "IV"])
    kw.setdefault("bars", 4)
    return Arrangement(**kw)


def notes_of(song):
    """Every note-on with velocity > 0, as (tick, channel, pitch, velocity)."""
    out = []
    for t in song.tracks:
        for tick, _, payload in sorted(t.events):
            if (payload[0] & 0xF0) == 0x90 and payload[2] > 0:
                out.append((tick, t.channel, payload[1], payload[2]))
    return out


def test_duration_matches_tempo():
    a = simple(bars=12, bpm=90)
    assert a.duration() == pytest.approx(32.0)
    assert simple(bars=1, bpm=120).duration() == pytest.approx(2.0)


def test_one_track_per_part():
    a = simple()
    a.add(inst="steel", role="fingerpick")
    a.add(inst="fingerbass", role="bass_root5")
    a.add(inst="drums", role="drums")
    song = a.build()
    assert len(song.tracks) == 3
    assert [t.name for t in song.tracks] == ["steel.fingerpick",
                                             "fingerbass.bass_root5",
                                             "drums.drums"]


def test_drums_land_on_channel_ten():
    a = simple()
    a.add(inst="steel", role="fingerpick")
    a.add(inst="drums", role="drums")
    song = a.build()
    drum_track = [t for t in song.tracks if t.name.endswith(".drums")][0]
    others = [t for t in song.tracks if not t.name.endswith(".drums")]
    assert drum_track.channel == 9
    assert all(t.channel != 9 for t in others)


def test_build_only_renders_one_part():
    a = simple()
    a.add(inst="steel", role="fingerpick")
    a.add(inst="fingerbass", role="bass_root5")
    assert len(a.build(only=0).tracks) == 1
    assert len(a.build(only=1).tracks) == 1
    assert len(a.build().tracks) == 2


def test_start_bar_is_respected():
    a = simple(bpm=84, bars=12)
    a.add(inst="drums", role="drums", start_bar=2, jitter=0)
    onset = min(t for t, _, _, _ in notes_of(a.build()))
    # a shaker sits a few ticks ahead of the beat by design, so allow that grace
    assert onset >= 2 * 4 * DIV - 8


def test_every_part_produces_notes():
    for name, (factory, _room) in presets.PRESETS.items():
        a = factory()
        for i, p in enumerate(a.parts):
            n = len(notes_of(a.build(only=i)))
            assert n > 0, f"{name}:{p.inst}.{p.role} produced no notes"


def test_notes_are_in_midi_range():
    a = presets.full_band()
    for _tick, _ch, pitch, vel in notes_of(a.build()):
        assert 0 <= pitch <= 127
        assert 1 <= vel <= 127


def test_parts_quieten_with_the_section_curve():
    """Sections exist to shape dynamics; a flat arrangement is the loudest
    tell of a machine, so verify the arc actually reaches the velocity data."""
    a = simple(bars=8, sections=[(0, 4, 0.3), (4, 8, 1.0)])
    a.add(inst="steel", role="fingerpick", jitter=0, howl=0)
    notes = notes_of(a.build())
    early = [v for t, _, _, v in notes if t < 4 * 4 * DIV]
    late = [v for t, _, _, v in notes if t >= 4 * 4 * DIV]
    assert early and late
    assert sum(late) / len(late) > sum(early) / len(early) * 2


def test_build_is_deterministic():
    a = simple(seed=5)
    a.add(inst="steel", role="fingerpick")
    a.add(inst="drums", role="drums")
    assert a.build().to_bytes() == a.build().to_bytes()


def test_different_seeds_differ():
    outs = []
    for seed in (1, 2):
        a = simple(seed=seed)
        a.add(inst="steel", role="fingerpick", jitter=6, howl=0.8)
        outs.append(a.build().to_bytes())
    assert outs[0] != outs[1]


def test_all_roles_are_registered_and_callable():
    assert set(ROLES) == {"fingerpick", "strum", "block", "bass_root5",
                          "bass_walk", "arp", "sparkle", "melody", "drums",
                          "funk_guitar", "slap_bass", "stab"}


@pytest.mark.parametrize("role,kw", [
    ("fingerpick", {"pattern": "travis"}),
    ("strum", {}),
    ("block", {}),
    ("bass_root5", {}),
    ("bass_walk", {}),
    ("arp", {"pattern": "arp_up"}),
    ("sparkle", {}),
    ("melody", {}),
    ("drums", {"extra": {"pattern": "boom_bap"}}),
    ("funk_guitar", {}),
    ("slap_bass", {}),
    ("stab", {}),
])
def test_each_role_produces_notes(role, kw):
    a = simple(bars=2)
    a.add(inst="steel", role=role, register=(52, 84), **kw)
    assert len(notes_of(a.build())) > 0


def test_unknown_role_fails_loudly():
    a = simple()
    a.add(inst="steel", role="nonsense")
    with pytest.raises(KeyError):
        a.build()


def test_melody_stays_in_its_register():
    a = simple(bars=6)
    a.add(inst="nylon", role="melody", register=(64, 81))
    pitches = [p for _, _, p, _ in notes_of(a.build())]
    assert min(pitches) >= 64
    assert max(pitches) <= 81
