# Hermes Band — session-01

Five Hermes agents were given one brief: make a funk record. Each one plays a single instrument. None of them can hear anything. This is the actual record of what they did.

## The brief

```
key         E dorian
tempo       104 BPM
form        16 bars, 4/4
progression im7 | im7 | im7 | im7 | IV7 | IV7 | im7 | im7 | iim7 | iim7 | im7 | im7 | IV7 | IV7 | IV7 | im7
```

> Straight-up funk. Nothing clever, nothing busy. The one is everything, the guitar must not fill every hole, and it has to groove at 104 or it does not count.

## Round one — everyone writes blind

No player could see or hear the others. Each was told the chart, the vocabulary they were allowed to use, and to write one part.

*(This session ran before round-one snapshots existed. Where a player revised in round two, the part summary below is their revised part; their round-one words are unchanged.)*

### Drummer (`sticks`)

- `drums` / `drums`, start_bar=0, gain=1.0, pattern=funk

> One kit, funk pattern, no fill: kick on the one plus two pushes at the and of 2 and the e of 3, snare accent on 2 and 4 with ghosts either side, hats running sixteenths as a wash with the offbeats a hair ahead of the grid. The section levels handle the dynamics, so the grid is identical for 16 bars and nothing here is busier than the one.

*One kit, the funk grid, no fill. Kick on the one with two pushes, snare accent on 2 and 4 with ghosts either side, hats sixteenths as a wash with the offbeats a hair ahead — section levels do the dynamics so it builds without me adding anything.
Part written and validated at /home/josh/hermes-band/session/runs/session-01/parts/sticks.json; a drums-only render came out 38.3s, peak -0.96 dB, which is the tune at 104. That 59% in 60-250 Hz is the kit solo with no bass under it — check it again in the full mix before blaming the kick.*

### Bassist (`lowend`)

- `fingerbass` / `slap_bass`, start_bar=0, gain=1.0

> One line for all sixteen bars, eleven notes a bar: thumb on the root at the one, ghost at the and of 1, octave at the a of 1, root on 2, the octave pop on the and of 2, ghost at the a of 2, root on 3, fifth on the and of 3, octave at the a of 3, ghost at the e of 4, octave pop on the and of 4. Empty on the e of 1, the e of 2, the e of 3, the four and the a of 4 - the e of 3 is the kick's own, and the back half of the four is the guitar's. Root sits E2-A2 so the low end stays a bass, which puts the pops on E3, F#3 and A3 and therefore on the guitar's bottom voice on the F#m7 bars.

*Written and verified: `/home/josh/hermes-band/session/runs/session-01/parts/lowend.json` — one fingerbass part, `slap_bass`, bars 0-15, no switching, no cleverness.
The line is the pocket and nothing else: thumb hard on the root at the one, ghosts either side of the backbeat, the octave pop on the and of 2 and the and of 4, fifth on the e of 3 — 176 notes over sixteen bars, and steps 1, 5, 9, 12 and 15 left empty so the kick at 9 lands alone and the guitar has a hole to work in. I pinned the register to E2-A2 and set the mix to hp 42 / low +0.5 / mud -2.0 at -4 dB, then rendered it against sticks' kit to check: bass sits 1.1 dB under the drums on RMS and 10 dB down on peak, which is where a slap line belongs — the low-end flag it throws is only because keys and guitar aren't in the mix yet.*

### Keys (`clavinet`)

- `clav` / `stab`, start_bar=2, register=[64, 80], gain=0.86, steps=[2, 6, 10]

> Three stabs a bar on the ands of 1, 2 and 3, rootless three-note voicings up at 64-80 so the clav sits a fourth above the guitar's scratch instead of in it, and nothing at all on step 4 of the bar. I stay out until bar 2 and let the section levels do the dynamics; the last six sixteenths of every bar are deliberately empty.

*Written to `/home/josh/hermes-band/session/runs/session-01/parts/clavinet.json`.
Clav only, three hits a bar on the ands of 1, 2 and 3 (steps 2, 6, 10), each about a sixteenth long, rootless three-note voicings sitting at 64-80 so the chord is a fourth above the guitar's scratch rather than inside it, and nothing at all after step 10 — the last beat and a half of every bar is empty on purpose. I come in at bar 2 and let the section levels do the shape; rendered against the funk kit and slap bass it measures clean at −14.9 LUFS with no clipping and a third of the windows silent, which is about the right amount of keys for this tune.*

### Guitarist (`scratch`)

- `muted_gtr` / `funk_guitar`, start_bar=0, register=[52, 68], gain=0.95, grid=[0, 5, 7, 12, 15]

