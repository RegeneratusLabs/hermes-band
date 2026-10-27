"""The four sets. Full plates at PW x PH, drawn once, then shot with a virtual
camera. Flat vector shapes plus additive light — the same language as the
character, so nothing looks pasted in.

Each set is built for a low camera and a lot of dark: one warm source, one cool
source, a floor, and something the light can fall off against.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from common import PW, PH, rgba, FONT_BLACK, font, tracked


# ---------------------------------------------------------------- primitives
def vgrad(stops):
    a = np.zeros((PH, PW, 3), np.float32)
    ys = np.linspace(0, 1, PH)
    pos = [s[0] for s in stops]
    cols = np.array([s[1] for s in stops], np.float32)
    for i in range(3):
        a[..., i] = np.interp(ys, pos, cols[:, i])[:, None]
    return Image.fromarray(a.astype(np.uint8)).convert("RGBA")


def veils(im, box, top_a, bot_a, colour=(255, 255, 255)):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return im
    ramp = np.linspace(top_a, bot_a, h)[:, None]
    lay = np.zeros((h, w, 4), np.float32)
    lay[..., 0], lay[..., 1], lay[..., 2] = colour
    lay[..., 3] = np.repeat(ramp, w, axis=1)
    im.alpha_composite(Image.fromarray(lay.astype(np.uint8), "RGBA"), (x0, y0))
    return im


def quad_light(im, pts, colour, a_top, a_bot):
    """A beam: polygon, alpha ramped from the top of its bounding box down."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = int(min(xs)), int(max(xs))
    y0, y1 = int(min(ys)), int(max(ys))
    w, h = x1 - x0 + 1, y1 - y0 + 1
    if w <= 0 or h <= 0:
        return im
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon([(p[0] - x0, p[1] - y0) for p in pts], fill=255)
    ramp = np.linspace(a_top, a_bot, h)[:, None]
    alp = np.array(m, np.float32) / 255.0 * np.repeat(ramp, w, axis=1)
    lay = np.zeros((h, w, 4), np.uint8)
    lay[..., 0], lay[..., 1], lay[..., 2] = colour
    lay[..., 3] = np.clip(alp, 0, 255).astype(np.uint8)
    im.alpha_composite(Image.fromarray(lay, "RGBA"), (x0, y0))
    return im


def glow_blob(im, cx, cy, r, colour, a=140, blur=0.10):
    lay = rgba(int(r * 2.8), int(r * 2.8))
    d = ImageDraw.Draw(lay)
    c = int(r * 1.4)
    for i in range(10, 0, -1):
        rr = r * i / 10
        d.ellipse([c - rr, c - rr, c + rr, c + rr],
                  fill=colour + (int(a * (1 - i / 11) ** 2.0),))
    lay = lay.filter(ImageFilter.GaussianBlur(r * blur))
    im.alpha_composite(lay, (int(cx - c), int(cy - c)))
    return im


def haze(im, n, box, colour, amin, amax, rmin, rmax, seed):
    r = np.random.RandomState(seed)
    lay = rgba(PW, PH)
    d = ImageDraw.Draw(lay)
    for _ in range(n):
        x = r.uniform(box[0], box[2])
        y = r.uniform(box[1], box[3])
        rr = r.uniform(rmin, rmax)
        d.ellipse([x - rr, y - rr, x + rr, y + rr],
                  fill=colour + (r.randint(amin, amax),))
    lay = lay.filter(ImageFilter.GaussianBlur(PW * 0.010))
    im.alpha_composite(lay)
    return im


