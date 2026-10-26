"""The MIDI writer. A malformed file is silent, so parse our own output back."""
from __future__ import annotations

import struct

from band.midi import DIV, Song, Track, _vlq


def parse_smf(data: bytes):
    """Minimal standard-midi-file reader, enough to prove the writer is valid."""
    assert data[:4] == b"MThd"
    hlen = struct.unpack(">I", data[4:8])[0]
    fmt, ntrks, div = struct.unpack(">HHH", data[8:8 + 6])
    assert hlen == 6
    pos = 8 + hlen
    tracks = []
    for _ in range(ntrks):
        assert data[pos:pos + 4] == b"MTrk"
        tlen = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        tracks.append(data[pos + 8:pos + 8 + tlen])
        pos += 8 + tlen
    assert pos == len(data), "trailing bytes after last track"
    return fmt, div, tracks


def read_events(track: bytes):
    """Yield (absolute_tick, status, data) for channel messages."""
    i = 0
    tick = 0
    out = []
    while i < len(track):
        delta = 0
        while True:
            b = track[i]
            i += 1
            delta = (delta << 7) | (b & 0x7F)
            if not b & 0x80:
                break
        tick += delta
        status = track[i]
        i += 1
        if status == 0xFF:
            mtype = track[i]
            i += 1
            ln = track[i]
            i += 1
            payload = track[i:i + ln]
            i += ln
            out.append((tick, "meta", mtype, payload))
            if mtype == 0x2F:
                break
        else:
            kind = status & 0xF0
            n = 2 if kind in (0x80, 0x90, 0xA0, 0xB0, 0xE0) else 1
            out.append((tick, kind, status & 0x0F, track[i:i + n]))
            i += n
    return out


def test_vlq_known_values():
    assert _vlq(0) == b"\x00"
    assert _vlq(0x40) == b"\x40"
    assert _vlq(0x7F) == b"\x7f"
    assert _vlq(0x80) == b"\x81\x00"
    assert _vlq(480) == b"\x83\x60"
    assert _vlq(15360) == b"\xf8\x00"


def test_header_is_valid():
    s = Song(bpm=90)
    s.track(name="lead", channel=0, program=25)
    fmt, div, tracks = parse_smf(s.to_bytes())
    assert fmt == 1
    assert div == DIV
    assert len(tracks) == 1


def test_note_on_and_off():
    s = Song(bpm=120)
    t = s.track(name="x", channel=0)
    t.note(0, 62, 100, 480)
    ev = read_events(parse_smf(s.to_bytes())[2][0])
    ons = [e for e in ev if e[1] == 0x90 and e[3][1] > 0]
    offs = [e for e in ev if e[1] == 0x80]
    assert len(ons) == 1 and ons[0][3][0] == 62 and ons[0][3][1] == 100
    assert len(offs) == 1 and offs[0][0] == 480


def test_negative_ticks_are_clamped():
    """Jitter can push a first-beat note before zero; the file format can't."""
    s = Song(bpm=90)
    t = s.track(name="x", channel=0)
    t.note(-40, 60, 90, 240)
    ev = read_events(parse_smf(s.to_bytes())[2][0])
    ons = [e for e in ev if e[1] == 0x90 and e[3][1] > 0]
    assert ons and ons[0][0] == 0


def test_events_are_time_ordered():
    s = Song(bpm=90)
    t = s.track(name="x", channel=0)
    for i, tick in enumerate([960, 0, 480, 1920]):
        t.note(tick, 60 + i, 80, 120)
    ticks = [e[0] for e in read_events(parse_smf(s.to_bytes())[2][0])
             if e[1] in (0x80, 0x90)]
    assert ticks == sorted(ticks)


def test_tempo_and_setup_events_written():
    s = Song(bpm=90)
    s.track(name="x", channel=0, program=25, volume=94, pan=44, reverb_send=38)
    ev = read_events(parse_smf(s.to_bytes())[2][0])
    tempo = [e for e in ev if e[1] == "meta" and e[2] == 0x51]
    assert tempo and int.from_bytes(tempo[0][3], "big") == int(60_000_000 / 90)
    progs = [e for e in ev if e[1] == 0xC0]
    assert progs and progs[0][3][0] == 25
    ccs = {e[3][0]: e[3][1] for e in ev if e[1] == 0xB0}
    assert ccs[7] == 94 and ccs[10] == 44 and ccs[91] == 38


def test_track_name_written():
    s = Song(bpm=90)
    s.track(name="steel.fingerpick", channel=0)
    ev = read_events(parse_smf(s.to_bytes())[2][0])
    names = [e[3] for e in ev if e[1] == "meta" and e[2] == 0x03]
    assert names == [b"steel.fingerpick"]


def test_pitch_and_velocity_are_clamped():
    s = Song(bpm=90)
    t = s.track(name="x", channel=0)
    t.note(0, 200, 400, 100)
    ev = read_events(parse_smf(s.to_bytes())[2][0])
    ons = [e for e in ev if e[1] == 0x90 and e[3][1] > 0]
    assert ons[0][3][0] == 127 and ons[0][3][1] == 127


def test_last_tick():
    t = Track(name="x")
    t.note(960, 60, 90, 240)
    assert t.last_tick() == 1200
