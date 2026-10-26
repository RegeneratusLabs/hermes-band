#!/usr/bin/env python3
"""Convene the band. Three rounds, then a render.

Round 1  each player writes a part, blind, from the brief
Round 2  each player reads the others and may revise — this is where they argue
Round 3  the bandleader keeps or drops parts, then the runner renders

Every prompt and every reply is written to runs/<run>/transcript/. Nothing is
paraphrased: the record is the actual turns.

    python session/run.py --brief session/briefs/funk-e-dorian.json
    python session/run.py --brief ... --rounds 1 --only sticks   # smoke test
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HERMES = os.path.expanduser("~/.local/bin/hermes")
if not os.path.exists(HERMES):
    HERMES = "hermes"

PLAYERS = ["sticks", "lowend", "clavinet", "scratch"]
LEADER = "maestro"
ORDER = [LEADER] + PLAYERS

# What each player is allowed to reach for. Mirrors session/CONTRACT.md.
ALLOWED = {
    "sticks":   {"drums"},
    "lowend":   {"fingerbass", "upright"},
    "clavinet": {"clav", "rhodes", "organ"},
    "scratch":  {"muted_gtr", "steel", "nylon", "clean_elec"},
}


def log(msg: str) -> None:
    print(msg, flush=True)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path: str, body: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)


def brief_block(brief: dict) -> str:
    prog = " | ".join(brief["progression"])
    secs = ", ".join(f"bars {a}-{b - 1} at level {lvl}" for a, b, lvl in brief["sections"])
    return (
        f"THE BRIEF\n"
        f"  tune:        {brief.get('name', 'untitled')}\n"
        f"  key:         {brief['key']} {brief['mode']}\n"
        f"  tempo:       {brief['bpm']} BPM\n"
        f"  form:        {brief['bars']} bars, {brief['beats_per_bar']}/4\n"
        f"  progression: {prog}\n"
        f"  sections:    {secs}\n"
        f'  direction:   {brief.get("direction", "none")}\n'
    )


BOX_CHARS = "│┃╭╮╰╯├┤─┌┐└┘·"


def clean_reply(text: str) -> str:
    """The quiet mode still echoes tool output. Keep the prose, drop the box art."""
    keep = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped[0] in BOX_CHARS:
            continue
        if stripped.startswith(("@@", "+++", "---")) or stripped.startswith(("+{", "-{")):
            continue
        keep.append(line.rstrip())
    return "\n".join(keep).strip()


def call_bot(profile: str, prompt: str, run_dir: str, tag: str,
             timeout: int = 300) -> tuple[str, float]:
    """One turn. Returns (reply, seconds). Prompt and reply both hit disk."""
    qpath = os.path.join(run_dir, "transcript", f"{tag}.prompt.txt")
    write(qpath, prompt)
    t0 = time.time()
    proc = subprocess.run(
        [HERMES, "-p", profile, "chat", "--query-file", qpath, "--oneshot", "-Q",
         "--in", REPO],
        capture_output=True, text=True, timeout=timeout,
    )
    dt = time.time() - t0
    reply = clean_reply((proc.stdout or "").strip() or (proc.stderr or "").strip())
    write(os.path.join(run_dir, "transcript", f"{tag}.reply.txt"), reply)
    status = "ok" if proc.returncode == 0 else f"exit {proc.returncode}"
    log(f"    {profile:9} {dt:5.1f}s  {status}  {len(reply):5d} chars")
    return reply, dt


def contract_text() -> str:
    return read(os.path.join(HERE, "CONTRACT.md"))


def round1_prompt(player: str, brief: dict, out_path: str) -> str:
    return (
        f"You are in a session with Hermes Band. {brief_block(brief)}\n"
        f"YOUR JOB\n"
        f"Write your part for this tune, on your own, before you hear anyone else.\n\n"
        f"Write valid JSON to exactly this path:\n  {out_path}\n\n"
        f'The shape is: {{"player": "{player}", "parts": [ ... ], '
        f'"comment": "two sentences"}}\n\n'
        f"Use only these instruments: {sorted(ALLOWED[player])}\n\n"
        f"Write the file with your file tool. Then reply in 2-3 sentences: what "
        f"you played and why. Do not paste the JSON into your reply.\n\n"
        f"---\n\n{contract_text()}\n"
    )


def others_block(parts: dict, exclude: str) -> str:
    chunks = []
    for name, data in parts.items():
        if name == exclude or data is None:
            continue
        chunks.append(
            f"### {name}\n```json\n{json.dumps(data, indent=2)}\n```\n"
            f"they said: {data.get('comment', '(no comment)')}\n"
        )
    return "\n".join(chunks) if chunks else "(nobody else has written yet)"


def round2_prompt(player: str, brief: dict, parts: dict, out_path: str) -> str:
    return (
        f"Round two. Same session, same tune. {brief_block(brief)}\n"
        f"Here is what the others wrote while you were working:\n\n"
        f"{others_block(parts, player)}\n"
        f"YOUR JOB\n"
        f"React to them, then decide about your own part.\n"
        f"- If someone is sitting in your space, say so and name what you would change.\n"
        f"- If the drummer is too busy, or the guitar is filling every hole, say it.\n"
        f"- If their part is better than yours, say that too. No false politeness.\n\n"
        f"Then: keep your part as it is, or revise it.\n"
        f"- To keep it: write nothing.\n"
        f"- To revise: rewrite {out_path} with the new version (same shape).\n\n"
        f"Reply in 2-3 sentences: your critique, and whether you changed anything. "
        f"Do not paste JSON.\n"
    )


def leader_prompt(brief: dict, parts: dict, out_path: str) -> str:
    return (
        f"You are the bandleader. The players have finished. {brief_block(brief)}\n"
        f"Here is everything they wrote:\n\n{others_block(parts, LEADER)}\n"
        f"YOUR JOB\n"
        f"Make the call. Decide which parts make the finished arrangement.\n\n"
        f"You may drop at most one player, and only for a musical reason — two "
        f"parts fighting for the same register counts. You must keep at least "
        f"three of them.\n\n"
        f"Write valid JSON to exactly this path:\n  {out_path}\n"
        f'Shape: {{"keep": ["sticks", "lowend", "clavinet", "scratch"], '
        f'"note": "one sentence on the single change that mattered most"}}\n\n'
        f"Then reply in 2-3 sentences: your verdict and why.\n"
    )


def parse_json_file(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return None


def part_gate(player: str, data) -> str | None:
    """Return an error string, or None if the part file is usable."""
    if not isinstance(data, dict):
        return "file missing or not valid JSON"
    if "parts" not in data or not isinstance(data["parts"], list) or not data["parts"]:
        return 'missing a non-empty "parts" list'
    if len(data["parts"]) > 2:
        return f'{len(data["parts"])} parts — two at most, you are not the arranger'
    for p in data["parts"]:
        inst = p.get("inst")
        if inst not in ALLOWED[player]:
            return f"instrument {inst!r} is not yours. Allowed: {sorted(ALLOWED[player])}"
    return None


def merge_score(brief: dict, parts: dict, keep: list[str], name: str) -> dict:
    out_parts = []
    for player, data in parts.items():
        if data is None or player not in keep:
            continue
        for p in data["parts"]:
            out_parts.append(p)
    return {
        "hermes_band": 1,
        "name": name,
        "bpm": brief["bpm"],
        "tonic": brief["tonic"],
        "key": brief["key"],
        "mode": brief["mode"],
        "bars": brief["bars"],
        "beats_per_bar": brief.get("beats_per_bar", 4),
        "progression": brief["progression"],
        "sections": brief["sections"],
        "seed": brief.get("seed", 0),
        "parts": out_parts,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Convene the Hermes Band.")
    ap.add_argument("--brief", required=True)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--rounds", type=int, default=2, choices=[1, 2])
    ap.add_argument("--only", default=None, help="comma separated players")
    ap.add_argument("--room", default=None)
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()

    brief = json.loads(read(args.brief))
    run_id = args.run_id or time.strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(HERE, "runs", run_id)
    parts_dir = os.path.join(run_dir, "parts")
    os.makedirs(os.path.join(run_dir, "transcript"), exist_ok=True)

    players = PLAYERS if not args.only else [p.strip() for p in args.only.split(",")]
    log(f"\n=== SESSION {run_id} ===")
    log(f"{brief['name']}: {brief['bars']} bars @ {brief['bpm']} BPM, "
        f"{brief['key']} {brief['mode']}, {len(players)} players\n")

    # ---------------------------------------------------------------- round 1
    log("ROUND 1 — write it blind")
    parts: dict[str, dict | None] = {}
    timings: dict[str, float] = {}
    for player in players:
        out_path = os.path.join(parts_dir, f"{player}.json")
        if os.path.exists(out_path):
            os.remove(out_path)
        reply, dt = call_bot(player, round1_prompt(player, brief, out_path),
                             run_dir, f"r1-{player}")
        timings[player] = dt
        data = parse_json_file(out_path)
        err = part_gate(player, data)
        if err:
            log(f"    -> rejected: {err}. One retry.")
            retry = round1_prompt(player, brief, out_path) + (
                f"\n\nYOUR PREVIOUS ATTEMPT WAS REJECTED: {err}\n"
                f"Write the file again, correctly, at {out_path}\n")
            reply2, dt2 = call_bot(player, retry, run_dir, f"r1-{player}-retry")
            timings[player] += dt2
            data = parse_json_file(out_path)
            err = part_gate(player, data)
            if err:
                log(f"    -> still rejected: {err}. Sitting this one out.")
                data = None
        parts[player] = data
    log("")

    # ---------------------------------------------------------------- round 2
    if args.rounds >= 2 and len(players) > 1:
        log("ROUND 2 — the room")
        for player in players:
            if parts.get(player) is None:
                continue
            out_path = os.path.join(parts_dir, f"{player}.json")
            before = json.dumps(parts[player], sort_keys=True)
            reply, dt = call_bot(player, round2_prompt(player, brief, parts, out_path),
                                 run_dir, f"r2-{player}")
            timings[player] += dt
            after_data = parse_json_file(out_path)
            if after_data and json.dumps(after_data, sort_keys=True) != before:
                err = part_gate(player, after_data)
                if err:
                    log(f"    -> revision rejected ({err}); keeping round-1 part")
                else:
                    parts[player] = after_data
                    log(f"    -> {player} REVISED their part")
            else:
                log(f"    -> {player} kept their part")
        log("")

    # ---------------------------------------------------------------- round 3
    keep = [p for p in parts if parts[p] is not None]
    verdict = None
    if len(keep) > 2 and not args.only:
        log("ROUND 3 — the bandleader calls it")
        vpath = os.path.join(parts_dir, f"{LEADER}-verdict.json")
        reply, dt = call_bot(LEADER, leader_prompt(brief, parts, vpath), run_dir, "r3-maestro")
        timings[LEADER] = dt
        verdict = parse_json_file(vpath)
        if isinstance(verdict, dict) and isinstance(verdict.get("keep"), list):
            proposed = [p for p in verdict["keep"] if p in keep]
            if len(proposed) >= 3:
                dropped = [p for p in keep if p not in proposed]
                keep = proposed
                log(f"    -> kept {keep}" + (f", dropped {dropped}" if dropped else ""))
            else:
                log("    -> verdict kept fewer than three; ignoring it")
        else:
            log("    -> no usable verdict; keeping everyone")
        log("")

    # ---------------------------------------------------------------- render
    if not keep:
        log("Nobody produced a usable part. Nothing to render.")
        return 1

    name = f"{brief.get('name', 'session')}-{run_id}"
    score = merge_score(brief, parts, keep, name)
    score_path = os.path.join(run_dir, "score.json")
    write(score_path, json.dumps(score, indent=2) + "\n")
    log(f"SCORE {score_path}  ({len(score['parts'])} parts: {', '.join(keep)})")

    result = {"run_id": run_id, "score": score_path, "parts": parts,
              "keep": keep, "verdict": verdict, "timings": timings}

    if not args.no_render:
        room = args.room or brief.get("room", "room")
        log("\nMIXDOWN")
        env = dict(os.environ)
        proc = subprocess.run(
            [os.path.join(REPO, ".venv/bin/hermes-band"), "play", score_path,
             "-o", os.path.join(REPO, "out"), "--room", room],
            capture_output=True, text=True, env=env)
        print(proc.stdout.strip() or proc.stderr.strip())
        result["render"] = proc.stdout.strip()
        tgt = os.path.join(REPO, "out", name)
        wav = os.path.join(tgt, f"{name}.wav")
        if os.path.exists(wav):
            chk = subprocess.run(
                [os.path.join(REPO, ".venv/bin/hermes-band"), "check", wav],
                capture_output=True, text=True)
            print(chk.stdout.strip()[-1200:])
            result["check"] = chk.stdout.strip()
            result["wav"] = wav
            result["mp3"] = os.path.join(tgt, f"{name}.mp3")

    write(os.path.join(run_dir, "result.json"), json.dumps(result, indent=2) + "\n")
    log(f"\n=== SESSION COMPLETE — {run_dir} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