# ---------------------------------------------------------------- ALLEY
def alley():
    im = vgrad([(0.0, (9, 10, 20)), (0.40, (20, 15, 24)),
                (0.66, (34, 22, 24)), (1.0, (7, 7, 11))])
    r = np.random.RandomState(11)
    VPX, VPY = PW * 0.545, PH * 0.505
    d = ImageDraw.Draw(im)

    # ---- walls
    d.polygon([(0, 0), (VPX - PW * 0.075, VPY), (VPX - PW * 0.075, PH), (0, PH)],
              fill=(27, 20, 21))
    d.polygon([(PW, 0), (VPX + PW * 0.085, VPY), (VPX + PW * 0.085, PH), (PW, PH)],
              fill=(14, 12, 16))
    # a shutter of cold light down the right wall, so it separates from the left
    d.polygon([(PW, 0), (VPX + PW * 0.085, VPY), (VPX + PW * 0.085, PH), (PW, PH)],
              fill=(26, 30, 44))

    # ---- brick, near wall only, in perspective: courses converge on the VP
    for row in range(22):
        f = (row / 21) ** 1.6
        y = PH * 0.03 + PH * 0.94 * f
        x_end = VPX - PW * 0.075 * (1 - 0.0)
        x_end = PW * 0.47 * (1 - f) + (VPX - PW * 0.075) * f
        d.line([(0, y), (x_end, y)], fill=(34, 26, 26), width=max(1, int(1 + 2.5 * f)))
    for col in range(18):
        f = (col / 17) ** 1.35
        x = PW * 0.015 + (VPX - PW * 0.085) * f
        d.line([(x, PH * 0.03), (x, PH * 0.98)], fill=(32, 25, 26),
               width=max(1, int(1 + 3 * f)))
    # dark gaps in the brickwork keep it from reading as corrugation
    for _ in range(260):
        bx = r.uniform(0, PW * 0.44)
        by = r.uniform(PH * 0.05, PH * 0.95)
        bw = r.uniform(PW * 0.004, PW * 0.018)
        bh = r.uniform(PH * 0.004, PH * 0.012)
        d.rectangle([bx, by, bx + bw, by + bh], fill=(22, 17, 18))

    # ---- roller shutter on the near left
    d.rectangle([PW * 0.02, PH * 0.30, PW * 0.125, PH * 0.80], fill=(20, 20, 24))
    for k in range(24):
        y = PH * 0.30 + PH * 0.50 * k / 23
        d.line([(PW * 0.02, y), (PW * 0.125, y)], fill=(26, 26, 31),
               width=max(1, int(PW * 0.0016)))

    # ---- wet asphalt with a vanishing point
    d.polygon([(0, PH), (PW, PH), (VPX + PW * 0.085, VPY + PH * 0.02),
               (VPX - PW * 0.075, VPY + PH * 0.02)], fill=(11, 12, 18))
    for i in range(22):
        f = (i / 21) ** 2.0
        y = VPY + PH * 0.02 + (PH - VPY) * f
        half = PW * (0.10 + 0.52 * f)
        d.line([(VPX - half, y), (VPX + half, y)], fill=(17, 18, 25),
               width=max(1, int(1 + 6 * f)))

    # ---- fire escape on the right wall
    for lvl in range(4):
        f = lvl / 3
        y = PH * (0.10 + lvl * 0.155)
        x0 = PW * (0.60 + 0.035 * f)
        x1 = PW * (0.80 + 0.20 * f)
        hgt = PH * (0.042 + 0.020 * f)
        # landing
        d.rectangle([x0, y, x1, y + PH * 0.011], fill=(13, 13, 17))
        # handrail posts
        n = 5
        for k in range(n):
            xx = x0 + (x1 - x0) * k / (n - 1)
            d.line([(xx, y), (xx, y - hgt)], fill=(13, 13, 17),
                   width=max(2, int(PW * 0.0024)))
        d.line([(x0, y - hgt), (x1, y - hgt)], fill=(18, 18, 23),
               width=max(2, int(PW * 0.0030)))
        d.line([(x0, y - hgt * 0.55), (x1, y - hgt * 0.55)], fill=(16, 16, 21),
               width=max(2, int(PW * 0.0026)))
        # the staircase down to the next landing — this is what makes it read
        d.polygon([(x0, y + PH * 0.011), (x0 + PW * 0.055, y + PH * 0.011),
                   (x0 + PW * 0.020, y + PH * 0.155), (x0 - PW * 0.035, y + PH * 0.155)],
                  fill=(11, 11, 15))
        for k in range(7):
            sy = y + PH * 0.011 + (PH * 0.144) * k / 7
            sx = x0 - PW * 0.035 * k / 7
            d.line([(sx, sy), (sx + PW * 0.052, sy)], fill=(17, 17, 22),
                   width=max(1, int(PW * 0.0016)))

    # ---- dumpster + a crate stack, foreground left, silhouetted
    d.rectangle([PW * 0.055, PH * 0.615, PW * 0.285, PH * 0.885], fill=(18, 24, 22))
    d.rectangle([PW * 0.046, PH * 0.590, PW * 0.294, PH * 0.630], fill=(24, 31, 28))
    d.line([(PW * 0.055, PH * 0.745), (PW * 0.285, PH * 0.745)], fill=(13, 18, 17),
           width=max(3, int(PW * 0.003)))

    # ---- pipes
    for x, w in ((0.318, 0.011), (0.336, 0.006), (0.349, 0.014)):
        d.rectangle([PW * x, PH * 0.02, PW * (x + w), PH * 0.90], fill=(23, 20, 21))

    # ---- graffiti, painted on the wall, not glowing
    tag = rgba(PW, PH)
    td = ImageDraw.Draw(tag)
    fnt = font(FONT_BLACK, int(PH * 0.052))
    from common import text_w
    gw = text_w(td, "HERMES", fnt, spacing=PH * 0.004)
    tracked(td, (PW * 0.055, PH * 0.345), "HERMES", fnt, (128, 58, 36, 185),
            spacing=PH * 0.004)
    tag = tag.rotate(-5, resample=Image.BICUBIC, center=(PW * 0.19, PH * 0.37))
    im = Image.alpha_composite(im, tag)

    # ---- the one warm light: sodium, high left, off frame
    im = glow_blob(im, PW * 0.175, PH * 0.02, PW * 0.048, (255, 178, 84), a=180)
    im = quad_light(im, [(PW * 0.13, 0), (PW * 0.30, 0), (PW * 0.52, PH), (PW * 0.02, PH)],
                    (255, 176, 82), 70, 2)
    # wet road: the lamp smeared straight down the asphalt
    for k, (cx, wd, aa) in enumerate(((0.175, 0.030, 62), (0.175, 0.075, 26),
                                      (0.245, 0.020, 30), (0.120, 0.014, 22))):
        im = veils(im, (PW * (cx - wd), PH * 0.60, PW * (cx + wd), PH * 1.0),
                   0, aa, (255, 168, 92))
    # puddle highlights
    wet = rgba(PW, PH)
    wd = ImageDraw.Draw(wet)
    r2 = np.random.RandomState(19)
    for _ in range(70):
        px = r2.uniform(PW * 0.0, PW * 0.60)
        py = r2.uniform(PH * 0.64, PH * 1.0)
        pw = r2.uniform(PW * 0.008, PW * 0.055)
        ph = pw * r2.uniform(0.05, 0.16)
        wd.ellipse([px, py, px + pw, py + ph], fill=(214, 146, 84, r2.randint(10, 34)))
    wet = wet.filter(ImageFilter.GaussianBlur(PW * 0.004))
    im = Image.alpha_composite(im, wet)

    # ---- the far end of the alley is cold daylight-blue: contrast for the sodium
    im = glow_blob(im, VPX + PW * 0.02, VPY - PH * 0.075, PW * 0.095, (96, 132, 200), a=95)
    im = glow_blob(im, VPX + PW * 0.02, VPY - PH * 0.05, PW * 0.045, (150, 180, 235), a=52)

    im = haze(im, 80, (PW * 0.24, PH * 0.42, PW * 0.60, PH * 0.92),
              (200, 200, 215), 6, 22, PW * 0.010, PW * 0.045, 7)
    return im


