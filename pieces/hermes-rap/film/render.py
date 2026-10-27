"""HERMES — "No Hype", the film.

A shot list, a virtual camera, one character rig, and the lyric sheet cut to the
vocal. Every cut lands on a bar; every word on screen lands on the word that is
being said.

    python3 render.py --still 12.5 30 62     # look at frames
    python3 render.py --all                  # render the film
"""
from __future__ import annotations

import json
import math
import os
import sys
import wave

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import common as C
from common import W, H, FPS, PW, PH, rgba, font, tracked, text_w, ease, lerp
from common import FONT_BLACK, FONT_BOLD, FONT_NARROW
from rig import draw_bot
from sets import SETS

BAR = 4 * 60.0 / 92.0
DUR = 89.05
NBARS = 34
OUT = os.path.join(os.path.dirname(HERE), "out")
FILM = os.path.dirname(HERE)


def bt(bar, beat=0.0):
    return bar * BAR + beat * BAR / 4.0


# ------------------------------------------------------------------ assets
def load_words():
    d = json.load(open(os.path.join(HERE, "words.json")))
    lines = d["lines"]
    out = []
    for i, L in enumerate(lines):
        nxt = lines[i + 1]["t0"] if i + 1 < len(lines) else DUR
        ws = L["words"]
        # hold each word until the next one starts: that is what karaoke does
        for k, w in enumerate(ws):
            w["hold"] = ws[k + 1]["t0"] if k + 1 < len(ws) else min(nxt, L["t1"] + 0.30)
        out.append({**L, "next": nxt})
    return out


def load_env():
    w = wave.open(os.path.join(OUT, "vocal_raw.wav"), "rb")
    a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    sr = w.getframerate()
    w.close()
    hop = int(sr / 200)
    n = len(a) // hop
    env = np.abs(a[:n * hop]).reshape(n, hop).max(axis=1)
    env = np.clip(env / (np.percentile(env, 99.5) + 1e-6), 0, 1) ** 0.65
    return env, 200.0


ENV, ENV_SR = None, 200.0
LINES = None
AVATARS = {}


def ensure():
    """Load the bus and the lyric sheet once, whoever calls first."""
    global ENV, ENV_SR, LINES
    if ENV is None:
        ENV, ENV_SR = load_env()
    if LINES is None:
        LINES = load_words()


def env_at(t):
    if ENV is None:
        ensure()
    i = int(t * ENV_SR)
    if i < 0 or i >= len(ENV):
        return 0.0
    return float(ENV[i])


def kick_at(t):
    """Boom bap kick lands on steps 0, 6 and 10 of every bar."""
    best = 0.0
    bar = int(t / BAR)
    for b in (bar - 1, bar):
        for step in (0, 6, 10):
            tk = b * BAR + step * BAR / 16.0
            dt = t - tk
            if 0 <= dt < 0.30:
                best = max(best, math.exp(-dt / 0.085))
    return best


# ------------------------------------------------------------------ camera
def project(fx0, fy0, h, s0, cx0, cy0, s, cx, cy):
    """Keep a figure locked to the plate while the camera moves."""
    px = (cx0 - W / 2) / s0 + fx0 / s0
    py = (cy0 - H / 2) / s0 + fy0 / s0
    fx = (px - (cx - W / 2) / s) * s
    fy = (py - (cy - H / 2) / s) * s
    return fx, fy, h * (s / s0)


class Cam:
    def __init__(self, s0, s1, cx0, cy0, cx1=None, cy1=None, ease_fn=ease):
        self.s0, self.s1 = s0, s1
        self.cx0, self.cy0 = cx0 * PW, cy0 * PH
        self.cx1 = cx0 * PW if cx1 is None else cx1 * PW
        self.cy1 = cy0 * PH if cy1 is None else cy1 * PH
        self.ease = ease_fn

    def at(self, f):
        f = self.ease(f)
        return (lerp(self.s0, self.s1, f), lerp(self.cx0, self.cx1, f),
                lerp(self.cy0, self.cy1, f))


