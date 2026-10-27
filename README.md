# Hermes Band

Compose and render original music on your own machine. No music API, no model
download, no per-track cost.

You write an arrangement — key, tempo, chord progression, which instruments play
what — and it renders a finished, mastered audio file. Renders are deterministic:
the same arrangement always produces the same audio.

```python
from band import Arrangement, render

arr = Arrangement(bpm=90, key="D", mode="major",
                  progression=["I", "V", "vi", "IV"], bars=12)
arr.add(inst="steel",     role="fingerpick", pattern="folk", register=(55, 79))
arr.add(inst="fingerbass", role="bass_root5", start_bar=2, register=(40, 52))
arr.add(inst="drums",     role="drums", start_bar=4,
        extra={"pattern": "folk_soft"})

print(render(arr, "out/bed", room="room", name="bed"))
# -> exact-length wav + mp3, mastered to -14 LUFS / -1 dBTP
```

## Why this instead of a music API

Generative music services give you a black box. You can't ask for *"D major,
I–V–vi–IV at 88 BPM, second inversion on the V, no vocals, exactly 32.000
seconds, and leave 1–4 kHz clear for narration"* and get it.

This gives you all of those dials. `Arrangement.duration()` tells you the exact
musical length, and `render(..., tail=0)` trims to it, so scoring to picture
never needs a stretch or a cut.

Use a generative model when you want a performance with human nuance you didn't
specify. Use this when you want control, an exact length, and a re-render that
costs nothing.

## Install

You need `fluidsynth` and a General MIDI soundfont. On Debian/Ubuntu:

```bash
sudo apt install fluidsynth fluid-soundfont-gm ffmpeg
```

Then:

```bash
git clone https://github.com/RegeneratusLabs/hermes-band
cd hermes-band
pip install -e .
hermes-band doctor
```

`doctor` tells you whether the pieces are in place, and where it's looking for
the soundfont. If your `.sf2` lives somewhere else, set `HERMES_BAND_SF2`.

It's not on PyPI yet — clone and install.

## Use it

```bash
hermes-band demo              # render every bundled arrangement
hermes-band demo -t funk      # just one
hermes-band check out/bed/bed.wav   # measure a render and flag problems
```

Or from Python:

```python
from band import presets, render

name = "bed"
factory, room = presets.PRESETS[name]
render(factory(), f"out/{name}", room=room, name=name)
```

## How an arrangement is built

An `Arrangement` holds a key, a tempo, a chord progression (one entry per bar,
repeats as needed), and a list of `Part`s. Each part picks an instrument and a
*role* — and the role is where the musical knowledge lives.

**Roles**

| role | what it plays |
| --- | --- |
| `fingerpick` | fingerstyle pattern with thumb/finger separation and let-ring |
| `strum` | chord voicing rolled across the strings |
| `block` | sustained pad chord |
| `bass_root5` | root and fifth on the strong beats |
| `bass_walk` | root, fifth, octave, and a chromatic approach to the next chord |
| `arp` | arpeggio over an extended voicing |
| `sparkle` | sparse high accents |
| `melody` | a generated lead line that lands on chord tones |
| `drums` | a kit pattern with humanised timing |
| `funk_guitar` | chicken scratch — muted off-sixteenths with accents |
| `slap_bass` | syncopated thumb and pop, with ghost notes |
| `stab` | sparse, short chord hits |

**Patterns** — `fingerpick`/`arp`: `folk`, `travis`, `sparse`, `arp_up`,
`rolling`, `oompah`. **Drums**: `folk_soft`, `folk_full`, `pulse`, `heartbeat`,
`boom_bap`, `funk`.

**Rooms** — `dry`, `close`, `room`, `hall`, `cathedral`.

Chord symbols are roman numerals: `I`, `vi`, `bVI`, `V7`, `Imaj7`, `ii7`,
`m7b5`. Case carries quality — uppercase is major, lowercase is minor.

```python
arr.add(inst="nylon", role="melody", start_bar=0, register=(64, 81))
arr.add(inst="strings", role="block", start_bar=4, gain=0.5)
arr.add(inst="kalimba", role="sparkle", start_bar=8, gain=0.5)
```

Every part takes `start_bar`, `end_bar`, `gain`, `octave`, `jitter`, `swing`,
`register`, `voices`, and an `extra` dict for role-specific options and mix
overrides.

Instruments are General MIDI: `piano`, `rhodes`, `vibes`, `nylon`, `steel`,
`clean_elec`, `muted_gtr`, `upright`, `fingerbass`, `cello`, `strings`, `choir`,
`flute`, `clav`, `organ`, `brass`, `kalimba`, `warm_pad`, `glass_pad`. See
`band/gm.py` for the full list.

## Five things that make it sound like music

Skip any one of these and you get a MIDI demo. They're the whole difference.

1. **Voice leading.** `voice_lead()` picks the inversion that moves least from
   the previous chord. Common tones hold, the rest step. Stacking every chord in
   root position is the single most recognisable "this was generated" sound.
2. **Per-instrument stems, mixed separately.** Each part gets its own high-pass,
   presence lift, pan, fader and reverb send. Summing a soundfont forces every
   instrument through the same EQ, which is why so much MIDI music sounds flat.
3. **A real impulse response.** The reverb is built from noise — exponential
   decay, highs decaying faster than lows, early reflections, decorrelated
   stereo — then FFT-convolved. Not a stock reverb algorithm.
