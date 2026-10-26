"""Hermes Band — compose and render original music locally, no music API.

    from band import Arrangement, render

    arr = Arrangement(bpm=90, key="D", mode="major",
                      progression=["I", "V", "vi", "IV"], bars=12)
    arr.add(inst="steel", role="fingerpick", pattern="folk")
    arr.add(inst="fingerbass", role="bass_root5", start_bar=2)
    print(render(arr, "out/mine", room="room", name="mine"))
"""
from . import presets  # noqa: F401
from .compose import ROLES, Arrangement, Part  # noqa: F401
from .renderer import (ROOMS, mix_to_wav, render,  # noqa: F401
                       render_midi, to_mp3)
from .theory import SCALES, Key, midi_to_freq, midi_to_note, note_to_midi  # noqa: F401

__version__ = "0.1.0"
__all__ = [
    "Arrangement", "Part", "ROLES", "presets",
    "render", "render_midi", "mix_to_wav", "to_mp3", "ROOMS",
    "Key", "SCALES", "note_to_midi", "midi_to_note", "midi_to_freq",
]
