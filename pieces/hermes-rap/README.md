# HERMES — "No Hype"

The band's first vocal record. 89 seconds of boom bap, rapped by a local TTS voice
locked to the grid, mixed here, mastered here. No generative music service, no
licensed beat, no cloud.

```bash
cd pieces/hermes-rap
python3 build.py     # the beat       -> out/bed/bed.wav   (-16 LUFS bed)
python3 vocals.py    # the rap        -> out/vocal_raw.wav
python3 mix.py       # the record     -> out/hermes-rap.mp3
```

Needs `fluidsynth`, `fluid-soundfont-gm`, `ffmpeg`, and a piper voice. Default
voice is `en_US-ryan-high`; override with `RAP_VOICE=/path/to/voice.onnx` and set
`RAP_OUT` if you don't want the renders in `pieces/hermes-rap/out/`.

The finished single is `hermes-rap.mp3` next to this file.

## The arrangement

92 BPM, A minor, 34 bars, one bar per lyric line. Am7 – Dm7 – Fmaj7 – E7.

| bar | inst | role | what it's doing |
| --- | --- | --- | --- |
| 0 | drums | `drums` | boom bap, fills on the last bar of each section |
| 0 | rhodes | `block` | the harmonic bed, rolled off at 7.8 kHz so the voice owns 2–5 kHz |
| 2 | fingerbass | `bass_root5` quarters | in on the verse, not the intro |
| 10 | vibes | `sparkle` | hook colour, offbeats |
| 22 | clav | `stab` | answers the second hook |
| 26 | strings_hi | `block` | lift for the last verse |

The bed renders at −16 LUFS and the vocal rides on top, sidechain-ducked. The sum
masters to −14 LUFS / −1.5 dBTP. Check it with `hermes-band check`:

```
lufs -14.1   true_peak -1.5   bass 25.5%   presence 10.5%
clipped_samples 0            VERDICT: clean
```

## How the voice raps

The engine has no vocals, so the rap is one TTS line per bar: synthesise, measure,
re-synthesise faster until it fills the bar but not quite, trim the silence so the
first syllable lands on the downbeat, sum at `bar * 2.6087s`. Full recipe and the
mix chain are in the skill at `skill/references/rap-vocals.md`.

Verified by transcribing the finished master with faster-whisper: it returns the
lyric sheet almost verbatim over the beat, which is the only proof that matters
that the words are actually sitting on top of the music and not under it.

## Files

| file | what |
| --- | --- |
| `build.py` | the arrangement, plus `LINES` — the lyric sheet as `{bar: line}` |
| `vocals.py` | piper fitting, bar placement, ad libs |
| `mix.py` | vocal chain, sidechain duck, dub taps, master |
| `lyrics.md` | the lyric sheet with bar and timestamp |
| `hermes-rap.mp3` | the record |
| `film/` | the music video — see `film/README.md` |