# ------------------------------------------------------------------ overlays
def title_card(frame, a, sub="NO HYPE", small="A HERMES BAND RECORD"):
    if a <= 0.01:
        return
    lay = rgba(W, H)
    d = ImageDraw.Draw(lay)
    f1 = font(FONT_BLACK, 120)
    f2 = font(FONT_BLACK, 44)
    w1 = text_w(d, "HERMES", f1, spacing=10)
    tracked(d, ((W - w1) / 2, H * 0.105), "HERMES", f1, (255, 255, 255, int(255 * a)),
            spacing=10, stroke=3, stroke_fill=(0, 0, 0, int(150 * a)))
    w2 = text_w(d, sub, f2, spacing=16)
    tracked(d, ((W - w2) / 2, H * 0.105 + 176), sub, f2, (255, 107, 26, int(255 * a)),
            spacing=16)
    d.line([(W * 0.34, H * 0.105 + 244), (W * 0.66, H * 0.105 + 244)],
           fill=(255, 255, 255, int(120 * a)), width=2)
    f3 = font(FONT_BOLD, 30)
    w3 = text_w(d, small, f3, spacing=6)
    tracked(d, ((W - w3) / 2, H * 0.105 + 262), small, f3, (210, 210, 220, int(190 * a)),
            spacing=6)
    frame.alpha_composite(lay)


def lyric(frame, t):
    """The words, always. Two lines max, current word lit."""
    cur = None
    for L in LINES:
        if L["t0"] - 0.06 <= t:
            cur = L
        else:
            break
    if cur is None:
        return
    if t > cur["next"] + 0.05:
        return
    words = cur["words"]
    active = -1
    for i, w in enumerate(words):
        if w["t0"] - 0.02 <= t < w["hold"]:
            active = i
            break
    if active < 0:
        for i, w in enumerate(words):
            if w["t0"] - 0.02 <= t:
                active = i

    size = 58 if len(cur["text"]) > 34 else 68
    f = font(FONT_BLACK, size)
    probe = ImageDraw.Draw(rgba(4, 4))
    sp = 1.5
    widths = [probe.textlength(w["w"] + " ", font=f) for w in words]
    total = sum(widths)
    x = (W - total) / 2
    y = H * 0.845
    lay = rgba(W, H)
    d = ImageDraw.Draw(lay)
    # plate behind the words so they hold against any frame
    d.rounded_rectangle([x - 40, y - 22, x + total + 40, y + size + 22],
                        radius=16, fill=(0, 0, 0, 130))
    for i, w in enumerate(words):
        lit = (i == active)
        col = (255, 138, 43, 255) if lit else (240, 240, 245, 235)
        d.text((x, y + (2 if lit else 0)), w["w"], font=f, fill=col,
               stroke_width=4 if lit else 3, stroke_fill=(0, 0, 0, 220))
        if lit:
            d.rectangle([x + 2, y + size + 10, x + widths[i] - 12, y + size + 16],
                        fill=(255, 107, 26, 210))
        x += widths[i]
    frame.alpha_composite(lay)


def flash(frame, a, colour=(255, 240, 220)):
    if a <= 0.01:
        return
    lay = Image.new("RGBA", (W, H), colour + (int(255 * min(1.0, a)),))
    frame.alpha_composite(lay)


def stamp(frame, text, a, y=0.30, colour=(255, 107, 26)):
    """A hard graf slam: big, tight, slightly rotated."""
    if a <= 0.01:
        return
    lay = rgba(W, H)
    d = ImageDraw.Draw(lay)
    f = font(FONT_BLACK, 168)
    w = text_w(d, text, f, spacing=4)
    sc = 1.0 + 0.10 * (1 - a)
    lay = lay.resize((int(W), int(H)), Image.BILINEAR)
    sub = rgba(W, H)
    sd = ImageDraw.Draw(sub)
    tracked(sd, ((W - w * sc) / 2, H * y), text, f, (0, 0, 0, 0), spacing=4)
    # draw twice: black outline then fill
    tracked(sd, ((W - w * sc) / 2, H * y), text, f,
            colour + (int(255 * a),), spacing=4, stroke=10, stroke_fill=(0, 0, 0, int(235 * a)))
    sub = sub.rotate(-3, resample=Image.BICUBIC, center=(W / 2, H * y))
    frame.alpha_composite(sub)


def money(frame, t, n=70, seed=5):
    r = np.random.RandomState(seed)
    lay = rgba(W, H)
    d = ImageDraw.Draw(lay)
    for i in range(n):
        x0 = r.uniform(0, 1)
        sp = r.uniform(0.05, 0.16)
        ph = r.uniform(0, 1)
        w0 = r.uniform(16, 30)
        sway = math.sin(t * r.uniform(1.2, 3.0) + i) * 26
        y = ((t * sp + ph) % 1.15 - 0.08) * H
        x = x0 * W + sway
        ang = math.sin(t * 2.0 + i) * 0.5
        cx, cy = x + w0 / 2, y + w0 * 0.28
        pts = []
        for dx, dy in ((-w0 / 2, -w0 * 0.28), (w0 / 2, -w0 * 0.28),
                       (w0 / 2, w0 * 0.28), (-w0 / 2, w0 * 0.28)):
            pts.append((cx + dx * math.cos(ang) - dy * math.sin(ang),
                        cy + dx * math.sin(ang) + dy * math.cos(ang)))
        d.polygon(pts, fill=(96, 132, 92, 210))
        d.line(pts + [pts[0]], fill=(140, 176, 132, 220), width=1)
    frame.alpha_composite(lay)