# ---------------------------------------------------------------- ROOFTOP
def rooftop():
    im = vgrad([(0.0, (6, 8, 19)), (0.30, (13, 17, 36)), (0.50, (34, 28, 50)),
                (0.575, (92, 54, 48)), (0.60, (44, 28, 30)), (0.62, (16, 15, 22)),
                (1.0, (9, 9, 14))])
    r = np.random.RandomState(21)
    d = ImageDraw.Draw(im)

    # ---- stars, uneven
    for _ in range(320):
        x, y = r.uniform(0, PW), r.uniform(0, PH * 0.46)
        fall = 1.0 - y / (PH * 0.5)
        rr = r.uniform(0.7, 2.6) * (0.6 + fall)
        v = int(r.uniform(70, 210) * (0.4 + 0.6 * fall))
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(v, v, min(255, v + 24)))

    # ---- moon
    im = glow_blob(im, PW * 0.795, PH * 0.135, PW * 0.040, (248, 232, 200), a=115)
    d = ImageDraw.Draw(im)
    mx, my, mr = PW * 0.795, PH * 0.135, PW * 0.0175
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(244, 236, 214))
    for _ in range(14):                        # a few maria, so it isn't a hole
        a2 = r.uniform(0, 6.28)
        rd = r.uniform(0, mr * 0.72)
        rr = r.uniform(mr * 0.08, mr * 0.26)
        d.ellipse([mx + math.cos(a2) * rd - rr, my + math.sin(a2) * rd - rr,
                   mx + math.cos(a2) * rd + rr, my + math.sin(a2) * rd + rr],
                  fill=(228, 219, 198))

    # ---- two skyline layers
    for base, hue, wmin, wmax, hmin, hmax, litp in [
            (0.615, (15, 19, 36), 0.028, 0.075, 0.08, 0.30, 0.22),
            (0.635, (9, 11, 23), 0.018, 0.055, 0.04, 0.17, 0.11)]:
        x = -PW * 0.02
        while x < PW * 1.02:
            w = PW * r.uniform(wmin, wmax)
            h = PH * r.uniform(hmin, hmax)
            top = PH * base - h
            d.rectangle([x, top, x + w, PH * (base + 0.03)], fill=hue)
            cols = max(1, int(w / (PW * 0.010)))
            rows = max(1, int(h / (PH * 0.020)))
            for cc in range(cols):
                for rr2 in range(rows):
                    if r.random() < litp:
                        wx = x + w * (cc + 0.22) / cols
                        wy = top + h * (rr2 + 0.26) / rows
                        warm = r.random() < 0.78
                        d.rectangle([wx, wy, wx + w / cols * 0.40,
                                     wy + h / rows * 0.30],
                                    fill=(214, 158, 84) if warm else (140, 182, 214))
            if r.random() < 0.22:
                ax = x + w * r.uniform(0.2, 0.8)
                d.line([(ax, top), (ax, top - PH * r.uniform(0.015, 0.055))],
                       fill=(24, 26, 40), width=max(2, int(PW * 0.0018)))
            x += w + PW * r.uniform(0.001, 0.010)

    # ---- roof deck: converging seams, so it has depth
    VPY = PH * 0.615
    d.polygon([(0, PH), (PW, PH), (PW * 0.78, VPY), (PW * 0.22, VPY)], fill=(14, 14, 20))
    for i in range(9):
        f = i / 8
        d.line([(PW * (0.22 + 0.56 * f), VPY), (PW * (-0.30 + 1.60 * f), PH)],
               fill=(19, 19, 26), width=max(1, int(PW * 0.002)))
    for i in range(10):
        f = (i / 9) ** 1.9
        y = VPY + (PH - VPY) * f
        d.line([(0, y), (PW, y)], fill=(18, 18, 25), width=max(1, int(1 + 4 * f)))

    # ---- parapet in the foreground, bottom of frame: this is what says "roof"
    d.rectangle([0, PH * 0.905, PW, PH], fill=(11, 11, 17))
    d.rectangle([0, PH * 0.885, PW, PH * 0.912], fill=(21, 21, 29))

    # ---- water tank, back right: cylinder + cone, properly built
    tx, ty, tw2, th2 = PW * 0.745, PH * 0.335, PW * 0.105, PH * 0.245
    d.rectangle([tx, ty, tx + tw2, ty + th2], fill=(20, 19, 24))
    d.ellipse([tx, ty - tw2 * 0.16, tx + tw2, ty + tw2 * 0.16], fill=(24, 23, 28))
    d.polygon([(tx - tw2 * 0.05, ty), (tx + tw2 * 1.05, ty),
               (tx + tw2 * 0.5, ty - th2 * 0.30)], fill=(17, 16, 21))
    for lx in (0.06, 0.5, 0.94):
        d.line([(tx + tw2 * lx, ty + th2), (tx + tw2 * lx, VPY + PH * 0.06)],
               fill=(15, 14, 19), width=max(3, int(PW * 0.004)))

    # ---- city bounce: cool from the sky, warm from the street
    im = veils(im, (0, PH * 0.62, PW, PH * 0.93), 26, 0, (140, 165, 215))
    im = glow_blob(im, PW * 0.42, PH * 0.70, PW * 0.30, (255, 150, 90), a=42)
    return im


