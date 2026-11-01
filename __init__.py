"""Hermes Band — Hermes plugin entry point.

Wraps the ``band`` engine (arrangement data -> fluidsynth -> mastered wav/mp3)
as model-callable tools. The engine itself is dependency-light (numpy) but the
audio backend needs the fluidsynth binary, a GM soundfont and ffmpeg on the
host; ``band_doctor`` reports exactly what is missing.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent
DEFAULT_SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
DEFAULT_FLUIDSYNTH = "fluidsynth"
KIT_HINT = "apt install fluidsynth fluid-soundfont-gm ffmpeg"

_PRESETS_SCHEMA_HINT = "bed | band | pulse | funk"


def _engine():
    """Import the engine lazily: the plugin must load (so band_doctor can
    explain a broken host) even when numpy or the audio backend is absent."""
    from . import band as engine

    return engine


def _slug(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", (name or "").strip()).strip("-._")
    return cleaned[:64] or "track"


def _out_root(ctx) -> Path:
    configured = str(ctx.get_config("output_dir", "") or "").strip()
    base = Path(configured).expanduser() if configured else Path.home() / "hermes-band-out"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _fluidsynth_version() -> str:
    binary = os.environ.get("HERMES_BAND_FLUIDSYNTH", DEFAULT_FLUIDSYNTH)
    path = shutil.which(binary)
    if not path:
        return ""
    done = subprocess.run([path, "--version"], capture_output=True, text=True, check=False)
    text = (done.stdout or done.stderr or "").strip().splitlines()
    return text[0].strip() if text else "present"


def _soundfont_path() -> str:
    return os.environ.get("HERMES_BAND_SF2", DEFAULT_SF2)


def _doctor(ctx) -> dict:
    checks: dict[str, object] = {}
    try:
        import numpy

        checks["numpy"] = numpy.__version__
    except ImportError:
        checks["numpy"] = ""

    checks["fluidsynth"] = _fluidsynth_version()

    sf2 = _soundfont_path()
    checks["soundfont"] = sf2 if os.path.exists(sf2) else ""
    checks["soundfont_mb"] = round(os.path.getsize(sf2) / 1e6) if os.path.exists(sf2) else 0

    ffmpeg = shutil.which("ffmpeg")
    checks["ffmpeg"] = ffmpeg or ""

    try:
        checks["output_dir"] = str(_out_root(ctx))
        checks["output_writable"] = os.access(checks["output_dir"], os.W_OK)
    except OSError as exc:
        checks["output_dir"] = ""
        checks["output_writable"] = False
        checks["output_error"] = str(exc)

    ready = bool(
        checks["numpy"]
        and checks["fluidsynth"]
        and checks["soundfont"]
        and checks["ffmpeg"]
        and checks["output_writable"]
    )
    return {
        "ready": ready,
        "checks": checks,
        "hint": "" if ready else KIT_HINT,
    }


def _presets() -> dict:
    return _engine().presets.PRESETS


def _score_payload(params: dict):
    """Return (score_dict, source_label) from the tool arguments."""
    score = params.get("score")
    if isinstance(score, dict):
        return score, "inline"
    path = str(params.get("score_path") or "").strip()
    if path:
        target = Path(path).expanduser()
        if not target.is_file():
            raise ValueError(f"score_path not found: {target}")
        return json.loads(target.read_text(encoding="utf-8")), str(target)
    return None, ""


def _handle_doctor(params, ctx, **_kwargs) -> str:
    return json.dumps(_doctor(ctx), indent=2)


def _handle_presets(params, ctx, **_kwargs) -> str:
    presets = _presets()
    return json.dumps(
        {
            "presets": [
                {"name": name, "room": room, "seconds": round(factory().duration(), 2)}
                for name, (factory, room) in presets.items()
            ],
            "rooms": sorted(_engine().ROOMS),
        },
        indent=2,
    )


def _handle_validate(params, ctx, **_kwargs) -> str:
    from .band import score as score_mod

    data, source = _score_payload(params)
    if data is None:
        return json.dumps({"success": False, "error": "pass 'score' (object) or 'score_path'"})
    try:
        score_mod.validate(data)
    except Exception as exc:  # noqa: BLE001 — the validator's message IS the answer
        return json.dumps({"success": False, "source": source, "error": str(exc)}, indent=2)
    return json.dumps(
        {
            "success": True,
            "source": source,
            "summary": score_mod.describe(data),
            "bars": data.get("bars"),
            "bpm": data.get("bpm"),
            "parts": len(data.get("parts") or []),
        },
        indent=2,
    )


def _handle_render(params, ctx, **_kwargs) -> str:
    engine = _engine()
    from .band import score as score_mod

    preset_name = str(params.get("preset") or "").strip()
    data, source = _score_payload(params)
    room = str(params.get("room") or "").strip()

    if data is not None:
        try:
            score_mod.validate(data)
        except Exception as exc:  # noqa: BLE001 — surfaced to the model verbatim
            return json.dumps({"success": False, "error": f"invalid score: {exc}"}, indent=2)
        arrangement = score_mod.from_dict(data)
        name = _slug(str(params.get("name") or data.get("name") or "track"))
    elif preset_name:
        preset = _presets().get(preset_name)
        if preset is None:
            return json.dumps(
                {"success": False, "error": f"unknown preset {preset_name!r}; choose {_PRESETS_SCHEMA_HINT}"}
            )
        factory, preset_room = preset
        arrangement = factory()
        name = _slug(preset_name)
        room = room or preset_room
        source = f"preset:{preset_name}"
    else:
        return json.dumps({"success": False, "error": "pass 'score'/'score_path' or 'preset'"})

    room = score_mod.validate_room(room or "room")
    lufs = params.get("lufs")
    lufs = -14.0 if lufs is None else float(lufs)
    mp3 = bool(params.get("mp3", True))

    workdir = _out_root(ctx) / name
    try:
        result = engine.render(
            arrangement, str(workdir), room=room, lufs=lufs, mp3=mp3, name=name
        )
    except Exception as exc:  # noqa: BLE001 — render failures must not kill the turn
        return json.dumps(
            {
                "success": False,
                "error": f"{type(exc).__name__}: {exc}",
                "hint": KIT_HINT,
                "doctor": _doctor(ctx),
            },
            indent=2,
        )

    return json.dumps(
        {
            "success": True,
            "source": source,
            "name": name,
            "room": room,
            "lufs": lufs,
            "wav": result["wav"],
            "mp3": result.get("mp3", ""),
            "duration": result["duration"],
            "music_duration": result["music_duration"],
            "peak_db": result["peak_db"],
            "stems": result["stems"],
        },
        indent=2,
    )


TOOLS = (
    (
        "band_doctor",
        _handle_doctor,
        "Check whether this host can render audio: numpy, the fluidsynth binary, the GM "
        "soundfont, ffmpeg and the output directory. Run this before the first render.",
        {"type": "object", "properties": {}},
    ),
    (
        "band_list_presets",
        _handle_presets,
        "List the bundled arrangements (bed, band, pulse, funk) with their default room and "
        "length in seconds, plus the available reverb rooms.",
        {"type": "object", "properties": {}},
    ),
    (
        "band_validate_score",
        _handle_validate,
        "Validate a score (inline object or a path) without rendering: instruments, roles, "
        "patterns, registers, tempo and bar counts. Returns a one-line summary.",
        {
            "type": "object",
            "properties": {
                "score": {"type": "object", "description": "Score object (hermes_band schema)."},
                "score_path": {"type": "string", "description": "Path to a score JSON file."},
            },
        },
    ),
    (
        "band_render",
        _handle_render,
        "Render original music locally: pass a score (inline or a path) or a preset name. Writes "
        "wav + mp3 into <output_dir>/<name>/ and returns their paths, exact duration and peak level. "
        "Deterministic — the same score always renders the same audio.",
        {
            "type": "object",
            "properties": {
                "score": {"type": "object", "description": "Score object (hermes_band schema)."},
                "score_path": {"type": "string", "description": "Path to a score JSON file."},
                "preset": {"type": "string", "description": _PRESETS_SCHEMA_HINT},
                "name": {"type": "string", "description": "Track name (output subdirectory)."},
                "room": {
                    "type": "string",
                    "enum": ["dry", "close", "room", "hall", "cathedral"],
                    "description": "Reverb room. Default: the preset's own, else 'room'.",
                },
                "lufs": {
                    "type": "number",
                    "description": "Target loudness, default -14 (social/video). Use null to skip loudness normalisation.",
                },
                "mp3": {"type": "boolean", "description": "Also write an mp3 (default true)."},
            },
        },
    ),
)


def register(ctx):
    for name, handler, description, parameters in TOOLS:
        ctx.register_tool(
            name=name,
            toolset="band",
            schema={"name": name, "description": description, "parameters": parameters},
            handler=(lambda h: (lambda params, **kwargs: h(params, ctx, **kwargs)))(handler),
        )

    skill_path = PLUGIN_DIR / "skill" / "SKILL.md"
    if skill_path.exists():
        ctx.register_skill("hermes-band", skill_path)