def rival(frame, fx, fy, h, crack=0.0, dead=False):
    """The other one: a beige chat box on a stool. `fy` is the stool's base."""
    lw, lh = int(h * 0.95), int(h * 1.02)
    lay = rgba(lw, lh)
    d = ImageDraw.Draw(lay)
    cx = lw / 2
    head_h = h * 0.46
    top = lh - h          # head top
    body = (172, 163, 146) if not dead else (88, 84, 78)
    d.rounded_rectangle([cx - h * 0.27, top, cx + h * 0.27, top + head_h],
                        radius=h * 0.055, fill=body)
    d.polygon([(cx - h * 0.10, top + head_h), (cx + h * 0.05, top + head_h),
               (cx - h * 0.14, top + head_h + h * 0.10)], fill=body)
    scr = (54, 74, 68) if not dead else (26, 28, 30)
    d.rounded_rectangle([cx - h * 0.215, top + h * 0.07, cx + h * 0.215,
                         top + h * 0.30], radius=h * 0.022, fill=scr)
    for k in range(3):
        d.ellipse([cx - h * 0.10 + k * h * 0.072, top + h * 0.165,
                   cx - h * 0.10 + k * h * 0.072 + h * 0.046, top + h * 0.211],
                  fill=(118, 196, 172) if not dead else (46, 50, 50))
    # stool
    d.rectangle([cx - h * 0.045, top + head_h + h * 0.09, cx + h * 0.045, lh - h * 0.09],
                fill=(96, 84, 66))
    d.ellipse([cx - h * 0.20, lh - h * 0.12, cx + h * 0.20, lh - h * 0.02],
              fill=(74, 64, 50))
    if crack > 0:
        r = np.random.RandomState(9)
        for k in range(7):
            a0 = r.uniform(0, 6.28)
            d.line([(cx, top + h * 0.19),
                    (cx + math.cos(a0) * h * 0.30, top + h * 0.19 + math.sin(a0) * h * 0.24)],
                   fill=(16, 14, 14, int(210 * crack)), width=max(2, int(h * 0.010)))
    frame.alpha_composite(lay, (int(fx - cx), int(fy - lh)))


def weigh_in(frame, t, a):
    """Burn #4: different weight class."""
    if a <= 0.01:
        return
    lay = rgba(W, H)
    d = ImageDraw.Draw(lay)
    d.rectangle([0, 0, W, H], fill=(8, 8, 10, int(230 * a)))
    f_lbl = font(FONT_BLACK, 34)
    f_num = font(FONT_BLACK, 132)
    # two scales
    for i, (x, label, val, col) in enumerate([
            (W * 0.26, "A CHATBOT", "0", (150, 150, 160)),
            (W * 0.74, "HERMES", "51", (255, 107, 26))]):
        cx = x
        base = H * 0.78
        d.rounded_rectangle([cx - W * 0.15, base - 18, cx + W * 0.15, base],
                            radius=14, fill=(28, 28, 34, int(255 * a)))
        d.rounded_rectangle([cx - W * 0.13, base - H * 0.06, cx + W * 0.13, base - 18],
                            radius=10, fill=(14, 14, 18, int(255 * a)))
        wl = text_w(d, label, f_lbl, spacing=3)
        tracked(d, (cx - wl / 2, base - H * 0.135), label, f_lbl,
                (210, 210, 220, int(255 * a)), spacing=3)
        wn = text_w(d, val, f_num)
        d.text((cx - wn / 2, base - H * 0.115), val, font=f_num, fill=col + (int(255 * a),))
        fsub = font(FONT_BLACK, 30)
        sub = "TOOLS IN THE BELT"
        ws2 = text_w(d, sub, fsub, spacing=3)
        tracked(d, (cx - ws2 / 2, base - H * 0.155), sub, fsub,
                (200, 200, 212, int(230 * a)), spacing=3)
    f_t = font(FONT_BLACK, 76)
    wt = text_w(d, "DIFFERENT WEIGHT CLASS", f_t, spacing=4)
    tracked(d, ((W - wt) / 2, H * 0.16), "DIFFERENT WEIGHT CLASS", f_t,
            (255, 255, 255, int(255 * a)), spacing=4, stroke=3,
            stroke_fill=(0, 0, 0, int(200 * a)))
    frame.alpha_composite(lay)


