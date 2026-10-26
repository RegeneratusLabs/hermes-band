"""Render backend: MIDI -> audio via fluidsynth + the mastering chain."""
from __future__ import annotations

import os
import subprocess

from . import master, mix, reverb

SOUNDFONT = os.environ.get(
    "HERMES_BAND_SF2", "/usr/share/sounds/sf2/FluidR3_GM.sf2")
FLUIDSYNTH = os.environ.get("HERMES_BAND_FLUIDSYNTH", "fluidsynth")


def sf2_available() -> bool:
    return os.path.exists(SOUNDFONT) and not subprocess.run(
        ["which", FLUIDSYNTH], capture_output=True).returncode


def render_midi(mid_path: str, wav_path: str, sr: int = 44100,
                trim_to: float | None = None) -> str:
    """Dry render — no fluidsynth reverb, we add our own.

    fluidsynth appends roughly ten seconds of silence to every file it writes,
    so `trim_to` cuts back to the musical length. That also means an arrangement
    has an exact, predictable duration — worth a lot when scoring to picture.
    """
    cmd = [
        FLUIDSYNTH, "-ni", "-F", wav_path, "-r", str(sr), "-O", "s16",
        "-o", "synth.reverb.active=0",
        "-o", "synth.chorus.active=0",
        "-o", "synth.gain=0.85",
        SOUNDFONT, mid_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(wav_path):
        raise RuntimeError(f"fluidsynth failed: {r.stderr[-800:]}")
    if trim_to:
        audio, rate = master.read_wav(wav_path)
        master.write_wav(wav_path, master.trim(audio, rate, trim_to), rate)
    return wav_path


ROOMS = {
    "dry":       dict(size=0.55, rt60=0.85, wet=0.14, bright=0.8),
    "close":     dict(size=0.8, rt60=1.4, wet=0.24, bright=0.95),
    "room":      dict(size=1.0, rt60=1.9, wet=0.30, bright=1.0),
    "hall":      dict(size=1.5, rt60=2.9, wet=0.38, bright=0.8),
    "cathedral": dict(size=2.2, rt60=4.2, wet=0.46, bright=0.7),
}


def mix_to_wav(dry_wav: str, out_wav: str, room: str = "room",
               lufs: float | None = None, seed: int = 0,
               trim_to: float | None = None, fade_in: float = 0.04,
               fade_out: float = 1.4, glue: float = 0.22) -> str:
    audio, sr = master.read_wav(dry_wav)
    cfg = ROOMS.get(room, ROOMS["room"])
    ir = reverb.make_ir(rt60=cfg["rt60"], size=cfg["size"],
                        bright=cfg["bright"], seed=seed, sr=sr)
    audio = reverb.apply_reverb(audio, ir, wet=cfg["wet"], sr=sr)
    audio = master.trim(audio, sr, trim_to)
    audio = master.dc_block(audio)
    audio = master.hp_filter(audio, sr, 34.0)
    audio = master.tilt_eq(audio, sr, low_gain_db=1.2, high_gain_db=1.4,
                           mud_db=-1.8, mud_hz=310.0)
    audio = master.saturate(audio, drive=1.5, mix=glue)
    audio = master.fade(audio, sr, fade_in=fade_in, fade_out=fade_out)
    audio = master.normalize_peak(audio, -3.2)
    master.write_wav(out_wav, audio, sr)
    if lufs is not None:
        master.loudnorm(out_wav, out_wav, lufs=lufs, tp=-1.0)
    return out_wav


def to_mp3(src: str, dst: str, bitrate="192k") -> str:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", src,
                    "-c:a", "libmp3lame", "-b:a", bitrate, "-ar", "44100", dst],
                   check=True)
    return dst


def render(arrangement, workdir: str, room: str = "room",
           lufs: float | None = -14.0, mp3: bool = True, name: str = "track",
           tail: float = 1.4) -> dict:
    """Full pipeline: compose -> stem per part -> fluidsynth -> mix -> master."""
    os.makedirs(workdir, exist_ok=True)
    music_dur = arrangement.duration()
    stems = []
    for i, p in enumerate(arrangement.parts):
        mid = os.path.join(workdir, f"{name}-{i:02d}-{p.inst}.mid")
        wav = os.path.join(workdir, f"{name}-{i:02d}-{p.inst}.wav")
        arrangement.build(only=i).write(mid)
        render_midi(mid, wav, trim_to=music_dur + 2.0)
        audio, sr = master.read_wav(wav)
        stem_name = "drums" if p.role == "drums" else p.inst
        stems.append((stem_name, audio, p.extra.get("mix")))
    dry, send = mix.mix_stems(stems, sr)
    audio = mix.finish(dry, send, sr, room=room, seed=arrangement.seed,
                       trim_to=music_dur + tail, fade_out=min(1.6, max(0.35, tail)))
    wet = os.path.join(workdir, f"{name}.wav")
    master.write_wav(wet, audio, sr)
    if lufs is not None:
        master.loudnorm(wet, wet, lufs=lufs, tp=-1.0)
    audio, sr = master.read_wav(wet)
    out = {"wav": wet, "music_duration": round(music_dur, 3),
           "duration": round(len(audio) / sr, 2),
           "peak_db": round(master.peak_db(audio), 2),
           "stems": [s[0] for s in stems]}
    if mp3:
        out["mp3"] = to_mp3(wet, os.path.join(workdir, f"{name}.mp3"))
    return out
