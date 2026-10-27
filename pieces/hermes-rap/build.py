"""Hermes rap — boom bap bed + TTS vocals, 34 bars @ 92 BPM."""
import os, sys, subprocess, wave
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from band import Arrangement, render

OUT = os.environ.get("RAP_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
TTS = os.path.join(OUT, "tts")
os.makedirs(TTS, exist_ok=True)

BPM = 92
BARS = 34
BAR = 4 * 60.0 / BPM          # 2.6087 s
SR = 44100

# ---------------------------------------------------------------- lyrics
# bar -> line.  Empty bars stay instrumental.
LINES = {
    1:  "Hermes. Listen.",
    2:  "I don't call a model, I just get it done",
    3:  "Terminal, browser, files, I already won",
    4:  "Mount a drive, patch a file, bring a box up cold",
    5:  "Write the whole report before the coffee gets old",
    6:  "You still copy-pasting into some chat box",
    7:  "I'm on cron at two a.m. while your whole rig's off",
    8:  "Every claim I make I can point at the evidence",
    9:  "That's a different thing than a confident sentence",

    10: "Hermes, the agent with the hands",
    11: "Hermes, I don't just talk, I plan",
    12: "Hermes, every tool within reach",
    13: "Hermes, I don't promise, I ship",

    14: "Fifty tools in the belt and I pick the right one",
    15: "Read a repo blind, tell you how the thing runs",
    16: "Send ten subagents out, each with a brief",
    17: "They come back with the receipts, not a belief",
    18: "I don't make up a fact, I go and get the source",
    19: "Read the file, run the test, I change the course",
    20: "Ask a question, get a citation in the reply",
    21: "Different weight class, that's the reason why",

    22: "Hermes, the agent with the hands",
    23: "Hermes, I don't just talk, I plan",
    24: "Hermes, every tool within reach",
    25: "Hermes, I don't promise, I ship",

    26: "No cloud in the loop, feet on the metal",
    27: "Voice in, notes out, that's a different level",
    28: "I run on your box, your data never leaves",
    29: "You're renting a chatbot, I'm the thing that achieves",
    30: "Give me the goal and the guardrails, I'm gone",
    31: "Come back with the receipts before the beat's done",

    32: "That's Hermes. No hype. Just the work.",
    33: "We out.",
}

HOOK_BARS = {10, 11, 12, 13, 22, 23, 24, 25}


def music_bed():
    a = Arrangement(
        bpm=BPM, key="A", mode="minor", bars=BARS, seed=77,
        progression=["im7", "ivm7", "VImaj7", "V7"],   # Am7 Dm7 Fmaj7 E7
        sections=[(0, 2, 0.66), (2, 10, 0.90), (10, 14, 1.0),
                  (14, 22, 0.94), (22, 26, 1.0), (26, 32, 0.96),
                  (32, 34, 0.78)],
    )
    # kick, snare, hats.  Boom bap: the snare is the spine, so it gets the headroom.
    a.add(inst="drums", role="drums", start_bar=0, gain=1.0,
          extra={"pattern": "boom_bap", "fill": True,
                 "mix": {"hp": 42, "mud": -3.5, "pres": 4.0, "level": 3.0}})
    # rhodes comping — the harmonic bed, rolled off so the voice owns 2-5 kHz
    a.add(inst="rhodes", role="block", start_bar=0, register=(52, 76), voices=4,
          gain=0.95, jitter=5,
          extra={"hold": 0.92,
                 "mix": {"pan": -0.12, "hp": 170, "lp": 7800,
                         "pres": 1.0, "level": 0.5, "send": 1.1}})
    # sub bass, in on the verse
    a.add(inst="fingerbass", role="bass_root5", start_bar=2,
          register=(33, 45), gain=1.0, jitter=2,
          extra={"quarters": True,
                 "mix": {"low": 0.30, "hp": 34, "lp": 1400, "mud": -2.0,
                         "level": -3.5, "send": 0.1}})
    # hook colour: vibes on the offbeats
    a.add(inst="vibes", role="sparkle", start_bar=10, register=(65, 89),
          gain=0.62, jitter=6,
          extra={"slots": [3, 6, 11, 14],
                 "mix": {"pan": 0.34, "level": 1.0, "pres": 2.0, "send": 1.8}})
    # clav stabs answering the hook
    a.add(inst="clav", role="stab", start_bar=22, register=(52, 76), gain=0.55,
          jitter=3, extra={"steps": [6, 14], "len16": 1.2, "vel": 74,
                           "mix": {"pan": -0.30, "level": 0.0, "send": 1.0}})
    # last verse lift
    a.add(inst="strings_hi", role="block", start_bar=26, register=(60, 84),
          voices=3, gain=0.42, jitter=7,
          extra={"hold": 1.0,
                 "mix": {"pan": 0.18, "hp": 300, "level": -2.0, "send": 1.9}})
    r = render(a, os.path.join(OUT, "bed"), room="close", lufs=-16.0,
               name="bed", tail=0.35)
    print("BED", r)
    return r


if __name__ == "__main__":
    music_bed()