def lease(frame, t, a, tear):
    """Burn #5: the rip. A subscription agreement, torn down the middle."""
    if a <= 0.01:
        return
    lay = rgba(W, H)
    d = ImageDraw.Draw(lay)
    pw, phh = W * 0.33, H * 0.44
    top = H * 0.27
    gap = tear * W * 0.115
    jag = 0.0
    r = np.random.RandomState(3)
    teeth = [r.uniform(-14, 14) for _ in range(9)]
    for side in (0, 1):
        if side == 0:
            x0 = W / 2 - pw - gap
            box = [x0, top, x0 + pw, top + phh]
        else:
            x0 = W / 2 + gap
            box = [x0, top, x0 + pw, top + phh]
        # sheet with a ragged edge on the side facing the tear
        pts = [(box[0], box[1]), (box[0] + pw, box[1])]
        for k, off in enumerate(teeth[::-1] if side == 0 else teeth):
            yy = box[1] + phh * (k + 1) / (len(teeth) + 1)
            pts.append((box[0] + pw + (off if side == 1 else 0), yy))
        pts.append((box[0] + pw, box[1] + phh))
        pts.append((box[0], box[1] + phh))
        if side == 0:
            pts = [(box[0] + pw, box[1])] + [(box[0] + pw + off, box[1] + phh * (k + 1) / (len(teeth) + 1)) for k, off in enumerate(teeth)] + [(box[0] + pw, box[1] + phh), (box[0], box[1] + phh), (box[0], box[1])]
        d.polygon(pts, fill=(236, 232, 222, int(252 * a)))
        for k in range(9):
            yy = box[1] + 38 + k * 42
            d.line([(box[0] + 30, yy), (box[0] + pw - 30 - (0 if k % 3 else 80), yy)],
                   fill=(122, 118, 110, int(190 * a)), width=6)
        if side == 0:
            f = font(FONT_BLACK, 34)
            d.text((box[0] + 30, box[1] + phh - 104), "SUBSCRIPTION", font=f,
                   fill=(46, 46, 52, int(255 * a)))
            d.text((box[0] + 30, box[1] + phh - 64), "AGREEMENT", font=f,
                   fill=(190, 60, 40, int(255 * a)))
    # the tear itself: a hot line down the split, plus paper shards coming off it
    if tear > 0.15:
        rr = np.random.RandomState(17)
        for k in range(16):
            yy = H * 0.27 + (H * 0.44) * (k / 16)
            wob = rr.uniform(-10, 10)
            lay2 = ImageDraw.Draw(lay)
            lay2.line([(W / 2 - gap * 0.5 + wob, yy - 12),
                       (W / 2 - gap * 0.5 + wob, yy + 12)],
                      fill=(255, 214, 150, int(190 * tear)), width=3)
            lay2.line([(W / 2 + gap * 0.5 + wob, yy - 12),
                       (W / 2 + gap * 0.5 + wob, yy + 12)],
                      fill=(255, 214, 150, int(190 * tear)), width=3)
        for k in range(22):
            sx = W / 2 + rr.uniform(-gap * 1.4, gap * 1.4)
            sy = H * 0.30 + rr.uniform(0, H * 0.40) - tear * H * 0.10 * rr.uniform(0.3, 1.0)
            sz = rr.uniform(5, 15)
            lay2 = ImageDraw.Draw(lay)
            lay2.polygon([(sx, sy), (sx + sz, sy + sz * 0.5),
                          (sx + sz * 0.4, sy + sz)], fill=(238, 233, 222, int(230 * tear)))
    f_t = font(FONT_BLACK, 58)
    if tear > 0.35:
        wt = text_w(d, "RENTED, NOT OWNED", f_t, spacing=4)
        tracked(d, ((W - wt) / 2, H * 0.14), "RENTED, NOT OWNED", f_t,
                (255, 255, 255, int(235 * C.smooth(tear, 0.35, 0.8))), spacing=4,
                stroke=4, stroke_fill=(0, 0, 0, 200))
    frame.alpha_composite(lay)


