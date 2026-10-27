---
name: hermes-band
description: "Use when generating original music locally, no music API."
version: 0.1.0
author: Regeneratus Labs
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Music, Audio, Composition, MIDI, Fluidsynth, Soundfont, Video, Mixing]
    homepage: https://github.com/RegeneratusLabs/hermes-band
prerequisites:
  commands: [fluidsynth, ffmpeg]
  python: [numpy]
---

# Hermes Band

Compose and render original music entirely on the local machine. No API key, no
model download, no per-track cost. Renders are deterministic — same arrangement,
same audio, every time.

Repo: https://github.com/RegeneratusLabs/hermes-band

## When to Use

- A video needs a music bed, sting, or outro and there's no licensed track.
- The music must be an **exact length** to cut against picture.
- A bed must leave space for narration or voiceover.
- You need a specific key, tempo, progression or instrument that a generative
  API can't be told precisely.
- A render must be reproducible — no generative drift between takes.
- Zero per-track cost matters (many variants, long series, revisions).

Do **not** reach for this for sung vocals, or to match a reference track's
production. That's a generative model or a human.

## Install

```bash
sudo apt install fluidsynth fluid-soundfont-gm ffmpeg
git clone https://github.com/RegeneratusLabs/hermes-band
cd hermes-band && pip install -e .
hermes-band doctor
```

`doctor` must say "ready to render" before anything else. If the soundfont lives
elsewhere, set `HERMES_BAND_SF2`.

## Minimal correct usage

```python
from band import Arrangement, render

arr = Arrangement(bpm=90, key="D", mode="major",
                  progression=["I", "V", "vi", "IV"], bars=12)
arr.add(inst="steel", role="fingerpick", pattern="folk", register=(55, 79))
arr.add(inst="fingerbass", role="bass_root5", start_bar=2, register=(40, 52))
arr.add(inst="drums", role="drums", start_bar=4, extra={"pattern": "folk_soft"})

r = render(arr, "out/bed", room="room", lufs=-14.0, name="bed")
```

CLI: `hermes-band demo [-t bed|band|pulse|funk] [-o DIR]` and
`hermes-band check <file.wav>`.

`render()` returns `{wav, mp3, music_duration, duration, peak_db, stems}`.
For exact lengths use `render(..., tail=0)`; `Arrangement.duration()` is the
musical length in seconds.

## Rules that are not optional

1. **Never ship a render you haven't measured.** Run `hermes-band check` and read
   the verdict.
2. **Keep parts inside their register** — `band/gm.py` lists low/high per
   instrument. Outside it, samples sound wrong or vanish.
3. **Give every part a `start_bar`.** Everything entering at bar 0 is the
   clearest tell of a machine arrangement.
4. **Let the section curve work.** One velocity for the whole piece sounds
   generated.
5. **Don't sum stems by hand.** `render()` already renders one stem per part and
   mixes with per-instrument EQ, pan, level and reverb send.

## The five things that make it sound like music

1. **Voice leading** — `theory.voice_lead()` picks the inversion that moves least
   from the previous chord. Root-position chords are the most recognisable
   generated sound.
2. **Per-instrument stems, mixed separately.** A summed soundfont forces every
   instrument through the same EQ and reverb, which is why it sounds flat.
3. **A real impulse response** — `band/reverb.py` synthesises one from noise
   (decay, frequency-dependent tail, early reflections, decorrelated stereo).
4. **Humanisation** — velocity variation, microtiming jitter, swing, per-voice
   drum offsets.
5. **A dynamic arc** — parts enter and leave; `sections` shapes the build.

## Vocabulary

Roles: `fingerpick` `strum` `block` `bass_root5` `bass_walk` `arp` `melody`
`sparkle` `drums` `funk_guitar` `slap_bass` `stab`.

Fingering patterns: `folk` `travis` `sparse` `arp_up` `rolling` `oompah`.
Drum patterns: `folk_soft` `folk_full` `pulse` `heartbeat` `boom_bap` `funk`.
Rooms: `dry` `close` `room` `hall` `cathedral`.
Chord symbols: `I` `vi` `bVI` `V7` `Imaj7` `ii7` `m7b5` — case carries quality.

`band/presets.py` has four complete arrangements worth copying from: folk bed,
full band, minor electronic, and an E-dorian funk groove.

## Traps that cost real time

- **fluidsynth appends ~10 s of silence to every file.** `render_midi()` trims it.
  Call fluidsynth yourself and your durations will be wrong.
- **Soundfont patch levels are wildly inconsistent.** FluidR3's flute is ~16 dB
  louder than its kalimba at identical velocity. Some patches need +8 dB faders —
  measure, don't assume.
- **Judge sparse parts on peak, not RMS.** A mallet ping has a ~28 dB crest
  factor; RMS calls it buried when it's clearly audible.
- **ffmpeg won't write over its own input.** `loudnorm` needs a temp file.
- **`-r 44100` and `synth.sample-rate` are separate settings.** A mismatch detunes
  everything — check a rendered A4 measures 440 Hz ±5 cents.
- **Jitter makes first-beat notes slightly negative.** The MIDI writer clamps at
  tick 0; don't remove that.
- **`band.render` is a function, not a module.** The module is `band.renderer`.

## Verify

```bash
hermes-band check out/bed/bed.wav
```

Reports loudness, true peak, L/R balance, stereo correlation, band energy,
silent windows, per-part post-mix level and note counts, then flags clipping,
mono collapse, mud, missing presence, and buried or dominating parts.

Healthy targets: −14 LUFS, −1 dBTP, L/R within ±1 dB, stereo correlation
0.4–0.9, 60–250 Hz at 25–35%, 2–8 kHz at 6%+, centroid 700–1100 Hz.

To confirm the audio contains the notes you composed, FFT a chord window and
check for peaks at `theory.midi_to_freq(pitch)`.

## Limits, stated plainly

- **Sampled GM instruments, not a real performer.** The ceiling is the soundfont.
  Good for beds, stings, sketches and library music; not a substitute for a
  recorded player on a lead line.
- **No vocals in the engine itself** — but a local TTS rapped one line per bar,
  trimmed to the downbeat and rate-fitted, reads as rap. See
  `references/rap-vocals.md` for the full recipe, mix chain and verification.
- **No audio-to-MIDI** — it writes music, it doesn't transcribe it.
- **Not a generative model.** You tell it what to play, in more detail than you'd
  tell a human, and it plays it properly.
