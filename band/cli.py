"""Command line entry point: `hermes-band doctor | demo | check`."""
from __future__ import annotations

import argparse
import os
import sys


def cmd_doctor(args) -> int:
    """Report whether this machine can actually make sound."""
    from . import renderer as render

    ok = True
    print("hermes-band doctor")
    print("-" * 46)
    try:
        import numpy
        print(f"  numpy          {numpy.__version__}")
    except ImportError:
        print("  numpy          MISSING  -> pip install numpy")
        ok = False

    fs = render.subprocess.run(["which", render.FLUIDSYNTH],
                               capture_output=True, text=True)
    if fs.returncode == 0:
        ver = render.subprocess.run([render.FLUIDSYNTH, "--version"],
                                    capture_output=True, text=True)
        line = (ver.stdout or ver.stderr).splitlines()[0].strip()
        print(f"  fluidsynth     {line}")
    else:
        print("  fluidsynth     MISSING  -> apt install fluidsynth fluid-soundfont-gm")
        ok = False

    sf = render.SOUNDFONT
    if os.path.exists(sf):
        mb = os.path.getsize(sf) / 1e6
        print(f"  soundfont      {sf}  ({mb:.0f} MB)")
    else:
        print(f"  soundfont      MISSING at {sf}")
        print("                 -> apt install fluid-soundfont-gm")
        print("                 -> or set HERMES_BAND_SF2 to another .sf2")
        ok = False

    print("-" * 46)
    print("  ready to render" if ok else "  not ready — fix the above")
    return 0 if ok else 1


def cmd_demo(args) -> int:
    from . import presets
    from .renderer import render

    names = args.tracks.split(",") if args.tracks else list(presets.PRESETS)
    for name in names:
        if name not in presets.PRESETS:
            print(f"unknown track {name!r}; choose from {sorted(presets.PRESETS)}")
            return 2
        factory, room = presets.PRESETS[name]
        arr = factory()
        r = render(arr, os.path.join(args.out, name), room=room,
                   lufs=args.lufs, name=name)
        print(f"{name:6} {r['duration']:6.2f}s  musical {r['music_duration']:6.2f}s  "
              f"peak {r['peak_db']}  -> {r['mp3']}")
    return 0


def cmd_check(args) -> int:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
    try:
        import verify  # lives in tools/
    except ImportError:
        print("tools/verify.py not found — run from a source checkout")
        return 2
    from . import presets

    by_name = {n: f for n, (f, _) in presets.PRESETS.items()}
    worst = 0
    for path in args.wav:
        base = os.path.basename(path).rsplit(".", 1)[0]
        arr = by_name[base]() if base in by_name else None
        rep = verify.check(path, arr, os.path.dirname(path), base)
        print("\n".join(f"  {k:20} {v}" for k, v in rep.items()))
        issues = verify.verdict(rep)
        print("  VERDICT:", "clean" if not issues else "; ".join(issues))
        worst = max(worst, 1 if issues else 0)
    return worst


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="hermes-band",
        description="Compose and render original music locally. No API, no model.")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="check fluidsynth + soundfont are installed")
    d.set_defaults(func=cmd_doctor)

    dm = sub.add_parser("demo", help="render the bundled arrangements")
    dm.add_argument("-o", "--out", default="out", help="output directory")
    dm.add_argument("-t", "--tracks", default=None,
                    help="comma separated: bed,band,pulse")
    dm.add_argument("--lufs", type=float, default=-14.0,
                    help="target loudness (default -14 for social)")
    dm.set_defaults(func=cmd_demo)

    ck = sub.add_parser("check", help="measure rendered wavs and flag problems")
    ck.add_argument("wav", nargs="+")
    ck.set_defaults(func=cmd_check)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
