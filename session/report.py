#!/usr/bin/env python3
"""Turn a finished session into something readable.

    python session/report.py session/runs/session-01

Reads only what the run actually produced — parts, transcripts, score, render —
so the write-up cannot drift from the record.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLAYERS = ["sticks", "lowend", "clavinet", "scratch"]
LEADER = "maestro"
TITLES = {
    "maestro": "Bandleader",
    "sticks": "Drummer",
    "lowend": "Bassist",
    "clavinet": "Keys",
    "scratch": "Guitarist",
}


def read(path: str, default: str = "") -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return default


def load(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def part_summary(part: dict) -> str:
    bits = [f"`{part.get('inst')}` / `{part.get('role')}`"]
    for key in ("start_bar", "register", "gain", "pattern"):
        if part.get(key) is not None:
            bits.append(f"{key}={part[key]}")
    extra = part.get("extra") or {}
    for key in ("pattern", "steps", "grid", "quarters"):
        if key in extra:
            bits.append(f"{key}={extra[key]}")
    return ", ".join(bits)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: report.py <run-dir>")
        return 2
    run_dir = sys.argv[1]
    result = load(os.path.join(run_dir, "result.json")) or {}
    score = load(os.path.join(run_dir, "score.json")) or {}
    brief_path = os.path.join(HERE, "briefs", "funk-e-dorian.json")
    brief = load(brief_path) or {}

    L: list[str] = []
    add = L.append

    name = brief.get("name", os.path.basename(run_dir))
    add(f"# Hermes Band — {name}\n")
    add("Five Hermes agents were given one brief: make a funk record. Each one "
        "plays a single instrument. None of them can hear anything. This is the "
        "actual record of what they did.\n")

    add("## The brief\n")
    add("```")
    add(f"key         {brief.get('key')} {brief.get('mode')}")
    add(f"tempo       {brief.get('bpm')} BPM")
    add(f"form        {brief.get('bars')} bars, {brief.get('beats_per_bar', 4)}/4")
    add(f"progression {' | '.join(brief.get('progression', []))}")
    add("```\n")
    if brief.get("direction"):
        add(f"> {brief['direction']}\n")

    # ------------------------------------------------------------ round one
    add("## Round one — everyone writes blind\n")
    add("No player could see or hear the others. Each was told the chart, the "
        "vocabulary they were allowed to use, and to write one part.\n")
    for player in PLAYERS:
        data = load(os.path.join(run_dir, "parts", f"{player}.json"))
        reply = read(os.path.join(run_dir, "transcript", f"r1-{player}.reply.txt")).strip()
        if not data:
            add(f"### {TITLES[player]} (`{player}`) — sat this one out\n")
            continue
        add(f"### {TITLES[player]} (`{player}`)\n")
        for p in data.get("parts", []):
            add(f"- {part_summary(p)}")
        add("")
        comment = (data.get("comment") or "").strip()
        if comment:
            add(f"> {comment}\n")
        if reply:
            add(f"*{reply}*\n")

    # ------------------------------------------------------------ round two
    add("## Round two — the room\n")
    add("Each player was shown everyone else's part and their comments, and told "
        "to react honestly and either keep or revise their own.\n")
    for player in PLAYERS:
        reply = read(os.path.join(run_dir, "transcript", f"r2-{player}.reply.txt")).strip()
        if not reply:
            continue
        add(f"### {TITLES[player]}\n")
        add(f"{reply}\n")

    # ----------------------------------------------------------- round three
    verdict = load(os.path.join(run_dir, "parts", f"{LEADER}-verdict.json"))
    leader_reply = read(os.path.join(run_dir, "transcript", "r3-maestro.reply.txt")).strip()
    if verdict or leader_reply:
        add("## Round three — the bandleader calls it\n")
        if leader_reply:
            add(f"{leader_reply}\n")
        if isinstance(verdict, dict):
            kept = ", ".join(verdict.get("keep", []))
            add(f"**Kept:** {kept}\n")
            if verdict.get("note"):
                add(f"> {verdict['note']}\n")

    # --------------------------------------------------------------- record
    add("## The record\n")
    if result.get("render"):
        add("```")
        add(result["render"])
        add("```\n")
    chk = result.get("check") or ""
    for line in chk.splitlines():
        if any(k in line for k in ("lufs", "true_peak", "lr_balance", "stereo_corr",
                                   "bands", "lra", "VERDICT", "duration_s",
                                   "clipped")):
            add(f"- {line.strip()}")
    add("")

    if score.get("parts"):
        add("### Final score\n")
        add(f"{len(score['parts'])} parts, {score['bars']} bars at {score['bpm']} BPM "
            f"in {score.get('key')} {score.get('mode')}.\n")
        add("| player | part |")
        add("| --- | --- |")
        owner = {}
        for player in PLAYERS:
            data = load(os.path.join(run_dir, "parts", f"{player}.json")) or {}
            for p in data.get("parts", []):
                owner[f"{p.get('inst')}|{p.get('role')}"] = player
        for p in score["parts"]:
            who = owner.get(f"{p.get('inst')}|{p.get('role')}", "?")
            add(f"| {TITLES.get(who, who)} | {part_summary(p)} |")
        add("")

    # ---------------------------------------------------------------- method
    add("## How it works\n")
    add("Each player is a Hermes Bot — an isolated profile with its own SOUL.md, "
        "memory and skills. They share no context. The bandleader merges their "
        "parts into one score file, and the renderer plays it.\n")
    add("The music engine is deterministic: the score file *is* the song. "
        "Same file, same audio, every time — so the argument is preserved even "
        "though the performance is reproducible.\n")
    add("The implication worth sitting with: these agents produced a finished, "
        "mastered record without any of them being able to hear it. They worked "
        "from a chart, a vocabulary and their own opinions about how music "
        "should go.\n")

    timings = result.get("timings") or {}
    if timings:
        add("### Time on the clock\n")
        add("| player | turn time |")
        add("| --- | --- |")
        for k, v in timings.items():
            add(f"| {TITLES.get(k, k)} | {v:.0f}s |")
        add("")

    out = os.path.join(run_dir, "REPORT.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"wrote {out} ({len(L)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
