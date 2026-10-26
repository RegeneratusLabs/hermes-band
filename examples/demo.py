#!/usr/bin/env python3
"""Render all three bundled arrangements, then measure them.

    python examples/demo.py            # writes out/{bed,band,pulse}/
    python examples/demo.py mydir
"""
from __future__ import annotations

import sys

from band import presets
from band.renderer import render

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"


def main() -> None:
    for name, (factory, room) in presets.PRESETS.items():
        r = render(factory(), f"{OUT}/{name}", room=room, lufs=-14.0, name=name)
        print(f"{name:6} {r['duration']:6.2f}s  musical {r['music_duration']:6.2f}s  "
              f"peak {r['peak_db']}  -> {r['mp3']}")


if __name__ == "__main__":
    main()