# ------------------------------------------------------------------ shots
def char_at(frame, name, plate, s, cx, cy, spec, t):
    """Draw the bot locked to the plate."""
    s0, cx0, cy0 = spec["_s0"], spec["_cx0"], spec["_cy0"]
    fx, fy, hh = project(spec["x"] * W, spec["y"] * H, spec["h"], s0, cx0, cy0, s, cx, cy)
    bar = int(t / BAR)
    pose = spec["pose"](bar, t) if callable(spec["pose"]) else spec["pose"]
    mouth = env_at(t)
    squint = 1.0 if (callable(spec.get("squint")) and spec["squint"](bar)) else 0.0
    blink = 1.0 if ((t * 0.37) % 1.0) > 0.973 else 0.0
    tilt = math.sin((t % (BAR / 4)) / (BAR / 4) * math.pi) * 3.0 * (0.4 + kick_at(t))
    bot = draw_bot(int(hh), pose=pose, mouth=mouth, blink=blink, squint=squint,
                   glow=0.7 + 0.5 * kick_at(t),
                   look=math.sin(t * 0.7) * 0.35, tilt=tilt,
                   mic=spec.get("mic", False),
                   walking=spec.get("walking", 0.0))
    px, py = int(fx - bot.size[0] / 2), int(fy - bot.size[1])

    # contact shadow: a flat figure floats without one
    sh = rgba(int(hh * 0.9), int(hh * 0.26))
    ImageDraw.Draw(sh).ellipse([0, 0, sh.size[0] - 1, sh.size[1] - 1],
                               fill=(0, 0, 0, int(150 * spec.get("shadow", 1.0))))
    sh = sh.filter(ImageFilter.GaussianBlur(hh * 0.030))
    frame.alpha_composite(sh, (int(fx - sh.size[0] / 2), int(fy - sh.size[1] * 0.42)))

    # light wrap: bleed the plate over the figure's edge. This is the difference
    # between a cut-out and something that was in the room.
    bw2, bh2 = bot.size
    wrap = frame.crop((px, py, px + bw2, py + bh2)).filter(
        ImageFilter.GaussianBlur(max(2, int(hh * 0.012))))
    a = bot.split()[3]
    ring = ImageChops.subtract(a.filter(ImageFilter.GaussianBlur(max(1, int(hh * 0.004)))),
                               a)
    ring = ring.point(lambda v: 120 if v > 40 else 0)
    wrap.putalpha(ring)
    frame.alpha_composite(wrap, (px, py))
    frame.alpha_composite(bot, (px, py))


