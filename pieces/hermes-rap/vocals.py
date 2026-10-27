"""Vocal side: synth each rap line with piper, fit it to its bar, build the bus."""
import os, sys, subprocess, wave
import numpy as np

OUT = os.environ.get("RAP_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
TTS = os.path.join(OUT, "tts")
VOICE = os.environ.get("RAP_VOICE", os.path.expanduser("~/.hermes/cache/piper-voices/en_US-ryan-high.onnx"))
SR = 44100
BPM = 92
BARS = 34
BAR = 4 * 60.0 / BPM


def read_wav(path):
    w = wave.open(path, "rb")
    n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
    raw = w.readframes(n)
    w.close()
    if sw == 2:
        a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    else:
        a = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    return a, sr


def write_wav(path, a, sr=SR):
    a = np.clip(a, -1.0, 1.0)
    w = wave.open(path, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(sr)
    w.writeframes((a * 32767).astype("<i2").tobytes())
    w.close()


def piper(text, path, length_scale):
    p = subprocess.run(
        ["piper", "-m", VOICE, "-f", path, "--length-scale", f"{length_scale:.3f}",
         "--sentence-silence", "0.02", "--noise-scale", "0.55", "--noise-w-scale", "0.7"],
        input=text.encode(), capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode()[-500:])


def trim(a, sr, thresh=0.012, pad=0.012):
    idx = np.where(np.abs(a) > thresh)[0]
    if len(idx) == 0:
        return a
    s = max(0, idx[0] - int(pad * sr))
    e = min(len(a), idx[-1] + int(pad * sr))
    return a[s:e]


def resample(a, sr_in, sr_out=SR):
    if sr_in == sr_out:
        return a
    n = int(round(len(a) * sr_out / sr_in))
    x = np.linspace(0, len(a) - 1, n)
    return np.interp(x, np.arange(len(a)), a).astype(np.float32)


def synth_fit(text, target_s, tag):
    """Synth until the line lands just under target duration."""
    path = os.path.join(TTS, f"{tag}.wav")
    scale = 0.88
    best = None
    for attempt in range(4):
        piper(text, path, scale)
        a, sr = read_wav(path)
        a = trim(a, sr)
        dur = len(a) / sr
        if best is None or abs(dur - target_s) < abs(best[1] - target_s):
            best = (a, dur, sr, scale)
        if dur <= target_s * 0.99:
            break
        scale = max(0.60, scale * (target_s / dur) * 0.995)
    a, dur, sr, scale = best
    a = resample(a, sr)
    # peak normalise each line, compressor comes later on the bus
    pk = np.abs(a).max()
    if pk > 0:
        a = a * (0.82 / pk)
    return a, dur, scale


def build(lines, hook_bars, out_path, dump=None):
    import json
    total = int((BARS * BAR + 3.0) * SR)
    rec = {}
    bus = np.zeros(total, np.float32)
    for bar, text in sorted(lines.items()):
        is_hook = bar in hook_bars
        target = BAR * (0.72 if len(text.split()) <= 4 else 0.90)
        a, dur, scale = synth_fit(text, target, f"bar{bar:02d}")
        start = int((bar * BAR + 0.02) * SR)
        bus[start:start + len(a)] += a
        rec[bar] = round(dur, 4)
        print(f"bar {bar:02d} dur={dur:.2f}s scale={scale:.2f} start={bar*BAR:.2f} "
              f"{'HOOK' if is_hook else '    '} | {text}")
    add_adlibs(bus)
    write_wav(out_path, bus)
    if dump:
        json.dump(rec, open(dump, "w"), indent=0)
        print("line durations ->", dump)
    print("vocal bus", out_path, round(len(bus) / SR, 2), "s")


# (bar, beat_offset, text, gain)
ADLIBS = [
    (1, 3.30, "yeah yeah", 0.30),
    (13, 3.55, "uh huh", 0.26),
    (25, 3.55, "huh", 0.30),
    (29, 3.60, "no doubt", 0.26),
]


def add_adlibs(bus):
    for bar, beat, text, gain in ADLIBS:
        a, dur, s = synth_fit(text, BAR * 0.30, f"ad_{bar}_{beat}")
        start = int((bar * BAR + beat * BAR / 4.0) * SR)
        end = min(len(bus), start + len(a))
        bus[start:end] += a[:end - start] * gain
        print(f"adlib @ bar {bar} beat {beat}: {text} ({dur:.2f}s)")


if __name__ == "__main__":
    from build import LINES, HOOK_BARS
    build(LINES, HOOK_BARS, os.path.join(OUT, "vocal_raw.wav"),
          dump=os.path.join(OUT, "lines.json"))
