"""A dependency-free MIDI file writer.

Standard MIDI File, format 1, one track per instrument, 480 ticks per beat.
Written from scratch because pulling a 3MB library to emit four bytes of VLQ
is silly, and this way the whole engine runs on a bare python3.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DIV = 480


def _vlq(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative delta")
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


@dataclass
class Track:
    """One MIDI track. `events` holds (tick, order, bytes)."""
    name: str = ""
    channel: int = 0
    program: int = 0
    volume: int = 100        # CC7
    pan: int = 64            # CC10, 0=L 64=C 127=R
    reverb_send: int = 40    # CC91
    events: list = field(default_factory=list)

    def add(self, tick: float, data: bytes, order: int = 5) -> None:
        # jitter can push a first-beat note slightly negative; the file format
        # can't express that, and clamping sounds identical.
        self.events.append((max(0, int(round(tick))), order, data))

    def note(self, tick: float, pitch: int, velocity: int, dur: float) -> None:
        pitch = max(0, min(127, int(pitch)))
        velocity = max(1, min(127, int(round(velocity))))
        self.add(tick, bytes([0x90 | self.channel, pitch, velocity]), 5)
        self.add(tick + max(1, dur), bytes([0x80 | self.channel, pitch, 0]), 4)

    def cc(self, tick: float, controller: int, value: int) -> None:
        self.add(tick, bytes([0xB0 | self.channel, controller,
                              max(0, min(127, int(value)))]), 1)

    def bend(self, tick: float, semitones: float, bend_range: int = 2) -> None:
        """Pitch bend. Used sparingly for string/slide realism."""
        v = int(8192 + (semitones / bend_range) * 8192)
        v = max(0, min(16383, v))
        self.add(tick, bytes([0xE0 | self.channel, v & 0x7F, (v >> 7) & 0x7F]), 2)

    def _chunk(self, bpm: float, first: bool) -> bytes:
        ev = list(self.events)
        if first:
            us = int(60_000_000 / bpm)
            ev.append((0, -20, b"\xff\x51\x03" + us.to_bytes(3, "big")))
            if self.name:
                nb = self.name.encode()[:127]
                ev.append((0, -19, b"\xff\x03" + _vlq(len(nb)) + nb))
        ev.append((0, -18, bytes([0xC0 | self.channel, self.program])))
        ev.append((0, -17, bytes([0xB0 | self.channel, 7, self.volume])))
        ev.append((0, -16, bytes([0xB0 | self.channel, 10, self.pan])))
        ev.append((0, -15, bytes([0xB0 | self.channel, 91, self.reverb_send])))
        ev.append((0, -14, bytes([0xB0 | self.channel, 93, 0])))       # chorus off
        ev.sort(key=lambda e: (e[0], e[1]))
        data = bytearray()
        prev = 0
        for tick, _, payload in ev:
            data += _vlq(tick - prev) + payload
            prev = tick
        data += _vlq(0) + b"\xff\x2f\x00"
        return b"MTrk" + len(data).to_bytes(4, "big") + bytes(data)

    def last_tick(self) -> int:
        return max((e[0] for e in self.events), default=0)


class Song:
    def __init__(self, bpm: float = 90.0):
        self.bpm = float(bpm)
        self.tracks: list[Track] = []

    def track(self, **kw) -> Track:
        t = Track(**kw)
        t.channel = kw.get("channel", 0)
        self.tracks.append(t)
        return t

    def bar_ticks(self, beats: int = 4) -> int:
        return DIV * beats

    def to_bytes(self) -> bytes:
        body = b"".join(t._chunk(self.bpm, i == 0)
                        for i, t in enumerate(self.tracks))
        header = b"MThd" + (6).to_bytes(4, "big") + (1).to_bytes(2, "big") \
            + len(self.tracks).to_bytes(2, "big") + DIV.to_bytes(2, "big")
        return header + body

    def write(self, path: str) -> str:
        with open(path, "wb") as f:
            f.write(self.to_bytes())
        return path