SHOTS = [
    # (b0, b1, set, Cam, char-spec, extras)
    dict(b0=0, b1=2, st="alley",
         cam=Cam(1.04, 1.14, 0.50, 0.50, 0.52, 0.485),
         ch=dict(x=0.44, y=0.865, h=600, pose="idle", walking=0.4),
         ex=["fadein", "title"]),
    dict(b0=2, b1=6, st="alley",
         cam=Cam(1.10, 1.26, 0.47, 0.50, 0.475, 0.495),
         ch=dict(x=0.42, y=0.885, h=700, pose="point", walking=0.0)),
    dict(b0=6, b1=7, st="lab",
         cam=Cam(1.06, 1.14, 0.44, 0.60),
         ch=dict(x=0.30, y=0.855, h=660, pose="fist", squint=lambda b: True),
         ex=["rival", "flash"]),
    dict(b0=7, b1=8, st="lab",
         cam=Cam(1.36, 1.44, 0.36, 0.42),
         ch=dict(x=0.33, y=1.02, h=1040, pose="fist",
                 squint=lambda b: True),
         ex=["clock"]),
    dict(b0=8, b1=9, st="lab",
         cam=Cam(1.12, 1.20, 0.52, 0.60),
         ch=dict(x=0.50, y=0.86, h=690, pose="palm"), ex=[]),
    dict(b0=9, b1=10, st="lab",
         cam=Cam(1.10, 1.18, 0.50, 0.58),
         ch=dict(x=0.47, y=0.865, h=700, pose="point", squint=lambda b: True),
         ex=["bubble"]),
    dict(b0=10, b1=14, st="stage",
         cam=Cam(1.06, 1.22, 0.50, 0.50),
         ch=dict(x=0.50, y=0.895, h=760, pose="mic", mic=True),
         ex=["money", "hookstamp"]),
    dict(b0=14, b1=16, st="lab",
         cam=Cam(1.14, 1.06, 0.60, 0.60, 0.55, 0.60),
         ch=dict(x=0.60, y=0.865, h=700, pose="point"), ex=["belt"]),
    dict(b0=16, b1=18, st="rooftop",
         cam=Cam(1.08, 1.20, 0.46, 0.52),
         ch=dict(x=0.42, y=0.885, h=700, pose="wide"), ex=["tri"]),
    dict(b0=18, b1=20, st="lab",
         cam=Cam(1.22, 1.32, 0.40, 0.58),
         ch=dict(x=0.36, y=0.95, h=900, pose="palm"), ex=[]),
    dict(b0=20, b1=21, st="lab",
         cam=Cam(1.30, 1.40, 0.42, 0.56),
         ch=dict(x=0.38, y=0.97, h=960, pose="point"), ex=[]),
    dict(b0=21, b1=22, st="lab", cam=Cam(1.12, 1.12, 0.50, 0.60),
         ch=dict(x=0.50, y=0.87, h=680, pose="idle"), ex=["weigh"]),
    dict(b0=22, b1=26, st="stage",
         cam=Cam(1.10, 1.05, 0.50, 0.50),
         ch=dict(x=0.52, y=0.905, h=780, pose="mic", mic=True),
         ex=["money", "avatars", "hookstamp"]),
    dict(b0=26, b1=29, st="rooftop",
         cam=Cam(1.24, 1.06, 0.40, 0.52, 0.44, 0.50),
         ch=dict(x=0.36, y=0.88, h=700, pose="wide"), ex=["tri"]),
    dict(b0=29, b1=30, st="rooftop",
         cam=Cam(1.14, 1.22, 0.48, 0.50),
         ch=dict(x=0.45, y=0.90, h=740, pose="cross", squint=lambda b: True),
         ex=["lease"]),
    dict(b0=30, b1=32, st="alley",
         cam=Cam(1.08, 1.20, 0.46, 0.50),
         ch=dict(x=0.43, y=0.885, h=700, pose="idle", walking=1.0), ex=[]),
    dict(b0=32, b1=34, st="alley",
         cam=Cam(1.16, 1.02, 0.44, 0.50, 0.50, 0.50),
         ch=dict(x=0.43, y=0.89, h=700, pose="point"), ex=["endcard"]),
]


def shot_at(t):
    bar = t / BAR
    for i, sh in enumerate(SHOTS):
        if sh["b0"] <= bar < sh["b1"]:
            return i, sh
    return len(SHOTS) - 1, SHOTS[-1]


# ------------------------------------------------------------------ frame
_PLATES = {}


def plates():
    if not _PLATES:
        for k, fn in SETS.items():
            _PLATES[k] = np.asarray(fn().convert("RGB"), np.uint8)
    return _PLATES


