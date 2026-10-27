# HERMES — "No Hype", the film

89 seconds, 1920×1080, 24 fps. A robot MC raps the whole lyric over the record,
with the words on screen the entire time so you can follow them.

Nothing here is a stock asset. The character, the four sets, the money, the crowd,
the light beams and the type are all drawn in code, frame by frame — there is no
image, no font beyond the system ones, and no video footage in the pipeline.

```bash
python3 words.py            # lyric + word timing  -> words.json
python3 render.py --still 27.4        # look at a frame
python3 render.py --all               # 2136 JPEGs -> frames/
ffmpeg -y -framerate 24 -i frames/f%05d.jpg -i ../out/hermes-rap.wav \
  -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -movflags +faststart \
  -c:a aac -b:a 192k -shortest hermes-rap-clip.mp4
```

Output: `hermes-rap-clip.mp4` (1080p, 256 MB) and `hermes-rap-clip-720.mp4`
(17 MB, for sending to people). Neither is tracked — `.gitignore` keeps video out
of the repo, same as the rest of the engine's renders.

## How the words stay on the beat

`words.py` combines two sources and trusts neither alone:

* `vocals.py` writes the **measured** synth duration of every line to
  `out/lines.json`, so each line's audio window is known exactly, and
* faster-whisper gives a **word-level transcript** of the vocal bus.

Whisper's absolute times drift up to half a second across a take, so they are only
used as relative positions: each line's words are mapped onto that line's measured
window. Exact at the line level, right at the word level. 26 of 33 lines get real
whisper timing; the rest fall back to proportional-by-character, which is still
monotonic and still on the bar.

A word stays lit until the next word starts, which is what karaoke does — that also
covers whisper splitting "copy-pasting" into two words.

## The edit

Every cut lands on a bar. 34 bars at 92 BPM (2.609 s each).

| bars | time | shot |
| --- | --- | --- |
| 0–2 | 0:00 | alley, wide, title |
| 2–6 | 0:05 | alley, push in |
| 6–7 | 0:16 | lab — **burn 1**: a labelled "A CHAT BOX" rival cracks and dies |
| 7–8 | 0:18 | lab, close — 02:00 on the wall clock |
| 8–9 | 0:21 | lab, medium |
| 9–10 | 0:24 | lab — **burn 3**: the bubble pops |
| 10–14 | 0:26 | stage, hook, money, HERMES stamps |
| 14–16 | 0:37 | lab, fifty tools |
| 16–18 | 0:42 | rooftop, subagent slashes |
| 18–21 | 0:47 | lab, close |
| 21–22 | 0:55 | **burn 4**: weigh-in — A CHATBOT 0, HERMES 51 |
| 22–26 | 0:57 | stage, hook, the band's five avatars in the crowd |
| 26–29 | 1:08 | rooftop, pull back |
| 29–30 | 1:16 | **burn 5**: the subscription agreement, ripped in half |
| 30–32 | 1:18 | alley, walking |
| 32–34 | 1:24 | alley, end card |

The five burns are the point of the video, so each one gets its own setup and its
own gag rather than a caption over the same shot.

## Files

| file | what |
| --- | --- |
| `common.py` | canvas maths, camera warp, grade, halation, grain, type |
| `rig.py` | the Hermes bot — posed, jaw on the vocal envelope |
| `sets.py` | alley, rooftop, lab, stage |
| `render.py` | shot list, camera moves, overlays, the lyric card |
| `words.py` | lyric + word timing from the audio and the transcript |
| `words.json` | the timing, generated |
| `whisper_words.json` | raw whisper transcript of the vocal bus, generated |

## Things that cost time

* **`multiprocessing` does not work here.** The forkserver pool dies with
  `ConnectionResetError`, and with `spawn` the children re-import the module so
  `ENV` is `None` and every frame fails. Threads are the answer — PIL and numpy
  both release the GIL, and 6 threads gives 0.20 s/frame.
* **Per-frame grain destroys video compression.** Grain at 0.030 rendered a 599 MB
  file at CRF 19 and *more* at CRF 23 with `-tune grain`. Dropping the grain to
  0.0125 got the same look down to 256 MB at CRF 20.
* **A flat figure floats without a contact shadow.** An ellipse under the feet and
  a light-wrap pass (the plate, blurred, bled over the figure's own edge) is the
  difference between a cut-out and something standing in the room.
* **Cel shading must not be composited over the silhouette's alpha.** Using
  `Image.composite` with a translucent shade layer punches holes in the figure's
  alpha; put the shade on its own layer and `alpha_composite` it.
* **The rim light is found by offsetting the alpha**, not drawn as a band. A band
  across the frame reads as a rendering error.
