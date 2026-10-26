#!/usr/bin/env python3
"""Round four — the mix.

The players set their own faders and the sum came out wrong, because none of them
can hear it. This is where the bandleader earns the title: it gets the actual
measurements and makes the call.

    python session/mix_round.py session/runs/session-01
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BAND = os.path.join(REPO, ".venv/bin/hermes-band")
sys.path.insert(0, HERE)

from run import call_bot, log, read, write  # noqa: E402

# The band's own instrument -> which player owns that part
BACKING = {"drums": "sticks", "fingerbass": "lowend", "upright": "lowend",
           "clav": "clavinet", "rhodes": "clavinet", "organ": "clavinet",
           "muted_gtr": "scratch", "steel": "scratch", "nylon": "scratch",
           "clean_elec": "scratch"}

HEALTHY = """Healthy targets for a -14 LUFS master:
  60-250 Hz   25-35%   (current value above is the problem)
  250-2000 Hz 35-50%
  2-8 kHz     6% or more
  L/R balance within 1 dB
  stereo correlation 0.4-0.9
  spectral centroid 700-1100 Hz"""


def measure(wav: str) -> str:
    out = subprocess.run([BAND, "check", wav], capture_output=True, text=True).stdout
    keep = [ln for ln in out.splitlines()
            if any(k in ln for k in ("bands", "lufs", "true_peak", "lra",
                                     "lr_balance", "stereo_corr", "centroid"))]
    return "\n".join(keep)


def render(score_path: str, out_dir: str, room: str, name: str) -> tuple[str, str]:
    proc = subprocess.run([BAND, "play", score_path, "-o", out_dir, "--room", room],
                          capture_output=True, text=True)
    print(proc.stdout.strip() or proc.stderr.strip())
    wav = os.path.join(out_dir, name, f"{name}.wav")
    return wav, (measure(wav) if os.path.exists(wav) else "(no wav)")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: mix_round.py <run-dir>")
        return 2
    run_dir = sys.argv[1]
    score_path = os.path.join(run_dir, "score.json")
    score = json.loads(read(score_path))
    name = score["name"]

    before_wav = os.path.join(REPO, "out", name, f"{name}.wav")
    before = measure(before_wav) if os.path.exists(before_wav) else "(not rendered yet)"
    log("=== BEFORE ===")
    log(before)

    owners = {BACKING.get(p["inst"], "?"): [] for p in score["parts"]}
    for p in score["parts"]:
        owners.setdefault(BACKING.get(p["inst"], "?"), []).append(
            f'{p["inst"]}/{p["role"]}  extra.mix={p.get("extra", {}).get("mix", "{}")}')

    prompt = (
        "You are the bandleader. The tune is mixed and it is wrong.\n\n"
        f"You measured the render. Here is what came back:\n\n```\n{before}\n```\n\n"
        f"{HEALTHY}\n\n"
        "Here is every part in the arrangement, with the mix its player chose:\n\n"
        + "\n".join(f"### {who}\n" + "\n".join(f"- {line}" for line in lines)
                    for who, lines in owners.items() if lines)
        + "\n\nYOUR JOB\n"
        "Fix the balance. You control each part's mix override, which takes these "
        "keys: level (dB), low (low shelf dB), hp (high-pass Hz), lp (low-pass Hz), "
        "pres (presence dB), air (air dB), mud (bell cut dB around 330 Hz), "
        "pan (-1..1), send (reverb send).\n\n"
        "Do not drop anyone. Do not change what they play — only the balance.\n\n"
        f"Write valid JSON to exactly this path:\n  "
        f"{os.path.join(run_dir, 'parts', 'maestro-mix.json')}\n"
        'Shape: {"mix": {"sticks": {"key": value}, "lowend": {...}, ...}, '
        '"note": "one sentence on what you changed"}\n\n'
        "Then reply in 2-3 sentences: what was wrong and what you did.\n"
    )
    reply, _dt = call_bot("maestro", prompt, run_dir, "r4-maestro-mix")
    log("\n" + reply + "\n")

    mix_path = os.path.join(run_dir, "parts", "maestro-mix.json")
    try:
        verdict = json.loads(read(mix_path))
    except (OSError, json.JSONDecodeError):
        log("no usable mix verdict — leaving the balance alone")
        return 1

    applied = 0
    for p in score["parts"]:
        who = BACKING.get(p["inst"])
        override = (verdict.get("mix") or {}).get(who)
        if not override:
            continue
        p.setdefault("extra", {})
        merged = dict(p["extra"].get("mix") or {})
        merged.update(override)
        p["extra"]["mix"] = merged
        applied += 1
    log(f"applied mix overrides to {applied} parts")

    fixed_path = os.path.join(run_dir, "score-v2.json")
    score["name"] = f"{name}-mixed"
    write(fixed_path, json.dumps(score, indent=2) + "\n")
    wav, after = render(fixed_path, os.path.join(REPO, "out"), "close", score["name"])
    log("\n=== AFTER ===")
    log(after)

    write(os.path.join(run_dir, "mix-round.json"),
          json.dumps({"before": before, "after": after, "verdict": verdict,
                      "reply": reply, "score": fixed_path}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
