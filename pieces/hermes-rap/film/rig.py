"""The Hermes bot — the rapper.

Flat vector, matching the band's avatar language (solid fills, no outlines), but
articulated: the head nods on the beat, the jaw is driven by the actual vocal
envelope, the eyes squint on the burns, and the arms run through a small library of
poses.

Draw order matters: legs, torso, arms ON TOP of the jacket, head, chain, mic.
Everything is a fraction of the figure's height, so the same rig works from a 200 px
insert to a 1000 px close-up.

Three things make it read at small sizes, learned the hard way: the jacket has to be
lighter than the night it stands in, every sleeve carries an orange stripe so the arm
is a shape and not a hole, and the jaw is a dark recessed cavity with lit bars in it —
bars on their own look like a speaker grille, a cavity reads as a mouth.
"""
from __future__ import annotations

import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from common import rgba

SHELL = (237, 231, 219)
SHELL_D = (194, 187, 172)
JACKET = (42, 45, 56)
JACKET_D = (24, 26, 34)
TRIM = (255, 107, 26)
TRIM_D = (186, 70, 12)
GOLD = (242, 193, 78)
GOLD_D = (150, 111, 30)
DENIM = (48, 51, 64)
DENIM_D = (31, 33, 43)
GLASS = (8, 10, 15)
EYE = (255, 140, 46)
MIC = (46, 48, 58)
STEEL = (196, 202, 214)

ASPECT = 0.60


def _capsule(d, p0, p1, w, fill):
    d.line([p0, p1], fill=fill, width=max(1, int(w)))
    r = w / 2
    for p in (p0, p1):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=fill)


def _perp(p0, p1, side):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1.0
    return -dy / L * side, dx / L * side


def _arm(d, sx, sy, l1, l2, a1, a2, w, outward):
    ex = sx + math.sin(a1) * l1
    ey = sy + math.cos(a1) * l1
    a2t = a1 + a2
    hx = ex + math.sin(a2t) * l2
    hy = ey + math.cos(a2t) * l2
    _capsule(d, (sx, sy), (ex, ey), w, JACKET)
    _capsule(d, (ex, ey), (hx, hy), w * 0.88, JACKET)
    # the stripe is what makes the arm a shape instead of a hole in the night
    # stripe each segment on its own normal, or a bent elbow slices the stripe
    # across the joint and the arm reads as a cardboard cut-out
    o1x, o1y = _perp((sx, sy), (ex, ey), outward * w * 0.34)
    o2x, o2y = _perp((ex, ey), (hx, hy), outward * w * 0.32)
    _capsule(d, (sx + o1x, sy + o1y), (ex + o1x, ey + o1y), w * 0.26, TRIM)
    _capsule(d, (ex + o2x, ey + o2y), (hx + o2x, hy + o2y), w * 0.24, TRIM)
    # shoulder and elbow caps: the joints are discs, so a bend reads as a bend
    d.ellipse([sx - w * 0.60, sy - w * 0.60, sx + w * 0.60, sy + w * 0.60], fill=JACKET)
    d.ellipse([ex - w * 0.46, ey - w * 0.46, ex + w * 0.46, ey + w * 0.46], fill=JACKET)
    # cuff
    cx = ex + (hx - ex) * 0.78
    cy = ey + (hy - ey) * 0.78
    _capsule(d, (cx, cy), (hx, hy), w * 0.92, TRIM_D)
    r = w * 0.86
    d.rounded_rectangle([hx - r, hy - r, hx + r, hy + r], radius=r * 0.38, fill=SHELL)
    return hx, hy, a2t


