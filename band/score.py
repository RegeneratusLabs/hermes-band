"""A song as data.

The score file is the contract the whole band depends on: each player writes one
part, the bandleader merges them, the renderer plays them. Everything downstream
is deterministic, so a score that renders well today renders identically forever.

    from band.score import load, save
    arr = load("scores/session-01.json")
    save(arr, "scores/session-01.json")
"""
from __future__ import annotations

import json
import os
from typing import Any

from . import drums, gm
from .compose import ROLES, Arrangement, Part
from .theory import SCALES, midi_to_note

SCORE_VERSION = 1

PART_FIELDS = ("inst", "role", "start_bar", "end_bar", "gain", "octave",
               "pattern", "swing", "jitter", "register", "voices",
               "rootless", "howl", "extra")

# Everything a score may name. Validating against these is what stops a bot
# inventing an instrument or a role that quietly renders nothing.
KNOWN_ROOMS = {"dry", "close", "room", "hall", "cathedral"}
KNOWN_PATTERNS = {"folk", "travis", "sparse", "arp_up", "rolling", "oompah"}


class ScoreError(ValueError):
    """A score that cannot be rendered as written."""


# --------------------------------------------------------------- conversions

def part_to_dict(p: Part) -> dict:
    d = {f: getattr(p, f) for f in PART_FIELDS}
    if d["register"] is not None:
        d["register"] = list(d["register"])
    return {k: v for k, v in d.items() if v is not None}


def part_from_dict(d: dict, where: str = "part") -> Part:
    unknown = set(d) - set(PART_FIELDS)
    if unknown:
        raise ScoreError(f"{where}: unknown field(s) {sorted(unknown)}. "
                         f"Allowed: {sorted(PART_FIELDS)}")
    kw: dict[str, Any] = dict(d)
    if "register" in kw and kw["register"] is not None:
        reg = kw["register"]
        if not (isinstance(reg, (list, tuple)) and len(reg) == 2):
            raise ScoreError(f"{where}: register must be [low, high], got {reg!r}")
        kw["register"] = tuple(int(x) for x in reg)
    if "extra" in kw and kw["extra"] is not None and not isinstance(kw["extra"], dict):
        raise ScoreError(f"{where}: extra must be an object")
    return Part(**kw)


def to_dict(arr: Arrangement, name: str | None = None) -> dict:
    return {
        "hermes_band": SCORE_VERSION,
        "name": name or "untitled",
        "bpm": arr.bpm,
        "key": midi_to_note(arr.key.tonic_midi),
        "mode": arr.key.mode,
        "tonic": arr.key.tonic_midi,
        "bars": arr.bars,
        "beats_per_bar": arr.beats_per_bar,
        "progression": list(arr.progression),
        "sections": [list(s) for s in arr.sections],
        "seed": arr.seed,
        "parts": [part_to_dict(p) for p in arr.parts],
    }


def from_dict(d: dict) -> Arrangement:
    validate(d)
    mode = d["mode"]
    tonic = d.get("tonic")
    key = _key_name_from_tonic(tonic) if tonic is not None else d["key"]
    arr = Arrangement(
        bpm=d["bpm"], key=key, mode=mode,
        progression=list(d["progression"]),
        bars=int(d["bars"]),
        beats_per_bar=int(d.get("beats_per_bar", 4)),
        sections=[tuple(s) for s in d["sections"]] if d.get("sections") else None,
        seed=int(d.get("seed", 0)),
    )
    for i, pd in enumerate(d["parts"]):
        arr.parts.append(part_from_dict(pd, f"parts[{i}] ({pd.get('inst')}.{pd.get('role')})"))
    return arr


def _key_name_from_tonic(midi: int) -> str:
    return midi_to_note(int(midi))


# --------------------------------------------------------------- validation

