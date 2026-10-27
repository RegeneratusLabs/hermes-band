"""Word-level timing for the film.

Two sources, combined:

* the **exact** extent of each line in the rendered vocal bus — vocals.py writes
  the measured synth duration of every line to `out/lines.json`, so the window is
  known rather than guessed, and
* whisper's word-level transcript of that same bus for the *shape* of the line.

Whisper's absolute times drift by up to ~0.5 s at the start of a take, so they are
only used as relative positions: each line's words are mapped onto that line's
measured window. Exact at the line level, right at the word level, and no
guessing from an envelope.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from build import LINES, BAR, BARS  # noqa: E402

OUT = os.path.join(HERE, "words.json")
LINES_JSON = os.path.join(os.path.dirname(HERE), "out", "lines.json")


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def main():
    durs = {int(k): v for k, v in json.load(open(LINES_JSON)).items()}
    wt = json.load(open(os.path.join(HERE, "whisper_words.json")))

    out, n_whisper = [], 0
    for bar in sorted(LINES):
        text = LINES[bar]
        canon = text.split()
        t0 = bar * BAR + 0.02
        t1 = t0 + durs[bar]

        # local candidate window — whisper may be early or late, so allow slack
        cand = [i for i, w in enumerate(wt)
                if t0 - 0.45 <= (w["t0"] + w["t1"]) / 2 <= t1 + 0.40]
        idx, p, ok = [], 0, True
        for w in canon:
            found = -1
            for k in range(p, min(p + 8, len(cand))):
                cw = norm(wt[cand[k]]["w"])
                if cw == norm(w) or (len(norm(w)) > 2 and cw.startswith(norm(w)[:3])):
                    found = k
                    break
            if found < 0:
                ok = False
                break
            idx.append(cand[found])
            p = found + 1
        words, how = None, "proportional"
        if ok and len(idx) == len(canon):
            ws = [wt[i] for i in idx]
            a0 = ws[0]["t0"]
            a1 = max(ws[-1]["t1"], a0 + 0.25)
            span = a1 - a0
            words = []
            for w in ws:
                f0 = min(1.0, max(0.0, (w["t0"] - a0) / span))
                f1 = min(1.0, max(f0 + 0.02, (w["t1"] - a0) / span))
                words.append({"w": w["w"], "t0": round(t0 + f0 * (t1 - t0), 3),
                              "t1": round(t0 + f1 * (t1 - t0), 3)})
            how = "whisper"
            n_whisper += 1
        if words is None:
            n = sum(len(w) + 1 for w in canon)
            acc, words = 0, []
            for w in canon:
                f0 = acc / n
                acc += len(w) + 1
                words.append({"w": w, "t0": round(t0 + f0 * (t1 - t0), 3),
                              "t1": round(t0 + (acc / n) * (t1 - t0), 3)})
        out.append({"bar": bar, "text": text, "t0": round(t0, 3), "t1": round(t1, 3),
                    "how": how, "words": words})
        print(f"bar {bar:2d} {t0:6.2f}-{t1:6.2f} {how:12s} {text}")

    json.dump({"bpm": 92, "bar": round(BAR, 5), "bars": BARS, "lines": out},
              open(OUT, "w"), indent=1)
    print(f"\n{n_whisper}/{len(out)} lines word-synced from whisper -> {OUT}")


if __name__ == "__main__":
    main()
