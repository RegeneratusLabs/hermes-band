"""The mixer and reverb: the parts that decide whether it sounds like a record."""
from __future__ import annotations

import numpy as np
import pytest

from band import mix, reverb


def test_profile_defaults_and_override():
    p = mix.profile("steel")
    assert p["level"] < 0                      # guitars are trimmed
    assert p["pres"] > 0                       # and lifted in presence
    p2 = mix.profile("steel", level=-9.0)
    assert p2["level"] == -9.0
    assert p2["pres"] == p["pres"]             # override is surgical


def test_unknown_instrument_gets_sane_defaults():
    p = mix.profile("kazoo")
    assert p == mix.DEFAULT


def test_pan_is_constant_power():
    mono = np.ones(1000)
    for p in (-1.0, -0.5, 0.0, 0.5, 1.0):
        st = mix.pan(mono, p)
        assert st.shape == (1000, 2)
        power = (st[:, 0] ** 2 + st[:, 1] ** 2)
        assert np.allclose(power, 1.0, atol=1e-5)


def test_pan_extremes():
    mono = np.ones(10)
    left = mix.pan(mono, -1.0)
    assert left[:, 1].max() == pytest.approx(0.0, abs=1e-6)
    right = mix.pan(mono, 1.0)
    assert right[:, 0].max() == pytest.approx(0.0, abs=1e-6)


def test_balance_equalises_channels():
    noisy = np.zeros((4000, 2))
    noisy[:, 0] = 0.5
    noisy[:, 1] = 0.1
    out = mix.balance(noisy, max_db=40.0)      # give it room to fully correct
    rl = np.sqrt((out[:, 0] ** 2).mean())
    rr = np.sqrt((out[:, 1] ** 2).mean())
    assert abs(20 * np.log10(rl / rr)) < 0.5


def test_balance_respects_its_limit():
    """Never correct by more than max_db, or a deliberate imbalance gets ruined."""
    noisy = np.zeros((4000, 2))
    noisy[:, 0] = 1.0
    noisy[:, 1] = 0.001
    out = mix.balance(noisy, max_db=3.0)
    rl = np.sqrt((out[:, 0] ** 2).mean())
    rr = np.sqrt((out[:, 1] ** 2).mean())
    assert 20 * np.log10(rl / rr) > 3.0        # still lopsided, just less so


def test_balance_handles_silence():
    assert mix.balance(np.zeros((100, 2))).shape == (100, 2)


def test_shape_preserves_length_and_sign():
    sr = 44100
    sig = np.sin(2 * np.pi * 220 * np.arange(sr) / sr).astype(np.float32)
    out = mix.shape(sig, sr, mix.profile("steel"))
    assert out.shape == sig.shape
    assert np.corrcoef(sig, out)[0, 1] > 0.8   # still the same signal


def test_shape_removes_energy_below_highpass():
    sr = 44100
    n = sr
    t = np.arange(n) / sr
    low = np.sin(2 * np.pi * 30 * t).astype(np.float32)
    out = mix.shape(low, sr, mix.profile("steel"))      # hp = 95 Hz
    assert np.sqrt((out ** 2).mean()) < 0.5 * np.sqrt((low ** 2).mean())


def test_exciter_adds_high_frequency_energy():
    sr = 44100
    t = np.arange(sr) / sr
    sig = np.sin(2 * np.pi * 220 * t).astype(np.float32) * 0.3
    out = mix.exciter(sig, sr, amount=0.3)
    def above_5k(x):
        S = np.abs(np.fft.rfft(x)) ** 2
        f = np.fft.rfftfreq(len(x), 1 / sr)
        return S[f > 5000].sum()
    assert above_5k(out) > above_5k(sig) * 2


def test_make_ir_shape_and_stereo_decorrelation():
    ir = reverb.make_ir(rt60=1.0, sr=22050, seed=1)
    assert ir.ndim == 2 and ir.shape[1] == 2
    assert len(ir) > 22050                     # at least a second of tail
    assert not np.allclose(ir[:, 0], ir[:, 1])  # decorrelated channels


def test_make_ir_decays():
    ir = reverb.make_ir(rt60=0.6, sr=22050, seed=2)
    head = np.abs(ir[int(0.05 * 22050):int(0.10 * 22050)]).mean()
    tail = np.abs(ir[-int(0.10 * 22050):]).mean()
    assert tail < head * 0.25


def test_apply_reverb_extends_the_tail():
    sr = 22050
    dry = np.zeros((sr, 2))
    dry[:1000, :] = 0.5
    ir = reverb.make_ir(rt60=0.8, sr=sr, seed=3)
    wet = reverb.apply_reverb(dry, ir, wet=0.3, sr=sr)
    assert len(wet) > len(dry)
    assert np.abs(wet[len(dry):]).max() > 0      # rings on past the input


def test_finish_keeps_output_in_range():
    sr = 22050
    n = sr
    dry = np.zeros((n, 2), np.float32)
    send = np.zeros((n, 2), np.float32)
    dry[:, :] = 0.2
    send[:, :] = 0.2
    out = mix.finish(dry, send, sr, room="dry", seed=0, fade_out=0.1)
    assert out.shape[1] == 2
    assert np.abs(out).max() <= 1.0