def validate(d: dict) -> None:
    """Fail loudly and early. A score that half-renders is worse than one that
    refuses, because silence looks like a mix problem."""
    if not isinstance(d, dict):
        raise ScoreError("score must be a JSON object")
    version = d.get("hermes_band")
    if version != SCORE_VERSION:
        raise ScoreError(f"hermes_band must be {SCORE_VERSION}, got {version!r}")

    for field in ("bpm", "mode", "bars", "progression"):
        if field not in d:
            raise ScoreError(f"missing required field {field!r}")

    if d["mode"] not in SCALES:
        raise ScoreError(f"unknown mode {d['mode']!r}. Known: {sorted(SCALES)}")
    if not (20 <= float(d["bpm"]) <= 300):
        raise ScoreError(f"bpm {d['bpm']!r} is outside 20-300")
    if int(d["bars"]) < 1:
        raise ScoreError("bars must be at least 1")

    prog = d["progression"]
    if not isinstance(prog, list) or not prog:
        raise ScoreError("progression must be a non-empty list of chord symbols")

    tone = d.get("tonic")
    if tone is None and "key" not in d:
        raise ScoreError("need either 'tonic' (midi number) or 'key' (note name)")

    # sections must tile the bar count without gaps
    sections = d.get("sections")
    if sections:
        total = 0
        for i, s in enumerate(sections):
            if not (isinstance(s, (list, tuple)) and len(s) == 3):
                raise ScoreError(f"sections[{i}] must be [start_bar, end_bar, level]")
            a, b, lvl = s
            if b <= a:
                raise ScoreError(f"sections[{i}] ends before it starts: {s!r}")
            if not (0.0 < float(lvl) <= 2.0):
                raise ScoreError(f"sections[{i}] level {lvl!r} must be in (0, 2]")
            total += b - a
        if total != int(d["bars"]):
            raise ScoreError(f"sections cover {total} bars but the score is {d['bars']}")

    parts = d.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ScoreError("parts must be a non-empty list")

    for i, p in enumerate(parts):
        where = f"parts[{i}]"
        if "inst" not in p or "role" not in p:
            raise ScoreError(f"{where}: needs both 'inst' and 'role'")
        unknown = set(p) - set(PART_FIELDS)
        if unknown:
            raise ScoreError(f"{where}: unknown field(s) {sorted(unknown)}. "
                             f"Allowed: {sorted(PART_FIELDS)}")
        inst, role = p["inst"], p["role"]
        where = f"parts[{i}] ({inst}.{role})"
        if inst != "drums" and inst not in gm.INSTRUMENTS:
            raise ScoreError(f"{where}: unknown instrument {inst!r}. "
                             f"Known: {sorted(gm.INSTRUMENTS)}")
        if role not in ROLES:
            raise ScoreError(f"{where}: unknown role {role!r}. Known: {sorted(ROLES)}")
        pat = p.get("pattern")
        if pat is not None and pat not in KNOWN_PATTERNS:
            raise ScoreError(f"{where}: unknown pattern {pat!r}. Known: {sorted(KNOWN_PATTERNS)}")
        extra = p.get("extra") or {}
        dpat = extra.get("pattern") if isinstance(extra, dict) else None
        if dpat is not None and dpat not in drums.PATTERNS:
            raise ScoreError(f"{where}: unknown drum pattern {dpat!r}. "
                             f"Known: {sorted(drums.PATTERNS)}")
        start = int(p.get("start_bar", 0))
        end = p.get("end_bar")
        if start < 0 or start >= int(d["bars"]):
            raise ScoreError(f"{where}: start_bar {start} is outside 0-{int(d['bars']) - 1}")
        if end is not None and not (start < int(end) <= int(d["bars"])):
            raise ScoreError(f"{where}: end_bar {end} must be > start_bar and <= {d['bars']}")
        reg = p.get("register")
        if reg is not None:
            lo, hi = reg
            if not (0 <= int(lo) < int(hi) <= 127):
                raise ScoreError(f"{where}: register {reg} must satisfy 0 <= low < high <= 127")


def validate_room(room: str) -> str:
    if room not in KNOWN_ROOMS:
        raise ScoreError(f"unknown room {room!r}. Known: {sorted(KNOWN_ROOMS)}")
    return room


# ------------------------------------------------------------------- io

def save(arr: Arrangement, path: str, name: str | None = None) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload = to_dict(arr, name=name or os.path.splitext(os.path.basename(path))[0])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    return path


def load(path: str) -> Arrangement:
    with open(path, "r", encoding="utf-8") as f:
        return from_dict(json.load(f))


def describe(d: dict) -> str:
    """One-line summary, for logs and the CLI."""
    parts = ", ".join(f"{p['inst']}.{p['role']}" for p in d["parts"])
    return (f"{d.get('name', 'untitled')}: {d['bars']} bars @ {d['bpm']} BPM, "
            f"{d['mode']}, {len(d['parts'])} parts ({parts})")
