# Rap / spoken-word vocals over a hermes-band bed

The engine has no vocals, but a local TTS (piper) rapped *against the grid* reads as
rap rather than narration. The trick is one line per bar, placed on the downbeat,
with each line's speaking rate tuned so it fills the bar.

## Recipe

1. **Fix the grid first.** Bars, tempo, and bar count decide the lyric count.
   At 92 BPM a bar is 2.609 s; a 12-syllable line at piper `--length-scale 0.88`
   lands about 2.1-2.4 s, which leaves a breath before the next bar. 34 bars = 89 s.
2. **One line = one bar.** Store lyrics as `{bar_number: text}`. Empty bars stay
   instrumental — that's what makes it feel arranged.
3. **Fit each line, don't stretch the take.** Synth at 0.88, measure, then
   re-synth with `scale * (target / actual)`, clamped to `[0.60, 0.95]`. Above 0.60
   you can hear the tape speed up, so *shorten the line* instead of pushing harder.
   Target ≈ 0.90 of a bar (~0.72 for lines under 5 words — short punches want air).
4. **Trim and place.** Cut leading/trailing silence (threshold 0.012, 12 ms pad) so
   the first syllable sits on the downbeat, then sum into a bus at
   `bar * BAR + 0.02 s`. Peak-normalise each line to 0.82 before summing.
5. **Ad libs are short.** Piper says "yeah" in 0.17 s at scale 1.0 — a single
   syllable is a blip. Use "yeah yeah" / "uh huh" for anything you want heard.
   Place them at `bar*BAR + beat*BAR/4` at gain 0.26-0.30.
6. **Produce the voice.** ffmpeg chain that works:
   `highpass=f=95, equalizer=f=260 -3dB (de-mud), f=1400 +1.2, f=3200 +3.5 (presence),
   f=9500 high-shelf +1.8, acompressor threshold=0.10 ratio=2.8 attack=8 release=160
   makeup=2.0`.
7. **Width without mush.** 13 ms delayed double at 0.30, plus tempo-synced 1/8 dub
   taps at 0.20 / 0.10 placed opposite in the stereo field. One-eighth at 92 BPM =
   0.326 s.
8. **Duck the bed.** Envelope-follow the vocal (4 ms attack / 150 ms release),
   normalise by the 99.5th percentile, then `bed *= 1 - 0.42 * env`. Cheaper and
   more transparent than a compressor sidechain, and it keeps the words legible.

## Verification (do not skip)

Transcribe your own mix with faster-whisper (`small.en`, int8, CPU). If Whisper
returns the lyric sheet nearly verbatim *over the beat*, the vocal is genuinely
sitting on top and every line is intelligible. If it returns mush, the vocal is
buried — fix that before touching anything else. This is a better mix check than
any spectrogram read.

Also assert the timings: segment start times should equal `bar * BAR` to within
~0.05 s, which proves the vocals are actually on the grid.

## Traps

- **`alimiter` defaults to `level=enabled`**, which auto-normalises its output back
  to 0 dBFS and undoes the limit. Always pass `alimiter=limit=0.89:level=disabled`
  or the master clips (67 clipped samples, peak 0.0 dBFS, VERDICT: clipping).
- **Bed at −16 LUFS, vocal on top, master to −14 LUFS.** Mastering the sum at
  −14 with a hot vocal gives −12.5 and an LRA of 1.4 — squashed.
- **Sidechain per channel.** `duck` is 1-D; broadcasting it against a stereo bed
  silently produces a 2-D mess. Index `bed[:, 0] * duck` explicitly.
- **Bed stereo matters.** `read_wav` in the vocal helpers averages to mono; read the
  bed with its own stereo reader or the whole bed collapses to the centre.
- **Lyric writing is the real constraint.** Longest line sets the tempo pressure,
  not the other way round. Write to the bar, count syllables, keep lines 9-12.