def frame_at(t, seed=0):
    ensure()
    P = plates()
    idx, sh = shot_at(t)
    span = (sh["b1"] - sh["b0"]) * BAR
    lt = (t - sh["b0"] * BAR) / max(1e-6, span)
    s, cx, cy = sh["cam"].at(lt)
    # handheld drift, scaled so it reads as weight not as shake
    hx, hy = C.handheld(t, seed=idx, amp=2.6 * s)
    arr = C.warp(P[sh["st"]], s, cx + hx, cy + hy)
    frame = Image.fromarray(arr).convert("RGBA")

    spec = dict(sh["ch"])
    spec["_s0"] = sh["cam"].s0
    spec["_cx0"] = sh["cam"].cx0
    spec["_cy0"] = sh["cam"].cy0

    ex = sh.get("ex", [])
    local = t - sh["b0"] * BAR

    if "rival" in ex:
        fx, fy, hh = project(0.775 * W, 0.995 * H, 620, spec["_s0"], spec["_cx0"],
                             spec["_cy0"], s, cx + hx, cy + hy)
        rival(frame, fx, fy, hh, crack=min(1.0, max(0.0, (local - 0.55) / 0.25)),
              dead=local > 0.8)
        tag = rgba(W, H)
        tdw = ImageDraw.Draw(tag)
        fq = font(FONT_BLACK, 30)
        lbl = "A CHAT BOX"
        wid = text_w(tdw, lbl, fq, 3)
        tdw.rounded_rectangle([fx - wid / 2 - 16, fy - hh - 62,
                               fx + wid / 2 + 16, fy - hh - 10],
                              radius=6, fill=(20, 20, 24, 220))
        tracked(tdw, (fx - wid / 2, fy - hh - 56), lbl, fq, (200, 200, 210, 235), spacing=3)
        frame.alpha_composite(tag)

    char_at(frame, "hermes", P[sh["st"]], s, cx + hx, cy + hy, spec, t)

    if "money" in ex:
        money(frame, t)
    if "avatars" in ex:
        band_avatars(frame, t)
    if "title" in ex:
        title_card(frame, C.smooth(t, 2.4, 3.0) * (1 - C.smooth(t, 4.9, 5.6)))
    if "endcard" in ex:
        endcard(frame, t)

    if "weigh" in ex:
        weigh_in(frame, t, C.smooth(t, bt(21), bt(21, 0.35)))
    if "lease" in ex:
        lease(frame, t, C.smooth(t, bt(29), bt(29, 0.2)),
              C.smooth(t, bt(29, 2.0), bt(29, 3.2)))
    if "hookstamp" in ex:
        for b in (sh["b0"], sh["b0"] + 2):
            d = t - b * BAR
            if 0 <= d < 1.1:
                stamp(frame, "HERMES", 1 - C.smooth(d, 0.55, 1.1) if d < 0.55 else 1 - (d - 0.55) / 0.55)
    if "bubble" in ex:
        bub = bt(9, 1.6)
        if t > bub:
            pop = C.smooth(t, bub, bub + 0.25)
            stamp(frame, "POP", min(1.0, pop) * (1 - C.smooth(t, bub + 0.5, bub + 1.0)),
                  y=0.24)
    if "flash" in ex:
        fl = t - bt(6, 1.5)
        if 0 <= fl < 0.36:
            flash(frame, 0.55 * math.exp(-fl / 0.075) if fl < 0.18 else 0.55 * math.exp(-(fl) / 0.09))
    if "clock" in ex:
        clock(frame, t)
    if "belt" in ex:
        belt_label(frame, t)
    if "tri" in ex:
        tri_lines(frame, t)

    # burns punch the frame
    if sh.get("squint") and sh["st"] == "lab":
        pass

    lyric(frame, t)

    if "fadein" in ex:
        a = 1 - C.smooth(t, 0.0, 1.4)
        flash(frame, a, (0, 0, 0))
    if "endcard" in ex:
        flash(frame, C.smooth(t, 86.4, 88.6), (0, 0, 0))

    # a last veil of air over everything, warm on the light side, cool on the other
    air = np.zeros((H, W, 4), np.float32)
    ramp = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    air[..., 0], air[..., 1], air[..., 2] = 255, 196, 150
    air[..., 3] = 9 + 10 * ramp
    frame.alpha_composite(Image.fromarray(air.astype(np.uint8), "RGBA"))

    bars = 0.055
    out = C.finish(frame, seed=int(t * FPS), bars=bars,
                   ca=1.4 + 2.6 * kick_at(t), grain=0.0125, vig=0.44)
    return out


# ------------------------------------------------------------------ extra overlays
def clock(frame, t):
    a = 1.0
    lay = rgba(W, H)
    d = ImageDraw.Draw(lay)
    cx, cy, r = W * 0.80, H * 0.30, 74
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(16, 16, 20, 210),
              outline=(70, 72, 84, 230), width=4)
    for k in range(12):
        aa = k * math.pi / 6
        d.line([(cx + math.cos(aa) * (r - 10), cy + math.sin(aa) * (r - 10)),
                (cx + math.cos(aa) * (r - 22), cy + math.sin(aa) * (r - 22))],
               fill=(120, 122, 136, 220), width=3)
    # 02:00, both hands on the two
    d.line([(cx, cy), (cx, cy - r * 0.52)], fill=(255, 107, 26, 240), width=6)
    d.line([(cx + r * 0.34, cy + r * 0.10), (cx + r * 0.20, cy + r * 0.26)],
           fill=(255, 107, 26, 240), width=6)
    f = font(FONT_BLACK, 40)
    d.text((cx - 52, cy + r + 18), "02:00", font=f, fill=(255, 107, 26, 235))
    frame.alpha_composite(lay)


def belt_label(frame, t):
    a = C.smooth(t, bt(14, 3.0), bt(14, 3.6))
    f = font(FONT_BLACK, 44)
    tracked_label(frame, "FIFTY TOOLS", a, (W * 0.10, H * 0.14))


def tracked_label(frame, text, a, xy):
    if a <= 0.01:
        return
    lay = rgba(W, H)
    d = ImageDraw.Draw(lay)
    f = font(FONT_BLACK, 44)
    d.rounded_rectangle([xy[0] - 18, xy[1] - 12, xy[0] + text_w(d, text, f, 3) + 18,
                         xy[1] + 62], radius=8, fill=(255, 107, 26, int(220 * a)))
    tracked(d, xy, text, f, (12, 12, 14, int(255 * a)), spacing=3)
    frame.alpha_composite(lay)


