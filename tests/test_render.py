"""End-to-end rendering. Skipped where fluidsynth or a soundfont is absent.

Run these on any machine that has audio set up:

    python -m pytest tests/test_render.py -v
"""
from __future__ import annotations

import os

import pytest

from band.compose import Arrangement
from band.renderer import ROOMS, render, sf2_available

has_audio = pytest.mark.skipif(
    not sf2_available(),
    reason="fluidsynth or the GM soundfont is not installed",
)


def two_bars():
    a = Arrangement(bpm=100, key="G", mode="major", bars=2,
                    progression=["I", "vi", "IV", "V"])
    a.add(inst="steel", role="fingerpick", register=(55, 79))
    a.add(inst="fingerbass", role="bass_root5", register=(40, 52))
    return a


def test_rooms_are_defined():
    assert set(ROOMS) == {"dry", "close", "room", "hall", "cathedral"}
    for cfg in ROOMS.values():
        assert cfg["rt60"] > 0 and 0 <= cfg["wet"] <= 1


@has_audio
def test_render_produces_exact_duration(tmp_path):
    a = two_bars()
    r = render(a, str(tmp_path), name="t", lufs=None, tail=0.0)
    assert os.path.exists(r["wav"])
    assert r["music_duration"] == pytest.approx(4.8)          # 2 bars at 100 BPM
    assert r["duration"] <= r["music_duration"] + 0.5


@has_audio
def test_render_does_not_clip(tmp_path):
    r = render(two_bars(), str(tmp_path), name="t", lufs=None)
    assert r["peak_db"] < 0.0


@has_audio
def test_render_hits_the_loudness_target(tmp_path):
    r = render(two_bars(), str(tmp_path), name="t", lufs=-16.0)
    assert -17.5 < _lufs(r["wav"]) < -14.5


@has_audio
def test_stems_are_written_per_part(tmp_path):
    r = render(two_bars(), str(tmp_path), name="t", lufs=None)
    assert r["stems"] == ["steel", "fingerbass"]
    wavs = [f for f in os.listdir(tmp_path) if f.endswith(".wav")]
    assert len(wavs) >= 3                                     # two stems + the mix


@has_audio
def test_render_is_reproducible(tmp_path):
    a = two_bars()
    first = render(a, str(tmp_path / "a"), name="t", lufs=None)
    second = render(two_bars(), str(tmp_path / "b"), name="t", lufs=None)
    assert first["peak_db"] == second["peak_db"]
    assert os.path.getsize(first["wav"]) == os.path.getsize(second["wav"])


def _lufs(path: str) -> float:
    import re
    import subprocess
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?\d+\.\d+) LUFS", r.stderr)
    return float(m[-1]) if m else 0.0