def draw_bot(height=900, pose="idle", mouth=0.0, blink=0.0, squint=0.0,
             glow=1.0, look=0.0, tilt=0.0, mic=False, walking=0.0):
    ss = 2
    hh = int(height * ss)
    ww = int(hh * ASPECT)
    im = rgba(ww, hh)
    d = ImageDraw.Draw(im)

    def Y(f):
        return f * hh

    def X(f):
        return f * ww

    head_top = 0.050
    head_h = 0.250
    head_w = 0.390
    hcx = X(0.5 + look * 0.010)
    neck_y = head_top + head_h + 0.008
    sh_y = neck_y + 0.030
    torso_top = sh_y - 0.006
    torso_bot = 0.720
    half_t = 0.176
    cx = X(0.5)

    # ---- legs
    lw = X(0.076)
    for sgn, col in ((-1, DENIM), (1, DENIM_D)):
        hx = cx + sgn * X(0.060)
        fx = hx + sgn * X(0.012 if not walking else 0.034)
        _capsule(d, (hx, Y(torso_bot - 0.02)), (fx, Y(0.970)), lw, col)
        d.rounded_rectangle([fx - X(0.050), Y(0.955), fx + X(0.058), Y(0.998)],
                            radius=Y(0.012), fill=(16, 16, 20))
        d.rounded_rectangle([fx - X(0.050), Y(0.984), fx + X(0.058), Y(0.998)],
                            radius=Y(0.007), fill=(58, 58, 66))

    # ---- torso
    d.polygon([(cx - X(half_t), Y(torso_top)), (cx + X(half_t), Y(torso_top)),
               (cx + X(half_t * 0.88), Y(torso_bot)),
               (cx - X(half_t * 0.88), Y(torso_bot))], fill=JACKET)
    d.rounded_rectangle([cx - X(half_t), Y(torso_top) - Y(0.008),
                         cx + X(half_t), Y(torso_top) + Y(0.028)],
                        radius=Y(0.020), fill=JACKET_D)
    d.line([(cx, Y(torso_top + 0.026)), (cx, Y(torso_bot - 0.046))],
           fill=(96, 100, 116), width=max(2, int(X(0.006))))
    d.rectangle([cx - X(half_t * 0.88), Y(torso_bot) - Y(0.030),
                 cx + X(half_t * 0.88), Y(torso_bot)], fill=TRIM_D)
    # lapels — the single strongest jacket signifier
    for sgn in (-1, 1):
        d.polygon([(cx + sgn * X(0.030), Y(torso_top + 0.024)),
                   (cx + sgn * X(0.104), Y(torso_top + 0.020)),
                   (cx + sgn * X(0.062), Y(torso_top + 0.105)),
                   (cx + sgn * X(0.030), Y(torso_top + 0.150))],
                  fill=JACKET_D)
    # pockets
    for sgn in (-1, 1):
        d.line([(cx + sgn * X(0.055), Y(torso_bot - 0.115)),
                (cx + sgn * X(0.135), Y(torso_bot - 0.115))],
               fill=(30, 32, 42), width=max(2, int(X(0.008))))
    # the lit chest panel, so the torso separates from the visor black
    d.polygon([(cx - X(half_t * 0.60), Y(torso_top + 0.030)),
               (cx - X(0.010), Y(torso_top + 0.030)),
               (cx - X(0.014), Y(torso_bot - 0.040)),
               (cx - X(half_t * 0.56), Y(torso_bot - 0.040))],
              fill=(54, 58, 72))

    # ---- arms
    aw = X(0.098)
    POSE = {
        "idle":  (-0.14, 0.26, 0.14, -0.18),
        "point": (-0.10, 0.38, 1.20, 0.02),
        "palm":  (1.05, 0.50, 0.10, -0.26),
        "fist":  (-0.08, 0.30, 0.86, -1.50),
        "mic":   (-0.14, 0.32, 0.66, -1.66),
        "cross": (0.42, -1.85, -0.42, 1.70),
        "wide":  (0.92, -0.26, -0.92, 0.26),
        "low":   (-0.28, 0.08, 0.28, -0.08),
        "reach": (1.28, 0.10, -0.10, 0.30),
    }
    aL1, aL2, aR1, aR2 = POSE.get(pose, POSE["idle"])
    aL1 -= walking * 0.28
    aR1 += walking * 0.28
    l1, l2 = Y(0.150), Y(0.142)
    _arm(d, cx - X(half_t * 0.92), Y(sh_y + 0.018), l1, l2, aL1, aL2, aw, -1)
    hand_r = _arm(d, cx + X(half_t * 0.92), Y(sh_y + 0.018), l1, l2, aR1, aR2, aw, 1)

    # ---- neck
    d.rectangle([cx - X(0.040), Y(neck_y - 0.022), cx + X(0.040), Y(neck_y + 0.026)],
                fill=JACKET_D)

    # ---- head
    hw = X(head_w)
    ht = Y(head_top + tilt * 0.0016)
    hb = ht + Y(head_h)
    d.rounded_rectangle([hcx - hw, ht, hcx + hw, hb], radius=Y(0.058), fill=SHELL)
    for sgn in (-1, 1):
        d.rounded_rectangle([hcx + sgn * hw - X(0.016), ht + Y(0.066),
                             hcx + sgn * hw + X(0.016), ht + Y(0.122)],
                            radius=Y(0.011), fill=SHELL_D)
    vy0 = ht + Y(0.062)
    vy1 = ht + Y(0.140)
    d.rounded_rectangle([hcx - hw * 0.93, vy0, hcx + hw * 0.93, vy1],
                        radius=Y(0.026), fill=GLASS)
    ey = (vy0 + vy1) / 2
    ew = hw * 0.20
    eh = (vy1 - vy0) * (0.40 - 0.16 * min(1.0, squint))
    ew = ew * (1.0 - 0.18 * min(1.0, squint))
    for sgn in (-1, 1):
        ex = hcx + sgn * hw * 0.41 + look * hw * 0.12
        if blink > 0.55:
            d.rounded_rectangle([ex - ew, ey - eh * 0.13, ex + ew, ey + eh * 0.13],
                                radius=eh * 0.12, fill=EYE)
        else:
            d.rounded_rectangle([ex - ew, ey - eh, ex + ew, ey + eh],
                                radius=eh * 0.40, fill=EYE)

    # ---- jaw: a recessed cavity with lit bars in it
    gy0 = vy1 + Y(0.008)
    gy1 = ht + Y(head_h - 0.012)
    cav = [hcx - hw * 0.56, gy0, hcx + hw * 0.56, gy1]
    d.rounded_rectangle(cav, radius=Y(0.016), fill=(18, 18, 24))
    gh = gy1 - gy0
    open_h = gh * (0.26 + 0.74 * min(1.0, mouth))
    bars = 5
    bx0 = cav[0] + X(0.008)
    bw = (cav[2] - cav[0] - X(0.016)) / bars
    lit = (255, 150, 60) if mouth > 0.05 else (122, 124, 138)
    for i in range(bars):
        x0 = bx0 + i * bw + bw * 0.16
        x1 = x0 + bw * 0.68
        inset = abs(i - (bars - 1) / 2) / ((bars - 1) / 2) * 0.26
        top = gy1 - open_h * (1.0 - inset)
        d.rounded_rectangle([x0, top, x1, gy1 - Y(0.004)], radius=bw * 0.26, fill=lit)

    # ---- antenna
    ax = hcx
    d.line([(ax, ht + Y(0.004)), (ax, ht - Y(0.048))], fill=SHELL_D,
           width=max(2, int(X(0.009))))
    d.ellipse([ax - X(0.017), ht - Y(0.074), ax + X(0.017), ht - Y(0.040)], fill=TRIM)

    # ---- chain
    cy0 = Y(torso_top + 0.012)
    pts = []
    for i in range(17):
        f = i / 16
        pts.append((cx - X(0.110) + f * X(0.220),
                    cy0 + math.sin(f * math.pi) * Y(0.056)))
    for i, p in enumerate(pts):
        r = X(0.0078) if i % 2 else X(0.0098)
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=GOLD)
    mx, my = pts[8]
    my += Y(0.016)
    mr = X(0.037)
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=GOLD_D)
    d.ellipse([mx - mr * 0.80, my - mr * 0.80, mx + mr * 0.80, my + mr * 0.80], fill=GOLD)
    blk = max(2, int(X(0.007)))
    for dxs in (-0.30, 0.30):
        d.line([(mx + mr * dxs, my + mr * 0.34), (mx + mr * dxs, my - mr * 0.36)],
               fill=GOLD_D, width=blk)
    d.line([(mx - mr * 0.30, my + mr * 0.02), (mx + mr * 0.30, my + mr * 0.02)],
           fill=GOLD_D, width=blk)

    # ---- mic
    if mic:
        hx, hy, ang = hand_r
        mx2 = hx + math.sin(ang) * Y(0.070)
        my2 = hy + math.cos(ang) * Y(0.070)
        d.line([(hx, hy), (mx2, my2)], fill=MIC, width=max(6, int(X(0.020))))
        r = X(0.040)
        d.ellipse([mx2 - r, my2 - r, mx2 + r, my2 + r], fill=STEEL)
        d.ellipse([mx2 - r * 0.66, my2 - r * 0.66, mx2 + r * 0.66, my2 + r * 0.66],
                  fill=(112, 118, 132))
        d.line([(mx2 - r * 0.5, my2 - r * 0.2), (mx2 + r * 0.5, my2 - r * 0.2)],
               fill=(78, 82, 94), width=max(2, int(X(0.006))))
        d.line([(mx2 - r * 0.5, my2 + r * 0.2), (mx2 + r * 0.5, my2 + r * 0.2)],
               fill=(78, 82, 94), width=max(2, int(X(0.006))))

    # ---- cel shadow: a hard edge on the key-light side, added as its own layer so
    #      it cannot punch a hole in the silhouette's alpha
    alpha = im.split()[3]
    side = Image.new("L", im.size, 0)
    sd0 = ImageDraw.Draw(side)
    sd0.polygon([(ww * 0.615, hh * 0.285), (ww, hh * 0.285), (ww, hh),
                 (ww * 0.520, hh)], fill=255)
    sd0.polygon([(ww * 0.815, 0), (ww, 0), (ww, hh * 0.30), (ww * 0.795, hh * 0.30)],
                fill=255)
    mask = ImageChops.multiply(alpha, side)
    shade = rgba(ww, hh)
    ImageDraw.Draw(shade).rectangle([0, 0, ww, hh], fill=(8, 10, 20))
    shade.putalpha(ImageChops.multiply(Image.new("L", im.size, 104), mask))
    im = Image.alpha_composite(im, shade)

    # ---- rim light: the silhouette's own right edge, found by shifting its alpha
    edge = ImageChops.subtract(alpha, ImageChops.offset(alpha, -max(2, int(ww * 0.006)), 0))
    rim = rgba(ww, hh)
    ImageDraw.Draw(rim).rectangle([0, 0, ww, hh], fill=(255, 156, 96))
    rim.putalpha(ImageChops.multiply(Image.new("L", im.size, 150), edge))
    rim = rim.filter(ImageFilter.GaussianBlur(ww * 0.0018))
    im = Image.alpha_composite(im, rim)

    # ---- eye + antenna glow
    glowl = rgba(ww, hh)
    gd = ImageDraw.Draw(glowl)
    for sgn in (-1, 1):
        ex = hcx + sgn * hw * 0.41 + look * hw * 0.12
        gd.ellipse([ex - ew * 2.8, ey - eh * 2.8, ex + ew * 2.8, ey + eh * 2.8],
                   fill=(255, 138, 43, int(62 * glow)))
    gd.ellipse([ax - X(0.044), ht - Y(0.104), ax + X(0.044), ht - Y(0.012)],
               fill=(255, 107, 26, int(80 * glow)))
    glowl = glowl.filter(ImageFilter.GaussianBlur(hh * 0.009))
    im = Image.alpha_composite(im, glowl)

    return im.resize((ww // ss, hh // ss), Image.LANCZOS)
