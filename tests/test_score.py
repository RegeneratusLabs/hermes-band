"""Score files: the contract between a player, the bandleader and the renderer.

A score that half-renders is worse than one that refuses, because silence looks
like a mix problem. These tests pin the validation, not just the happy path.
"""
from __future__ import annotations

import json

import pytest

from band import presets, score
from band.score import ScoreError


def minimal(**over) -> dict:
    d = {
        "hermes_band": 1,
        "name": "t",
        "bpm": 104,
        "tonic": 64,
        "mode": "dorian",
        "bars": 4,
        "progression": ["im7", "IV7"],
        "seed": 1,
        "parts": [{"inst": "steel", "role": "fingerpick"}],
    }
    d.update(over)
    return d


# ------------------------------------------------------------------ roundtrip

def test_preset_roundtrip_is_lossless():
    a = presets.funk()
    d = score.to_dict(a, name="funk")
    b = score.from_dict(d)
    assert b.duration() == pytest.approx(a.duration())
    assert len(b.parts) == len(a.parts)
    assert [p.inst for p in b.parts] == [p.inst for p in a.parts]
    assert [p.role for p in b.parts] == [p.role for p in a.parts]


def test_roundtrip_renders_identical_bytes():
    """The whole point of a score: same file, same audio, forever."""
    a = presets.funk()
    b = score.from_dict(score.to_dict(a))
    assert a.build().to_bytes() == b.build().to_bytes()


def test_sections_and_registers_survive(tmp_path):
    a = presets.funk()
    path = score.save(a, str(tmp_path / "s.json"))
    b = score.load(path)
    assert b.sections == a.sections
    assert all(isinstance(p.register, tuple) or p.register is None for p in b.parts)


def test_save_writes_readable_json(tmp_path):
    path = score.save(presets.bed(), str(tmp_path / "bed.json"), name="bed")
    d = json.loads(open(path).read())
    assert d["hermes_band"] == 1
    assert d["name"] == "bed"
    assert isinstance(d["progression"], list)


def test_nested_extra_survives(tmp_path):
    a = presets.funk()
    b = score.load(score.save(a, str(tmp_path / "f.json")))
    clav = [p for p in b.parts if p.inst == "clav"][0]
    assert clav.extra["steps"] == [2, 6, 10, 14]
    brass = [p for p in b.parts if p.inst == "brass"][0]
    assert brass.extra["mix"]["send"] == 1.4
    assert brass.extra["vel"] == 78


# ----------------------------------------------------------------- validation

def test_minimal_score_is_valid():
    score.validate(minimal())


def test_version_is_enforced():
    with pytest.raises(ScoreError, match="hermes_band"):
        score.validate(minimal(hermes_band=99))


@pytest.mark.parametrize("field", ["bpm", "mode", "bars", "progression"])
def test_missing_required_fields_rejected(field):
    d = minimal()
    del d[field]
    with pytest.raises(ScoreError, match=field):
        score.validate(d)


def test_unknown_mode_rejected():
    with pytest.raises(ScoreError, match="mode"):
        score.validate(minimal(mode="funkytown"))


def test_tempo_bounds():
    with pytest.raises(ScoreError, match="bpm"):
        score.validate(minimal(bpm=5))
    with pytest.raises(ScoreError, match="bpm"):
        score.validate(minimal(bpm=999))


def test_unknown_instrument_rejected():
    with pytest.raises(ScoreError, match="instrument"):
        score.validate(minimal(parts=[{"inst": "kazoo", "role": "fingerpick"}]))


def test_unknown_role_rejected():
    with pytest.raises(ScoreError, match="role"):
        score.validate(minimal(parts=[{"inst": "steel", "role": "shred"}]))


def test_unknown_pattern_rejected():
    with pytest.raises(ScoreError, match="pattern"):
        score.validate(minimal(parts=[{"inst": "steel", "role": "fingerpick",
                                       "pattern": "djent"}]))


def test_unknown_drum_pattern_rejected():
    with pytest.raises(ScoreError, match="drum pattern"):
        score.validate(minimal(parts=[{"inst": "drums", "role": "drums",
                                       "extra": {"pattern": "blastbeat"}}]))


def test_unknown_part_field_rejected():
    with pytest.raises(ScoreError, match="unknown field"):
        score.validate(minimal(parts=[{"inst": "steel", "role": "fingerpick",
                                       "volume": 11}]))


def test_start_bar_outside_the_song_rejected():
    with pytest.raises(ScoreError, match="start_bar"):
        score.validate(minimal(parts=[{"inst": "steel", "role": "fingerpick",
                                       "start_bar": 9}]))


def test_end_bar_before_start_rejected():
    with pytest.raises(ScoreError, match="end_bar"):
        score.validate(minimal(parts=[{"inst": "steel", "role": "fingerpick",
                                       "start_bar": 2, "end_bar": 2}]))


def test_register_order_enforced():
    with pytest.raises(ScoreError, match="register"):
        score.validate(minimal(parts=[{"inst": "steel", "role": "fingerpick",
                                       "register": [80, 60]}]))


def test_sections_must_tile_the_song():
    with pytest.raises(ScoreError, match="sections cover"):
        score.validate(minimal(sections=[[0, 2, 1.0]]))          # only 2 of 4 bars


def test_sections_level_bounds():
    with pytest.raises(ScoreError, match="level"):
        score.validate(minimal(sections=[[0, 2, 0.0], [2, 4, 1.0]]))


def test_valid_sections_accepted():
    score.validate(minimal(sections=[[0, 2, 0.8], [2, 4, 1.0]]))


def test_room_validation():
    assert score.validate_room("hall") == "hall"
    with pytest.raises(ScoreError, match="room"):
        score.validate_room("cavern")


def test_describe_is_informative():
    text = score.describe(score.to_dict(presets.funk(), name="funk"))
    assert "funk" in text and "104" in text and "dorian" in text
