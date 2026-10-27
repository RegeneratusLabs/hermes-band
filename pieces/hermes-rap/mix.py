"""Mix: vocal processing, sidechain duck, master."""
import os, subprocess, numpy as np
from vocals import read_wav, write_wav, SR

OUT = os.environ.get("RAP_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
BPM = 92


def ff(inp, out, af, extra=None):
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", inp, "-af", af,
           "-ar", str(SR), "-c:a", "pcm_s16le", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    return out


def read_stereo(path):
    import wave
    w = wave.open(path, "rb")
    n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
    raw = w.readframes(n)
    w.close()
    a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    a = a.reshape(-1, ch)
    if ch == 1:
        a = np.repeat(a, 2, axis=1)
    return a[:, :2], sr


def env_of(a, sr, atk=0.004, rel=0.150):
    """Fast-attack / slow-release envelope follower."""
    rect = np.abs(a)
    # simple one-pole smoothing, two different time constants
    ca = np.exp(-1.0 / (atk * sr))
    cr = np.exp(-1.0 / (rel * sr))
    out = np.zeros_like(rect)
    prev = 0.0
    for i in range(len(rect)):
        x = rect[i]
        c = ca if x > prev else cr
        prev = c * prev + (1 - c) * x
        out[i] = prev
    return out


def main():
    # ---- vocal chain: presence, low cut, glue compression, de-mud
    raw = os.path.join(OUT, "vocal_raw.wav")
    proc = os.path.join(OUT, "vocal_proc.wav")
    af = (
        "highpass=f=95,"
        "equalizer=f=260:t=q:w=1.0:g=-3.0,"   # de-mud
        "equalizer=f=1400:t=q:w=1.4:g=1.2,"   # body
        "equalizer=f=3200:t=q:w=1.1:g=3.5,"   # presence / intelligibility
        "equalizer=f=9500:t=h:w=2500:g=1.8,"  # air
        "acompressor=threshold=0.10:ratio=2.8:attack=8:release=160:makeup=2.0,"
        "alimiter=limit=0.95:level=disabled"
    )
    ff(raw, proc, af)
    vox, sr = read_wav(proc)

    bed, sr2 = read_stereo(os.path.join(OUT, "bed", "bed.wav"))
    n = min(len(bed), len(vox))
    bed, vox = bed[:n], vox[:n]

    # ---- sidechain: pull the bed back under the bars
    e = env_of(vox, SR)
    e = e / max(1e-9, np.percentile(e, 99.5))
    e = np.clip(e, 0, 1) ** 0.7
    duck = 1.0 - 0.42 * e

    # ---- vocal width: lead centre + 13 ms double panned out
    d = int(0.013 * SR)
    double = np.zeros_like(vox)
    double[d:] = vox[:-d] * 0.30
    lead = vox * 1.0

    dk = duck[:, None]
    # tempo-synced 1/8 dub taps: sheen and space, not a wash
    eighth = int(round((60.0 / BPM) / 2.0 * SR))
    tap1 = np.zeros_like(vox); tap1[eighth:] = vox[:-eighth] * 0.20
    tap2 = np.zeros_like(vox); tap2[2 * eighth:] = vox[:-2 * eighth] * 0.10

    mixL = bed[:, 0] * duck * 0.92 + lead * 0.90 + double * 0.55 + tap2 * 0.9 + tap1 * 0.25
    mixR = bed[:, 1] * duck * 0.92 + lead * 0.90 + double * 0.10 + tap1 * 0.9 + tap2 * 0.25
    mix = np.stack([mixL, mixR], axis=1)

    # normalise peak with headroom, loudnorm does the rest
    pk = np.abs(mix).max()
    mix = mix * (0.89 / pk)
    staged = os.path.join(OUT, "mix_stage.wav")
    w = __import__("wave").open(staged, "wb")
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
    w.close()

    final = os.path.join(OUT, "hermes-rap.wav")
    tmp = os.path.join(OUT, "mix_ln.wav")
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", staged,
                        "-af", "loudnorm=I=-14.0:TP=-1.5:LRA=9", "-ar", str(SR),
                        "-c:a", "pcm_s16le", tmp], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
    af2 = "alimiter=limit=0.89:level=disabled,afade=t=out:st=88.2:d=1.0"
    ff(tmp, final, af2)
    mp3 = os.path.join(OUT, "hermes-rap.mp3")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", final,
                    "-b:a", "256k", mp3], check=True)
    a, _ = read_wav(final)
    print("final", final, "dur", round(len(a) / SR, 2), "peak",
          round(20 * np.log10(np.abs(a).max()), 2), "dBFS")
    print("mp3", mp3, os.path.getsize(mp3))


if __name__ == "__main__":
    main()
