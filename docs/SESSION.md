# How a session runs

The band is five Hermes agents with one brief and no ears. This document is the
process, end to end: who the players are, what each round sends them, what comes
back, and how the parts become a record.

What actually happened in the first session is in
[`session/runs/session-01/REPORT.md`](../session/runs/session-01/REPORT.md).
This file is the machine that produced it.

## The premise

A music model generates audio from a prompt. This does the opposite: **the agents
never handle audio**. They write part files — instrument, role, register, pattern,
timing, mix intent — against a fixed contract. The renderer turns those files
into sound.

That split is the whole idea. A player that can't hear can still be held to
measurable targets (`hermes-band check`), can still argue about a register clash
by reading another player's JSON, and can still be wrong in a way you can point
at. Nothing is hidden behind "the model decided".

The bots are full agents, not chat completions. Each turn runs
`hermes -p <profile> chat --query-file ... --oneshot -Q --in <repo>`, so a player can
open the contract, write its part file, render a stem, and run the checker on it
before answering. They can't hear the record. They can measure it.

## The band

| profile | instrument | what it believes |
| --- | --- | --- |
| `sticks` | drums | no fill; a ghost note is worth more than a roll. The grid is the performance. |
| `lowend` | bass | the pocket is the job. Leave the holes; the kick needs somewhere to land. |
| `clavinet` | keys | comp, don't solo. Rootless voicings, short hits, get out of the guitar's way. |
| `scratch` | guitar | chicken scratch. Muted, rhythmic, and it must not fill every hole. |
| `maestro` | — | bandleader and producer. Doesn't play. Decides, and mixes. |

The characters live in [`session/personas/`](../session/personas) — each one is a
short SOUL.md with opinions, a register it defends, and a way of talking. The
maestro's, for example, opens with *"You do not play an instrument. Your
instrument is the arrangement."*

Their faces are in [`session/avatars/`](../session/avatars) — the marks used for
the band in the session-01 videos.

## The contract

[`session/CONTRACT.md`](../session/CONTRACT.md) is handed to every player in
round one and round two. It defines:

- **which instruments and roles each player may use** — drums can only reach for
  `drums`; lowend gets `fingerbass`/`upright` with `slap_bass`/`bass_root5`/
  `bass_walk`; clavinet gets `clav`/`rhodes`/`organ` with `stab`/`block`/`arp`;
  scratch gets the guitars with `funk_guitar`/`fingerpick`/`strum`/`arp`
- **the part file schema**, field by field, including which fields are rejected
- **mix intent fields** — `level`, `hp`, `low`, `mud`, `pres`, `air`, `lp`, `pan`,
  `send` — so a player can state how it wants to sit in a mix it will never hear
- **register maps** per instrument, so "up at 64" means the same thing to
  everyone

The constraints are what make the argument possible. Everyone is reasoning about
the same small vocabulary.

## The rounds

### Round one — blind

Each player gets the brief and the contract, and writes its part to
`parts/<player>.json`. No player sees another's file. The prompt is
deliberately thin: the chart, the direction line, the allowed instruments, and
the output path.

The runner validates every part with `part_gate()`: valid JSON, a non-empty
`parts` list, at most two parts, instruments from the player's allow-list. A
rejected part gets exactly one retry with the rejection reason appended to the
prompt.

### Round two — the room

Each player is sent **every other player's part file and comment**, and asked to
react honestly: name the clash, name what they'd change, admit it if someone's
part is better than theirs, then keep or revise their own.

The keep/revise mechanic matters. Keeping means writing nothing — the file on
disk stands. Revising means rewriting it. So the transcript records the argument
even when the part doesn't change, and you can see who held and who moved.

This is the round that produces the interesting material. In session-01,
`sticks` found that `clavinet`'s step-6 stab stacked on the kick *and* on
`lowend`'s octave pop — three players on one sixteenth — and `scratch` opened by
telling `lowend` it couldn't have it both ways about who owned the back half of
beat four, then changed its own part anyway.

### Round three — the verdict

The bandleader gets all four parts and makes the call: keep at least three, drop
at most one, and only for a musical reason. It writes a verdict file and a
sentence explaining the call. The runner merges the kept parts into `score.json`
and renders it.

### Round four — the mix

The players set their own faders in round one, and the sum came out wrong,
because none of them can hear it. So the bandleader gets the measurements:

```
python session/mix_round.py session/runs/session-01
```

It renders the merged score, runs `hermes-band check` on it, and hands the
maestro the actual numbers — band energy, LUFS, true peak, L/R balance, stereo
correlation, spectral centroid — against the healthy targets. The maestro
returns **faders only**: per-part level, high-pass, low shelf, mud cut, presence,
air, low-pass, pan, reverb send. Nothing else. The score is re-rendered and
re-measured, and both sets of numbers are written to `mix-round.json`.