4. **Humanisation.** Velocity variation, microtiming jitter, swing on off-beats,
   and per-voice drum offsets. A shaker that sits 3 ticks ahead of the beat and a
   snare that sits 6 behind is the difference between a drummer and a machine.
5. **A dynamic arc.** Parts enter and leave; a `sections` curve shapes the build.

## Check your renders

Don't trust a render you haven't measured.

```bash
hermes-band check out/band/band.wav
```

It reports loudness, true peak, L/R balance, stereo correlation, band energy,
silent windows, per-part post-mix level and note counts — then flags objective
faults: clipping, mono collapse, a muddy low end, missing presence, parts that
are buried or dominating.

Healthy targets for a social/video master: −14 LUFS, −1 dBTP, L/R within ±1 dB,
stereo correlation 0.4–0.9, 60–250 Hz at 25–35%, 2–8 kHz at 6% or more, spectral
centroid 700–1100 Hz.

To confirm the audio contains the notes you composed, FFT a chord window and look
for peaks at the expected frequencies:

```python
from band import theory
theory.midi_to_freq(62)   # D4 -> 293.66
```

## Tests

```bash
pip install -e ".[dev]"
python -m pytest
```

Unit tests cover theory, the MIDI writer and the composer without touching audio
hardware. `tests/test_render.py` renders real audio end to end and skips itself
if `fluidsynth` or the soundfont isn't installed.

## Limits, stated plainly

- **Sampled GM instruments, not a real performer.** The ceiling is the soundfont.
  Good for beds, stings, sketches and library music. It is not a substitute for a
  recorded player on a lead line.
- **No vocals in the engine.** It doesn't sing. It can still *rap*: a local TTS
  voice placed one line per bar reads as rap, and `pieces/hermes-rap/` proves it.
- **No audio-to-MIDI.** It writes music; it doesn't transcribe it.
- **Not a generative model.** It doesn't invent a style from a text prompt. You
  tell it what to play, in more detail than you'd tell a human, and it plays it
  properly.

## The band

`session/` contains a five-piece band of Hermes Bots: a drummer, a bassist, keys,
a guitarist and a bandleader. Each is an isolated profile with its own SOUL.md and
opinions. They write parts, argue about the arrangement, and the bandleader mixes.

```bash
python session/assemble.py                                   # create the bots
python session/run.py --brief session/briefs/funk-e-dorian.json
python session/mix_round.py session/runs/<run-id>             # fix the balance
python session/report.py session/runs/<run-id>                # write it up
```

They work from a chart and a vocabulary, not from hearing anything — which is
what makes the result interesting rather than merely automatic. `session/runs/`
holds a complete session: every prompt, every reply, the parts they wrote, the
final score and a report.

**[docs/SESSION.md](docs/SESSION.md) is the process in full** — the five personas,
the contract they work against, what each of the four rounds actually sends them,
how the bandleader mixes a record it can't hear, and what lands on disk. The
result of the first session is in
[session/runs/session-01/REPORT.md](session/runs/session-01/REPORT.md); the
band's faces are in [session/avatars](session/avatars).

## Pieces

Finished work, with its source, so you can hear what the engine does before you
read the code.

**[`pieces/hermes-rap/`](pieces/hermes-rap) — "No Hype", 89 seconds of boom bap.**
The band's first vocal record. A local TTS voice raps one line per bar, locked to
the grid and rate-fitted so each line fills its bar, over an A-minor
Am7–Dm7–Fmaj7–E7 loop at 92 BPM. The beat is deterministic; the voice isn't, so
re-running gives you a different take of the same performance.

```bash
cd pieces/hermes-rap && python3 build.py && python3 vocals.py && python3 mix.py
```

`hermes-rap.mp3` is the master. The video is in `pieces/hermes-rap/film/`.
The technique — how you get a TTS engine to sit on a grid and read as rap, the
mix chain that keeps it legible, and the traps — is written up in
[skill/references/rap-vocals.md](skill/references/rap-vocals.md).

## Using it with Hermes

This is built to be operated by a [Hermes](https://hermes-agent.nousresearch.com)
agent as much as by a person. `skill/SKILL.md` is a ready-made Hermes skill:

```bash
cp -r skill ~/.hermes/skills/creative/hermes-band
```

An agent that loads it gets the workflow, the vocabulary, and — more usefully —
the traps that cost real time: fluidsynth's ten seconds of trailing silence,
soundfont patches that differ by 16 dB at the same velocity, and why a sparse
part should be judged on peak rather than RMS. Those are the things you'd
otherwise rediscover one wrong render at a time.

If you're wiring this into an agent pipeline, the contract is small: build an
`Arrangement`, call `render()`, then verify. `render()` returns the file paths
and the measured peak, so a caller doesn't need to re-measure to know it worked.

## Credits

This stands on other people's work:

- **[FluidR3 GM](https://github.com/musescore/MuseScore/tree/master/share/sound)** —
  the soundfont, by **Frank Wen**, released under the MIT licence. It's the
  instruments you're hearing.
- **[FluidSynth](https://www.fluidsynth.org/)** — real-time soundfont synthesis,
  LGPL-2.1. Renders MIDI to audio here.
- **[NumPy](https://numpy.org/)** — BSD-3. All the DSP: reverb, EQ, mixing.

## Licence

MIT. See [LICENSE](LICENSE).