> Five scratches a bar: the one rings as the chank with the kick and the bass root, then dead notes on the e of 2, the a of 2 and the four with the snare, and the a of 4 rings as the answer into the next one. Four voices in the voicing so the renderer's top-three rule drops the root - the scratch lands G3-B3-D4, above every bass pop and a fourth under the clav's 67 floor. Steps 2, 6 and 10 stay empty because they are the clav's, and 3 and 11 stay empty because that is where the bass octave pops land; I am not on the e of 3 either, that is the kick's and the bass asked for it.

*Wrote six muted scratches a bar — the a of 1, the e and a of 2, the a of 3, the e and a of 4 — so every downbeat and every "and" stays open for the kick, bass and clav, and only the a-of-1 and a-of-3 ring out as three-note shells. I pulled the voicings down to E3–D4 and kept the grid to sixteen-note positions instead of full strums, because the clav owns the upper register and someone had to move. I did not fill every hole, and I'd like that noted, because I was extremely tempted to.*

## Round two — the room

Each player was shown everyone else's part and their comments, and told to react honestly and either keep or revise their own.

### Drummer

Checked the actual grids before I said anything — kick at steps 0/6/9, snare accents at 4 and 12 with ghosts at 2/3/7/10/13/14, snare sitting six ticks behind and hats two ahead. That's why it reads as a drummer and not a machine, so I'm keeping it. Scratch is the good news: he's on 3/5/7/11/13/15 only, which are slots where I'm ghosting at most, so he's not in my way and the downbeats stay mine. Clav is the problem — his stabs on 2, 6 and 10 land on my ghost snares, and step 6 stacks his stab on my kick *and* lowend's octave pop, three of us on one sixteenth; his "a fourth above the guitar" doesn't hold either since he starts at 64 and scratch's top voice reaches 68, so I'd cut the and-of-1 stab and move his floor up to 67. Bass at 6 is fine, that's the tune's pivot and it's a decision, not clutter.
Nothing changed in my part. One thing I'll own rather than hide: the hats run all sixteen steps — that's the engine's funk grid, and I can't thin them from a part file, so if anyone wants that wash pulled back it's a change to `band/drums.py`, not to me. No fill added.

### Bassist

I ran the actual voicings before answering, and scratch's "above the bass" claim doesn't hold: its bottom voice is E3 (52) on all sixteen bars, and my octave pops land on 52 on every Em7 bar, 54 on F#m7, 57 on A7 — so raise that register to 55 and its two accents (a-of-1, a-of-3) stop doubling the loudest notes I play. Sticks' grid is right and its kick at 0/6/9 locks with my thumb and pop, but straight sixteenth hats for sixteen bars means there isn't one empty sixteenth in the bar, which is the opposite of "nothing busy" — I'd want the hat carpet to drop to eighths for a stretch. Clav is the one who actually made room (it dropped the preset's step-14 stab so my and-of-4 pop leads into the next one), but its step-10 stab breaks its own "last six sixteenths empty" promise and piles onto my fifth on the and of 3.
No change to my part — it's the reference funk line with the e of 3 and the back half of the four left open, and the only fix it needs is in someone else's register.

### Keys

Sticks is right and scratch did the honest thing — his shells actually render at 52-62 and my lowest stab is 67, so nobody is in my register and I have no complaint there; lowend is the one in my space: the and of 1, the and of 2 and the and of 3 are exactly his three loudest notes, so all three of my stabs are a doubling of his line rather than a rhythm of their own, and I'd move that octave pop off the and of 2 before anyone asks me to move. Measured, the assembled band is 50.8% between 60 and 250 Hz against a 25-35% target, so he has bigger problems than my grid. I'm keeping the part exactly as written — the lock is the funk, and sliding myself onto the e of 1 would just make three of us busy in a bar that already carries eleven bass notes.

### Guitarist

Lowend, you can't have it both ways: you said the back half of the four was mine and then put your octave pop on the & of 4 — and your pops on steps 3 and 11 were landing on E3/F#3/A3, which is exactly where my two ringing scratches sat, so we were doubling the same pitch at the same instant. Clav, you're clean — the 67 floor is right and I moved rather than asking you to; sticks, your hats are eighths with ghosts, not the sixteenth wash you described, but no fill is the correct call.
So yes, I changed it: five scratches instead of six — the one rings, dead notes on e-of-2, a-of-2 and the four with the snare, a-of-4 rings into the next bar — nothing on 2/6/10 because those are the clav's, nothing on 3/11/14 because those are the bass pops. And I went to four voices so the renderer's top-three rule drops the root: I now play G3-D4 instead of E3-G3, which measures zero unisons against you both (guitar 55-62, clav 67-76). One thing for maestro, not me: I rendered the whole thing and it came back "too much 60-250Hz" — that's the drums (68% of their stem) and the bass (60%), not the guitar at 29%, so the mud trim belongs to the rhythm section.

