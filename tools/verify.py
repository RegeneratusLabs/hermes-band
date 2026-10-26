#!/usr/bin/env python3
"""Verify a Hermes Band render: musical content, mix balance, master loudness.

Checks the things that are objectively wrong versus merely an opinion:
silent parts, buried parts, mud, mono collapse, clipping, wrong duration.

    python3 verify.py out/band/band.wav [arrangement]
"""
from __future__ import annotations

import os
import subprocess
import sys

import numpy as np

from band import master, mix


def db(x):
    return 20 * np.log10(max(float(x), 1e-12))


def band_split(mono, sr):
    S = np.abs(np.fft.rfft(mono)) ** 2
    f = np.fft.rfftfreq(len(mono), 1 / sr)
    tot = S.sum()
    out = {}
    for lo, hi, label in [(20, 60, "sub"), (60, 250, "bass"), (250, 2000, "mid"),
                          (2000, 8000, "presence"), (8000, 20000, "air")]:
        m = (f >= lo) & (f < hi)
        out[label] = round(100 * S[m].sum() / tot, 1)
    out["centroid_hz"] = int((f * S).sum() / tot)
    return out


def stem_balance(arr, workdir, name):
    """Post-mix level of each part: RMS and peak, relative to the summed bus.

    Peak matters for sparse parts — a mallet ping has a 28 dB crest factor, so
    judging it on RMS alone calls it buried when it is perfectly audible.
    """
    parts = []
    for i, p in enumerate(arr.parts):
        wav = os.path.join(workdir, f"{name}-{i:02d}-{p.inst}.wav")
        if not os.path.exists(wav):
            return None
        audio, sr = master.read_wav(wav)
        mono = audio.mean(axis=1)
        prof = mix.profile("drums" if p.role == "drums" else p.inst,
                           **(p.extra.get("mix") or {}))
        shaped = mix.shape(mono, sr, prof)
        shaped = mix.exciter(shaped, sr, amount=prof.get("air", 0) * 0.06)
        shaped = shaped * mix.db(prof["level"])
        parts.append((f"{p.inst}.{p.role}",
                      float(np.sqrt((shaped ** 2).mean())),
                      float(np.abs(shaped).max())))
    bus_rms = np.sqrt(sum(v ** 2 for _, v, _ in parts))
    bus_pk = max(pk for _, _, pk in parts)
    return [(n, round(db(v / bus_rms), 1), round(db(pk / bus_pk), 1))
            for n, v, pk in parts]


def lufs(path):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True)
    out, grab = {}, False
    for line in r.stderr.splitlines():
        if "Summary" in line:
            grab = True
        if grab and "I:" in line:
            out["lufs"] = float(line.split()[1])
        if grab and "Peak:" in line:
            out["true_peak_db"] = float(line.split()[1])
        if grab and "LRA:" in line:
            out["lra"] = float(line.split()[1])
    return out


def check(path, arr=None, workdir=None, name=None):
    audio, sr = master.read_wav(path)
    mono = audio.mean(axis=1)
    rep = {
        "file": path,
        "duration_s": round(len(audio) / sr, 2),
        "peak_dbfs": round(master.peak_db(audio), 2),
        "rms_dbfs": round(db(np.sqrt((mono ** 2).mean())), 2),
        "lr_balance_db": round(db(np.sqrt((audio[:, 0] ** 2).mean()))
                               - db(np.sqrt((audio[:, 1] ** 2).mean())), 2),
        "stereo_corr": round(float(np.corrcoef(audio[:, 0], audio[:, 1])[0, 1]), 3),
        "clipped_samples": int((np.abs(audio) > 0.999).sum()),
        "bands": band_split(mono, sr),
    }
    rep.update(lufs(path))
    w = int(sr * 0.1)
    win = np.abs(audio[: len(audio) // w * w]).reshape(-1, w, 2).max(axis=(1, 2))
    rep["silent_windows"] = int((win < 0.01).sum())
    rep["windows"] = len(win)
    if arr is not None:
        rep["musical_duration_s"] = round(arr.duration(), 2)
        rep["parts"] = stem_balance(arr, workdir, name) if workdir else None
        rep["notes"] = {}
        for i, p in enumerate(arr.parts):
            song = arr.build(only=i)
            n = sum(1 for t in song.tracks
                    for e in t.events if e[2][0] & 0xF0 == 0x90 and e[2][2] > 0)
            rep["notes"][f"{p.inst}.{p.role}"] = n
    return rep


def verdict(rep):
    """Flag objective problems, not taste."""
    issues = []
    b = rep["bands"]
    if rep["clipped_samples"]:
        issues.append(f"clipping: {rep['clipped_samples']} samples")
    if abs(rep["lr_balance_db"]) > 1.0:
        issues.append(f"L/R imbalance {rep['lr_balance_db']:+.1f} dB")
    if rep["stereo_corr"] > 0.97:
        issues.append("effectively mono")
    if b["bass"] > 45:
        issues.append(f"too much 60-250Hz ({b['bass']}%)")
    if b["presence"] < 5:
        issues.append(f"dull: only {b['presence']}% presence (2-8kHz)")
    if "lufs" in rep and rep["lufs"] < -16:
        issues.append(f"quiet: {rep['lufs']} LUFS")
    if rep.get("parts"):
        for name, rel_rms, rel_pk in rep["parts"]:
            if rel_pk < -30:
                issues.append(f"{name} inaudible (peak {rel_pk} dB under bus)")
            elif rel_rms < -26 and rel_pk < -18:
                issues.append(f"{name} buried (rms {rel_rms} / peak {rel_pk} dB)")
            elif rel_rms > -0.5:
                issues.append(f"{name} IS the bus ({rel_rms} dB)")
    return issues


if __name__ == "__main__":
    from demo import band, bed
    targets = {"bed": bed, "band": band}
    for path in sys.argv[1:]:
        base = os.path.basename(path).rsplit(".", 1)[0]
        arr = targets[base]() if base in targets else None
        rep = check(path, arr, os.path.dirname(path), base)
        print("\n".join(f"  {k:20} {v}" for k, v in rep.items()))
        issues = verdict(rep)
        print("  VERDICT:", "clean" if not issues else "; ".join(issues))
