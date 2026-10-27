"""Film kit: canvas maths, camera, grading, type.

Everything is flat vector shapes and additive light, then one grade on top. No
3D, no textures, no assets — the whole film is drawn.
"""
from __future__ import annotations

import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FPS = 24
PW, PH = 2688, 1512          # plate resolution: always >= output, so we only ever
                             # down-sample when the camera pushes in

FONT_BLACK = "/usr/share/fonts/truetype/lato/Lato-Black.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"
FONT_NARROW = "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf"


# ------------------------------------------------------------------ timing
def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def smooth(t, a, b):
    if b <= a:
        return 1.0
    return ease((t - a) / (b - a))


def lerp(a, b, f):
    return a + (b - a) * f


# ------------------------------------------------------------------ drawing
def rgba(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def font(path, size):
    return ImageFont.truetype(path, size)


def tracked(draw, xy, text, fnt, fill, spacing=0.0, anchor_right=False,
            stroke=0, stroke_fill=None):
    """Draw text with letter spacing. Returns the width used."""
    widths = [draw.textlength(c, font=fnt) for c in text]
    total = sum(widths) + spacing * max(0, len(text) - 1)
    x = xy[0] - total if anchor_right else xy[0]
    y = xy[1]
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=fnt, fill=fill,
                  stroke_width=stroke, stroke_fill=stroke_fill)
        x += w + spacing
    return total


def text_w(draw, text, fnt, spacing=0.0):
    return sum(draw.textlength(c, font=fnt) for c in text) + spacing * max(0, len(text) - 1)


# ------------------------------------------------------------------ camera
def warp(plate, s, cx, cy, w=W, h=H):
    """Sample a window of `plate` into a w*h frame. s>=1 = push in."""
    ph, pw = plate.shape[:2]
    ys = (cy - (h / 2) / s + np.arange(h) / s).astype(np.int32)
    xs = (cx - (w / 2) / s + np.arange(w) / s).astype(np.int32)
    np.clip(ys, 0, ph - 1, out=ys)
    np.clip(xs, 0, pw - 1, out=xs)
    return plate[ys][:, xs]


def handheld(t, seed=0, amp=2.2):
    """Slow gate drift, so nothing sits perfectly still."""
    r = np.random.RandomState(seed)
    a = r.uniform(0, 6.28, 4)
    return (amp * math.sin(t * 0.83 + a[0]) + amp * 0.5 * math.sin(t * 2.1 + a[1]),
            amp * math.sin(t * 0.71 + a[2]) + amp * 0.5 * math.sin(t * 1.9 + a[3]))


# ------------------------------------------------------------------ grade
def _lut():
    x = np.arange(256, dtype=np.float32) / 255.0
    return x


def grade(arr, teal=0.055, warm=0.045, contrast=1.10, sat=1.06, lift=0.012):
    """Cinema grade: cool shadows, warm highlights, slight crush."""
    a = arr.astype(np.float32) / 255.0
    lum = a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
    # contrast around 0.42
    a = (a - 0.42) * contrast + 0.42 + lift
    # split tone: add cool in the darks, warm in the brights
    shadow = np.clip(1.0 - lum * 2.2, 0, 1)[..., None]
    high = np.clip(lum * 1.9 - 0.35, 0, 1)[..., None]
    a = a + shadow * np.array([-teal * 0.35, teal * 0.35, teal], np.float32) * 0.9
    a = a + high * np.array([warm, warm * 0.45, -warm * 0.55], np.float32) * 0.9
    # saturation
    l2 = a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722
    a = l2[..., None] + (a - l2[..., None]) * sat
    return np.clip(a, 0, 1) * 255.0


_VIG = None


def vignette(w=W, h=H, strength=0.42):
    global _VIG
    if _VIG is None or _VIG.shape[:2] != (h, w):
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        nx = (xx - w / 2) / (w / 2)
        ny = (yy - h / 2) / (h / 2)
        r = np.sqrt(nx ** 2 * 0.85 + ny ** 2)
        v = 1.0 - strength * np.clip(r - 0.35, 0, 1.6) ** 1.7
        _VIG = np.clip(v, 0, 1)[..., None].astype(np.float32)
    return _VIG


def bloom(im, amount=0.55, radius=18, threshold=0.62):
    """Halation: bright pass, blurred, added back warm."""
    small = im.resize((W // 4, H // 4), Image.BILINEAR)
    a = np.asarray(small, np.float32) / 255.0
    lum = a[..., :3].max(axis=2)
    mask = np.clip((lum - threshold) / (1 - threshold), 0, 1)[..., None] ** 1.5
    bright = a[..., :3] * mask
    bi = Image.fromarray((np.clip(bright, 0, 1) * 255).astype(np.uint8))
    bi = bi.filter(ImageFilter.GaussianBlur(radius / 4))
    bi = bi.resize((W, H), Image.BILINEAR)
    out = np.asarray(im, np.float32) / 255.0
    add = np.asarray(bi, np.float32) / 255.0
    add = add * np.array([1.0, 0.82, 0.66], np.float32)   # warm halation
    return np.clip(out + add * amount, 0, 1)


_GRAIN = {}


def grain_arr(seed, amount=0.030):
    key = seed % 8
    if key not in _GRAIN:
        r = np.random.RandomState(9001 + key)
        g = r.normal(0, 1, (H, W)).astype(np.float32)
        g = g + r.normal(0, 1, (H, W)).astype(np.float32) * 0.5
        _GRAIN[key] = g
    return _GRAIN[key] * amount


def ca_shift(arr, px=1.6):
    """Chromatic aberration: pull R in, push B out, very slightly."""
    if px <= 0:
        return arr
    out = arr.copy()
    p = int(round(px))
    if p < 1:
        return arr
    out[:, p:, 0] = arr[:, :-p, 0]
    out[:, :-p, 2] = arr[:, p:, 2]
    return out


def letterbox(arr, h=H, w=W, bar=0.0):
    if bar <= 0:
        return arr
    n = int(h * bar)
    arr[:n] = 0
    arr[h - n:] = 0
    return arr


def finish(im, seed=0, vig=0.42, grain=0.030, ca=1.4, bars=0.0, bloom_amt=0.5):
    """Grade -> halation -> vignette -> aberration -> grain -> letterbox."""
    a = grade(np.asarray(im.convert("RGB"), np.float32))
    bi = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    a = bloom(bi, amount=bloom_amt) * 255.0
    a = a * vignette(strength=vig)
    a = ca_shift(a, ca)
    a = a + grain_arr(seed, grain)[..., None] * 255.0
    return Image.fromarray(letterbox(np.clip(a, 0, 255).astype(np.uint8), bar=bars))