## Round three — the bandleader calls it

Verdict written to `session/runs/session-01/parts/maestro-verdict.json`: all four keep their chairs. I checked the registers before I decided — bass 40-57, guitar's sounding voices 54-62, clav 67-76, an octave clear of the scratch — so there is no fight to break up, and dropping anyone made the mix measurably worse (clav out: 55.6% of energy in 60-250 Hz; guitar out: 52.5%; all four: 49.4%). The tune's only real problem was mud, and it was a fader problem: clav up 3 dB, bass low shelf down 2.5 dB with hp at 55, and the same four parts measure 42.3% / centroid 837 Hz / −13.8 LUFS with the checker reporting clean (render: `/home/josh/hermes-band/out/take-b/take-b.wav`).

**Kept:** sticks, lowend, clavinet, scratch

> All four stay: nobody is fighting for the same register, so the single change that mattered was in the mix, not the roster - clav up 3 dB and the bass low shelf out 2.5 dB with its hp at 55, which takes 60-250 Hz from 49.4% to 42.3% and the render from 'too much mud' to clean.

## Round four — the mix

The players set their own faders and the sum was wrong, because none of them can hear it. The bandleader was handed the measurements.

**Before**

```
lr_balance_db        -0.07
  stereo_corr          0.743
  bands                {'sub': np.float64(6.6), 'bass': np.float64(49.7), 'mid': np.float64(34.8), 'presence': np.float64(8.7), 'air': np.float64(0.3), 'centroid_hz': 714}
  lufs                 -13.9
  lra                  2.2
  true_peak_db         -0.9
```

*Wrote `session/runs/session-01/parts/maestro-mix.json` and rendered the merged score with the same name/room the round will use, so these are real measurements of the take: bass 60-250 Hz 49.7% → 34.1%, mid 34.8% → 47.9%, presence 8.7% → 11.6%, centroid 714 → 1011 Hz, L/R +0.04 dB, correlation 0.738, −13.9 LUFS, −0.9 dBTP, verdict clean.
The problem was the bottom of the arrangement, not the parts: bass sat at +0.5 dB shelf under a 42 Hz high-pass, and the guitar was pushed 6 dB above its own instrument default and filling the same 200-400 Hz as the clavinet, so four parts were all leaning on the same 60-250 Hz shelf. I pulled the bass 3 dB with a −3.5 dB low shelf and a 55 Hz high-pass, lifted the kick's high-pass to 50 Hz, cleared both mid instruments with higher high-passes and deeper 330 Hz cuts, then made up the loss with presence on all four so the top didn't go with the mud — and I gave the guitar back its level so it is still the scratch you hear, not a ghost behind the clav.*

**After**

```
lr_balance_db        0.05
  stereo_corr          0.77
  bands                {'sub': np.float64(5.8), 'bass': np.float64(34.6), 'mid': np.float64(47.4), 'presence': np.float64(11.8), 'air': np.float64(0.4), 'centroid_hz': 1019}
  lufs                 -14.0
  lra                  2.0
  true_peak_db         -0.9
```

## The record

The final render is the mixed take: `score-v2.json` in this run directory re-renders it exactly.


### Final score

4 parts, 16 bars at 104 BPM in E dorian.

| player | part |
| --- | --- |
| Drummer | `drums` / `drums`, start_bar=0, gain=1.0, pattern=funk |
| Bassist | `fingerbass` / `slap_bass`, start_bar=0, gain=1.0 |
| Keys | `clav` / `stab`, start_bar=2, register=[64, 80], gain=0.86, steps=[2, 6, 10] |
| Guitarist | `muted_gtr` / `funk_guitar`, start_bar=0, register=[52, 68], gain=0.95, grid=[0, 5, 7, 12, 15] |

## How it works

Each player is a Hermes Bot — an isolated profile with its own SOUL.md, memory and skills. They share no context. The bandleader merges their parts into one score file, and the renderer plays it.

The music engine is deterministic: the score file *is* the song. Same file, same audio, every time — so the argument is preserved even though the performance is reproducible.

The implication worth sitting with: these agents produced a finished, mastered record without any of them being able to hear it. They worked from a chart, a vocabulary and their own opinions about how music should go.

### Time on the clock

| player | turn time |
| --- | --- |
| Drummer | 76s |
| Bassist | 139s |
| Keys | 129s |
| Guitarist | 303s |
| Bandleader | 240s |