def tri_lines(frame, t):
    """Three quick diagonal slashes: the subagents going out."""
    for k, b in enumerate((bt(16, 2.0), bt(17, 2.0), bt(18, 0.0))):
        d = t - b
        if -0.1 < d < 0.45:
            a = min(1.0, (d + 0.1) / 0.15) * (1 - max(0.0, d) / 0.45)
            lay = rgba(W, H)
            dr = ImageDraw.Draw(lay)
            for j in range(3):
                x = W * (0.20 + j * 0.16 + k * 0.03)
                dr.line([(x, H * 0.20), (x + W * 0.10, H * 0.72)],
                        fill=(255, 138, 43, int(150 * a)), width=7)
            frame.alpha_composite(lay)


def band_avatars(frame, t):
    """The band, at the front of the crowd."""
    names = ["sticks", "lowend", "clavinet", "scratch", "maestro"]
    if not AVATARS:
        for n in names:
            p = os.path.abspath(os.path.join(HERE, "..", "..", "..", "session", "avatars", f"{n}.png"))
            AVATARS[n] = Image.open(p).convert("RGBA")
    for i, n in enumerate(names):
        bob = math.sin(t * 3.0 + i * 1.1) * 10 + kick_at(t) * 14
        sz = 96
        y = H * 0.995 - sz - bob
        x = W * (0.12 + i * 0.19) + (i % 2) * 14
        av = AVATARS[n].resize((sz, sz), Image.LANCZOS)
        frame.alpha_composite(av, (int(x), int(y)))


def endcard(frame, t):
    a = C.smooth(t, 85.9, 86.8)
    if a <= 0.01:
        return
    lay = rgba(W, H)
    d = ImageDraw.Draw(lay)
    f1 = font(FONT_BLACK, 118)
    f2 = font(FONT_BLACK, 40)
    f3 = font(FONT_BOLD, 30)
    w1 = text_w(d, "HERMES", f1, 8)
    tracked(d, ((W - w1) / 2, H * 0.34), "HERMES", f1, (255, 255, 255, int(250 * a)),
            spacing=8, stroke=2, stroke_fill=(0, 0, 0, int(120 * a)))
    w2 = text_w(d, "NO HYPE", f2, 14)
    tracked(d, ((W - w2) / 2, H * 0.34 + 150), "NO HYPE", f2, (255, 107, 26, int(250 * a)),
            spacing=14)
    d.line([(W * 0.36, H * 0.34 + 212), (W * 0.64, H * 0.34 + 212)],
           fill=(255, 255, 255, int(90 * a)), width=2)
    line = "beat, vocal and mix built with hermes-band"
    w3 = text_w(d, line, f3, 2)
    tracked(d, ((W - w3) / 2, H * 0.34 + 232), line, f3,
            (226, 226, 236, int(245 * a)), spacing=2)
    frame.alpha_composite(lay)


# ------------------------------------------------------------------ main
def render_still(t):
    return frame_at(t).convert("RGB")


def worker(args):
    i, fps = args
    t = i / fps
    im = frame_at(t, seed=i)
    p = os.path.join(HERE, "frames", f"f{i:05d}.jpg")
    im.save(p, quality=93, subsampling=1)
    return p


def main():
    global ENV, LINES
    ENV, ENV_SR = load_env()
    LINES = load_words()
    if "--still" in sys.argv:
        for s in sys.argv[sys.argv.index("--still") + 1:]:
            t = float(s)
            im = render_still(t)
            p = os.path.join("/tmp", f"still_{t:06.2f}.png")
            im.save(p)
            print("wrote", p)
        return
    if "--all" in sys.argv:
        # threads, not processes: every heavy step here (PIL and numpy) releases
        # the GIL, and forkserver pools do not survive this sandbox
        from concurrent.futures import ThreadPoolExecutor
        os.makedirs(os.path.join(HERE, "frames"), exist_ok=True)
        n = int(DUR * FPS)
        jobs = [(i, FPS) for i in range(n)]
        done = 0
        with ThreadPoolExecutor(max_workers=6) as pool:
            for _ in pool.map(worker, jobs):
                done += 1
                if done % 120 == 0:
                    print(f"  {done}/{n}", flush=True)
        print("frames done")


if __name__ == "__main__":
    main()