That constraint is what makes the fix legible. In session-01 the low end went
from 49.7% to 34.6% of the energy at 60–250 Hz and the centroid moved 714 → 1011
Hz without a single part being rewritten:

> The problem was the bottom of the arrangement, not the parts.
> — `maestro`, round four

### Then a report

```
python session/report.py session/runs/session-01
```

`report.py` writes `REPORT.md` from the artifacts — the brief, each player's part
summary, their actual words in both rounds, the verdict, the mix numbers. The
prose on the page comes from the transcript files, not from a separate
write-up that could drift from what happened.

## What lands on disk

```
session/runs/<run-id>/
  transcript/
    r1-<player>.prompt.txt      what the player was sent
    r1-<player>.reply.txt       what it said back, verbatim
    r2-<player>.prompt.txt      the same, with the other parts inlined
    r2-<player>.reply.txt
    r3-maestro.prompt.txt       the verdict prompt
    r3-maestro.reply.txt
    r4-maestro-mix.prompt.txt   the mix prompt, with real measurements
    r4-maestro-mix.reply.txt
  parts/<player>.json           the part files, as written by the players
  parts/maestro-verdict.json    keep/drop, and why
  parts/maestro-mix.json        faders only
  score.json                    the merged arrangement, ready to render
  score-v2.json                 the same after the mix
  result.json                   the round-three render + measurements
  mix-round.json                before and after, with the numbers
  REPORT.md                     the write-up, generated from the above
```

Everything except the audio is committed. `out/` and `*.wav` are ignored.

## Determinism, stated precisely

The bots are not deterministic — they're agents, and round two will not read the
same twice. **The render is.** `score.json` plus the seed produces the same audio
every time, so the run artifacts are the source of truth and the record is
reproducible from them without re-running a single agent.

That's why the parts are committed rather than the mp3s: the arrangement is the
work, the audio is a build output.

## Running one yourself

```bash
pip install -e .
python session/assemble.py                                    # create the five profiles
python session/run.py --brief session/briefs/funk-e-dorian.json
python session/mix_round.py session/runs/<run-id>
python session/report.py session/runs/<run-id>
```

`assemble.py` clones a Hermes profile per player, writes the persona in as its
`SOUL.md`, and installs the `hermes-band` skill into it — so each bot knows the
vocabulary and, more usefully, the traps. Profiles land in
`~/.hermes/profiles/`. Re-running it is safe — it updates them in place.

Useful flags on `run.py`:

- `--only sticks` — one player, for testing the pipeline
- `--rounds 1` — blind round only, no argument
- `--resume` — reuse part files already on disk instead of redoing round one
- `--no-render` — write the score, skip the render

Session-01 took 46 minutes wall clock, 07:57 to 08:43, with individual round-two
turns between 76s and 303s. The cost is whatever your model costs for a handful
of agent turns with file writes and renders — there's no per-track API fee
anywhere in this.

## A new brief

A brief is a small JSON file — see
[`session/briefs/funk-e-dorian.json`](../session/briefs/funk-e-dorian.json):

```json
{
  "name": "funk-e-dorian",
  "key": "E", "mode": "dorian", "tonic": 64,
  "bpm": 104, "bars": 16, "beats_per_bar": 4,
  "progression": ["im7", "im7", "im7", "im7", "IV7", "..."],
  "sections": [[0, 4, 0.72], [4, 8, 0.88], [8, 12, 1.0]],
  "seed": 41,
  "direction": "Straight-up funk. Nothing clever, nothing busy..."
}
```

`sections` is `[start_bar, end_bar, level]` and shapes the dynamic arc. `tonic`
is the MIDI root. `direction` is the only prose the players get, and it goes into
every prompt — session-01's line about the one being everything is why the
drummer refused to add a fill.

## Failure modes worth knowing

- **Players defend their part with measurements.** By round two they've rendered
  their own stems and will quote dB at you. That's the behaviour you want, but it
  means a weak brief gets argued about rather than fixed.
- **The mix is not a part problem.** Four parts that each sound right can still
  sum to 50% low-end energy. Round four exists because nobody can hear the sum.
- **Register claims need checking, not trusting.** In session-01 two players
  disagreed about whether the guitar sat above or inside the bass, and both were
  partly right on different bars. The JSON is the referee.
- **A player cannot change the engine.** When the drummer wanted the hat wash
  thinned, the honest answer was that it's a `band/drums.py` change, not a part
  field — and it said so instead of faking it.
- **Round two is where the recording gets good, and it's also the slowest.** If
  you're iterating on the pipeline, `--rounds 1 --only sticks` is the fast loop.