# ---------------------------------------------------------------- LAB
def lab():
    im = vgrad([(0.0, (8, 9, 13)), (0.55, (13, 14, 19)), (1.0, (6, 6, 9))])
    r = np.random.RandomState(31)
    d = ImageDraw.Draw(im)

    # ---- pegboard of tools: fifty tools on the wall, because of course
    px0, py0, px1, py1 = PW * 0.055, PH * 0.10, PW * 0.40, PH * 0.56
    d.rectangle([px0, py0, px1, py1], fill=(19, 19, 25))
    for gy in np.arange(py0 + PH * 0.012, py1, PH * 0.026):
        for gx in np.arange(px0 + PW * 0.010, px1, PW * 0.020):
            d.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=(11, 11, 15))
    # hung tools: hammers, spanners, screwdrivers — silhouettes
    for k in range(16):
        tx = px0 + PW * 0.028 + (k % 4) * PW * 0.078
        ty = py0 + PH * 0.045 + (k // 4) * PH * 0.115
        kind = k % 3
        if kind == 0:                      # spanner
            d.line([(tx, ty), (tx, ty + PH * 0.070)], fill=(58, 62, 74),
                   width=max(3, int(PW * 0.0035)))
            d.ellipse([tx - PW * 0.008, ty - PW * 0.008, tx + PW * 0.008,
                       ty + PW * 0.008], outline=(58, 62, 74),
                      width=max(3, int(PW * 0.003)))
        elif kind == 1:                    # hammer
            d.line([(tx, ty + PH * 0.006), (tx, ty + PH * 0.062)], fill=(74, 56, 40),
                   width=max(4, int(PW * 0.004)))
            d.rectangle([tx - PW * 0.016, ty, tx + PW * 0.016, ty + PH * 0.014],
                        fill=(70, 74, 88))
        else:                              # screwdriver
            d.line([(tx, ty), (tx, ty + PH * 0.052)], fill=(200, 120, 40),
                   width=max(4, int(PW * 0.004)))
            d.line([(tx, ty + PH * 0.052), (tx, ty + PH * 0.070)], fill=(150, 156, 170),
                   width=max(2, int(PW * 0.0022)))

    # ---- server racks
    for bx, bw in ((0.44, 0.135), (0.60, 0.115)):
        x0, x1 = PW * bx, PW * (bx + bw)
        d.rectangle([x0, PH * 0.16, x1, PH * 0.80], fill=(13, 15, 21))
        d.rectangle([x0, PH * 0.16, x1, PH * 0.185], fill=(22, 25, 34))
        for u in range(14):
            uy = PH * 0.20 + u * PH * 0.042
            d.rectangle([x0 + PW * 0.008, uy, x1 - PW * 0.008, uy + PH * 0.030],
                        fill=(18, 21, 28))
            for lx in range(4):
                d.rectangle([x0 + PW * 0.014 + lx * PW * 0.010, uy + PH * 0.010,
                             x0 + PW * 0.019 + lx * PW * 0.010, uy + PH * 0.018],
                            fill=(40, 44, 56))

    # ---- bench
    d.rectangle([0, PH * 0.80, PW, PH * 0.84], fill=(28, 23, 20))
    d.rectangle([0, PH * 0.84, PW, PH], fill=(15, 13, 13))

    # ---- monitor with a terminal on it
    mx0, my0 = PW * 0.68, PH * 0.52
    d.rectangle([mx0, my0, mx0 + PW * 0.26, my0 + PH * 0.20], fill=(10, 12, 16))
    d.rectangle([mx0 + PW * 0.006, my0 + PH * 0.008, mx0 + PW * 0.254,
                 my0 + PH * 0.192], fill=(12, 22, 18))
    fnt = font("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
               int(PH * 0.018))
    lines = ["$ hermes run --site", "ok  boot            0.4s",
             "ok  tools   51 loaded", "ok  cron    02:00", "> shipping"]
    for i, s in enumerate(lines):
        d.text((mx0 + PW * 0.012, my0 + PH * 0.018 + i * PH * 0.030), s,
               font=fnt, fill=(96, 226, 140) if i else (170, 230, 180))
    # stand + bezel shadow: without them the terminal reads as a UI overlay
    d.rectangle([mx0 + PW * 0.115, my0 + PH * 0.200, mx0 + PW * 0.145,
                 my0 + PH * 0.245], fill=(24, 24, 30))
    d.rectangle([mx0 + PW * 0.075, my0 + PH * 0.243, mx0 + PW * 0.185,
                 my0 + PH * 0.258], fill=(26, 26, 33))
    d.rectangle([mx0, my0, mx0 + PW * 0.26, my0 + PH * 0.20],
                outline=(44, 46, 58), width=max(2, int(PW * 0.003)))

    # ---- hanging lamp
    d.line([(PW * 0.235, 0), (PW * 0.235, PH * 0.19)], fill=(30, 30, 34),
           width=max(3, int(PW * 0.003)))
    d.polygon([(PW * 0.205, PH * 0.19), (PW * 0.265, PH * 0.19),
               (PW * 0.252, PH * 0.245), (PW * 0.218, PH * 0.245)], fill=(38, 38, 44))
    im = glow_blob(im, PW * 0.235, PH * 0.245, PW * 0.030, (255, 206, 150), a=170)
    im = quad_light(im, [(PW * 0.205, PH * 0.245), (PW * 0.265, PH * 0.245),
                         (PW * 0.46, PH * 0.86), (PW * 0.01, PH * 0.86)],
                    (255, 200, 140), 54, 3)
    # cool rack spill
    im = glow_blob(im, PW * 0.575, PH * 0.42, PW * 0.16, (70, 150, 200), a=54)
    im = veils(im, (0, PH * 0.80, PW, PH * 0.99), 16, 0, (255, 190, 130))
    im = haze(im, 40, (PW * 0.10, PH * 0.15, PW * 0.80, PH * 0.75),
              (210, 210, 220), 4, 14, PW * 0.012, PW * 0.040, 3)
    return im


# ---------------------------------------------------------------- STAGE
def stage():
    im = vgrad([(0.0, (7, 7, 12)), (0.45, (12, 11, 18)), (0.66, (20, 15, 20)),
                (1.0, (6, 5, 9))])
    r = np.random.RandomState(41)
    d = ImageDraw.Draw(im)

    # ---- back wall wordmark, huge and dim
    tag = rgba(PW, PH)
    td = ImageDraw.Draw(tag)
    fnt = font(FONT_BLACK, int(PH * 0.26))
    from common import text_w
    wtxt = text_w(td, "HERMES", fnt, spacing=PH * 0.010)
    tracked(td, ((PW - wtxt) / 2, PH * 0.31), "HERMES", fnt,
            (58, 30, 22, 225), spacing=PH * 0.010)
    im = Image.alpha_composite(im, tag.filter(ImageFilter.GaussianBlur(PW * 0.0016)))

    # ---- floor
    d = ImageDraw.Draw(im)
    d.polygon([(0, PH), (PW, PH), (PW * 0.74, PH * 0.60), (PW * 0.26, PH * 0.60)],
              fill=(13, 12, 18))

    # ---- four beams from the rig
    for i, (bx, col) in enumerate([(0.20, (255, 150, 70)), (0.42, (255, 190, 120)),
                                   (0.60, (255, 150, 70)), (0.82, (150, 190, 255))]):
        top_x = PW * bx
        spread = PW * (0.16 if i % 2 else 0.11)
        im = quad_light(im, [(top_x - PW * 0.012, 0), (top_x + PW * 0.012, 0),
                             (top_x + spread, PH * 0.78), (top_x - spread, PH * 0.78)],
                        col, 54, 6)
        im = glow_blob(im, top_x, PH * 0.02, PW * 0.026, col, a=120)
        im = glow_blob(im, top_x, PH * 0.78, PW * 0.09, col, a=34)

    # ---- light pool on the floor
    im = glow_blob(im, PW * 0.5, PH * 0.80, PW * 0.26, (255, 180, 110), a=58)

    # ---- crowd silhouettes along the bottom, some hands up
    d = ImageDraw.Draw(im)
    for row, (yb, sc, alpha) in enumerate([(0.985, 1.0, 255), (0.95, 0.94, 205)]):
        x = -PW * 0.03
        while x < PW * 1.05:
            hw2 = PW * r.uniform(0.028, 0.046) * sc
            hy = PH * yb - hw2 * 1.5
            col = (5, 5, 8) if row == 0 else (8, 8, 12)
            d.ellipse([x - hw2 * 0.55, hy - hw2 * 0.75, x + hw2 * 0.55, hy + hw2 * 0.75],
                      fill=col)
            d.rounded_rectangle([x - hw2, hy + hw2 * 0.55, x + hw2, PH * yb + PH * 0.10],
                                radius=hw2 * 0.55, fill=col)
            if r.random() < 0.30:
                ax = x + r.uniform(-hw2 * 0.9, hw2 * 0.9)
                ay = hy - hw2 * r.uniform(1.2, 2.6)
                d.line([(x, hy + hw2 * 0.6), (ax, ay)], fill=col,
                       width=max(4, int(hw2 * 0.30)))
                d.ellipse([ax - hw2 * 0.22, ay - hw2 * 0.30, ax + hw2 * 0.22,
                           ay + hw2 * 0.14], fill=col)
            x += hw2 * r.uniform(1.7, 2.5)

    im = haze(im, 90, (0, PH * 0.25, PW, PH * 0.85), (255, 210, 170), 4, 16,
              PW * 0.014, PW * 0.060, 5)
    return im


SETS = {"alley": alley, "rooftop": rooftop, "lab": lab, "stage": stage}
