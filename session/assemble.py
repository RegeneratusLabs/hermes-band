#!/usr/bin/env python3
"""Assemble the band: one Hermes Bot profile per player.

A Bot is just a profile, so this is the whole setup — create the profile, write
its SOUL.md, make sure the hermes-band skill is installed in it.

    python session/assemble.py --dry-run     # show what would happen
    python session/assemble.py               # do it
    python session/assemble.py --only sticks # one player
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

HOME = os.path.expanduser("~")
PROFILES = os.path.join(HOME, ".hermes", "profiles")
SKILL_SRC = os.path.join(HOME, ".hermes", "skills", "creative", "hermes-band")
HERE = os.path.dirname(os.path.abspath(__file__))

# profile name -> (title, persona file, one-line description)
BAND = {
    "maestro":  ("Bandleader", "maestro.md",
                 "Producer and arranger. Owns tempo, form, the mix and the render."),
    "sticks":   ("Drummer", "sticks.md",
                 "Pocket drummer. The one is sacred. Ghost notes are the feel."),
    "lowend":   ("Bassist", "lowend.md",
                 "Bass and drums are one instrument. Leaves holes on purpose."),
    "clavinet": ("Keys", "clavinet.md",
                 "Clavinet. One perfect stab beats eight notes."),
    "scratch":  ("Guitarist", "scratch.md",
                 "Chicken scratch and too many ideas. Needs telling to play less."),
}


def profile_path(name: str) -> str:
    return os.path.join(PROFILES, name)


def exists(name: str) -> bool:
    return os.path.exists(os.path.join(profile_path(name), "profile.yaml"))


def run(cmd: list[str], dry: bool) -> int:
    print("  $ " + " ".join(cmd))
    if dry:
        return 0
    return subprocess.run(cmd, capture_output=True, text=True).returncode


def create_profile(name: str, title: str, description: str, dry: bool) -> bool:
    """--clone brings the model config, .env (API keys) and the skill library."""
    if exists(name):
        print(f"[{name}] profile already exists — leaving it alone")
        return True
    print(f"[{name}] creating profile ({title})")
    rc = run(["hermes", "profile", "create", name, "--clone",
              "--description", f"{title} — {description}"], dry)
    if rc != 0:
        print(f"[{name}] create FAILED (exit {rc})")
        return False
    return True


def write_soul(name: str, persona_file: str, title: str, dry: bool) -> bool:
    src = os.path.join(HERE, "personas", persona_file)
    if not os.path.exists(src):
        print(f"[{name}] persona missing: {src}")
        return False
    body = open(src, encoding="utf-8").read()
    soul = (
        f"{body}\n\n"
        f"---\n\n"
        f"You are **{title}** in Hermes Band, a five-piece band of Hermes agents "
        f"that write and render original music together. Your bandmates are "
        f"maestro (bandleader), sticks (drums), lowend (bass), clavinet (keys) "
        f"and scratch (guitar).\n\n"
        f"Read the `hermes-band` skill before you write a part. When the "
        f"bandleader sends you a session brief, write your part to the file it "
        f"names and keep your reply short.\n"
    )
    dst = os.path.join(profile_path(name), "SOUL.md")
    print(f"[{name}] writing SOUL.md ({len(soul)} chars) -> {dst}")
    if not dry:
        os.makedirs(profile_path(name), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(soul)
    return True


def ensure_skill(name: str, dry: bool) -> bool:
    dst = os.path.join(profile_path(name), "skills", "creative", "hermes-band")
    if os.path.exists(os.path.join(dst, "SKILL.md")):
        print(f"[{name}] skill already installed")
        return True
    if not os.path.exists(SKILL_SRC):
        print(f"[{name}] WARNING: source skill missing at {SKILL_SRC}")
        return False
    print(f"[{name}] installing hermes-band skill")
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(SKILL_SRC, dst)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble the Hermes Band bots.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None, help="comma separated profile names")
    args = ap.parse_args()

    names = list(BAND) if not args.only else [n.strip() for n in args.only.split(",")]
    unknown = [n for n in names if n not in BAND]
    if unknown:
        print(f"unknown player(s): {unknown}. Known: {sorted(BAND)}")
        return 2

    ok = True
    for name in names:
        title, persona, desc = BAND[name]
        ok &= create_profile(name, title, desc, args.dry_run)
        if not exists(name) and not args.dry_run:
            print(f"[{name}] skipping SOUL/skill — profile was not created")
            ok = False
            continue
        ok &= write_soul(name, persona, title, args.dry_run)
        ok &= ensure_skill(name, args.dry_run)
        print()

    print("done" if ok else "finished with problems")
    if not args.dry_run:
        print("\nThe band now appears in the Desktop Bots tab "
              f"({', '.join(names)}).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
