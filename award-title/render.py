"""Award-ceremony title animation: 3840x2160, 30 fps, 10 s, with synthesized audio.

Usage:  python3 render.py [--preview] [--frames a:b] [--still t]
Needs:  numpy, Pillow (with raqm), ffmpeg on PATH, Montserrat TTFs in ./fonts
"""
import argparse
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")

W, H = 3840, 2160
FPS = 30
DUR = 10.0
NFRAMES = int(FPS * DUR)
SMAX = 1.04            # text is pre-rendered at this scale so camera push-in only ever downsamples
CAM_PUSH = 0.035       # total push-in over 10 s

ROYAL = np.array([0x1F, 0x33, 0x75], np.float32) / 255.0
NAVY = np.array([0x0E, 0x17, 0x40], np.float32) / 255.0
DARK_START = np.array([0x07, 0x0C, 0x24], np.float32) / 255.0

# Metallic gold ramp, sampled over each line's cap height (0 = cap top, 1 = baseline).
GOLD_STOPS = [
    (0.00, (255, 246, 214)),
    (0.22, (246, 214, 128)),
    (0.46, (205, 158, 62)),
    (0.54, (168, 120, 40)),
    (0.72, (232, 194, 102)),
    (0.88, (252, 232, 168)),
    (1.00, (190, 140, 50)),
]

# ---------------------------------------------------------------- helpers

def clamp01(x):
    return min(1.0, max(0.0, x))


def prog(t, a, b):
    return clamp01((t - a) / (b - a))


def ease_out(x):
    return 1.0 - (1.0 - x) ** 3


def smooth(x):
    return x * x * (3.0 - 2.0 * x)


def font(weight, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"Montserrat-{weight}.ttf"), int(round(size)))


def _box(a, r, axis):
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad), axis=axis, dtype=np.float64)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(np.float32)


def gblur(a, sigma):
    """Gaussian approximation: three box passes per axis."""
    if sigma <= 0.3:
        return a
    r = max(1, int(round((math.sqrt(4 * sigma * sigma / 3 + 1) - 1) / 2)))
    for _ in range(3):
        a = _box(a, r, 0)
        a = _box(a, r, 1)
    return a


def resize_f(a, size, box=None, resample=Image.BICUBIC):
    """Resize a float32 HxW or HxWxC array with PIL (mode F, per channel)."""
    if a.ndim == 2:
        return np.asarray(Image.fromarray(a, "F").resize(size, resample, box=box), np.float32)
    return np.stack([resize_f(a[..., c], size, box, resample) for c in range(a.shape[2])], -1)


def over(dst, src, x, y):
    """Premultiplied 'over' of RGBA src onto dst at integer (x, y), clipped."""
    h, w = src.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    d = dst[y0:y1, x0:x1]
    d *= (1.0 - s[..., 3:4])
    d += s

# ---------------------------------------------------------------- text assets

def text_mask(text, fnt, tracking, pad):
    """Antialiased mask with the cap top at y=pad and left edge at x=pad."""
    size = fnt.size
    cap = fnt.getbbox("H", anchor="ls")
    cap_h = -cap[1]
    adv = [fnt.getlength(text[:i]) + i * tracking for i in range(len(text) + 1)]
    width = int(math.ceil(adv[-1] - tracking)) + 2 * pad
    height = int(math.ceil(cap_h)) + 2 * pad + int(size * 0.05)
    img = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(img)
    base_y = pad + cap_h
    if tracking == 0:
        d.text((pad, base_y), text, font=fnt, fill=255, anchor="ls")
    else:
        for i, ch in enumerate(text):
            d.text((pad + adv[i], base_y), ch, font=fnt, fill=255, anchor="ls")
    return np.asarray(img, np.float32) / 255.0, cap_h


def gold_fill(mask, pad, cap_h):
    h, w = mask.shape
    u = (np.arange(h, dtype=np.float32) - pad) / cap_h
    xs = [s[0] for s in GOLD_STOPS]
    rows = np.stack([np.interp(u, xs, [s[1][c] / 255.0 for s in GOLD_STOPS]) for c in range(3)], -1)
    fill = np.broadcast_to(rows[:, None, :], (h, w, 3)).astype(np.float32).copy()
    # faint diagonal sheen so the metal is not a flat stripe pattern
    xx = np.arange(w, dtype=np.float32)[None, :] / max(w, 1)
    yy = u[:, None]
    sheen = np.exp(-((xx * 2.2 - yy * 0.6 - 0.55) ** 2) / 0.02) * 0.10
    fill += sheen[..., None]
    # bevel: light from upper left
    b = gblur(mask, max(1.0, cap_h * 0.035))
    gy = np.gradient(b, axis=0)
    gx = np.gradient(b, axis=1)
    lit = -(gy * 0.85 + gx * 0.35)
    m = np.abs(lit).max() + 1e-6
    lit /= m
    hi = np.clip(lit, 0, 1)[..., None]
    sh = np.clip(-lit, 0, 1)[..., None]
    fill = fill * (1.0 - 0.38 * sh) + hi * 0.45 * np.array([1.0, 0.97, 0.86], np.float32)
    return np.clip(fill, 0, 1)


def make_text_asset(text, weight, size, tracking_em, glow_gain=0.22, shadow_a=0.55):
    """Returns dict with premultiplied 'base' (shadow + gold) and 'glow' (additive, A=0)."""
    fnt = font(weight, size)
    cap_h_est = size * 0.70
    pad = int(cap_h_est * 1.1) + 8
    mask, cap_h = text_mask(text, fnt, tracking_em * size, pad)
    fill = gold_fill(mask, pad, cap_h)

    off = int(round(cap_h * 0.045))
    sm = gblur(np.roll(mask, off, axis=0), cap_h * 0.07) * shadow_a
    shadow_col = np.array([0.02, 0.04, 0.14], np.float32)

    a = mask + sm * (1.0 - mask)
    rgb = fill * mask[..., None] + shadow_col * (sm * (1.0 - mask))[..., None]
    base = np.concatenate([rgb, a[..., None]], -1).astype(np.float32)

    g = gblur(mask, cap_h * 0.10) * 0.55 + gblur(mask, cap_h * 0.38) * 0.45
    glow_col = np.array([1.0, 0.78, 0.36], np.float32)
    glow = np.concatenate([glow_col * g[..., None] * glow_gain, np.zeros_like(g)[..., None]], -1)
    # soft (defocused) version for the depth entrance
    soft = np.stack([gblur(base[..., c], cap_h * 0.12) for c in range(4)], -1)
    # additive gold used mid-fade so semi-transparent gold does not read as grey on blue
    warm = np.concatenate([fill * mask[..., None], np.zeros_like(mask)[..., None]], -1)
    return {"base": base, "glow": glow, "soft": soft, "warm": warm, "pad": pad, "cap_h": cap_h,
            "w": mask.shape[1], "h": mask.shape[0], "text_w": mask.shape[1] - 2 * pad}


def make_rule_asset(length, thick):
    """Thin gold horizontal line, tapered at both ends, premultiplied RGBA + glow."""
    pad = int(thick * 12)
    w, h = int(length) + 2 * pad, int(thick) + 2 * pad
    x = (np.arange(w, dtype=np.float32) - pad) / length       # 0..1 along the line
    y = np.arange(h, dtype=np.float32) - (pad + thick / 2.0)
    taper = np.clip(np.minimum(x, 1 - x) / 0.18, 0, 1) ** 1.3
    core = np.clip(thick / 2.0 + 0.5 - np.abs(y), 0, 1)
    mask = core[:, None] * taper[None, :]
    col = np.array([0.98, 0.84, 0.50], np.float32) + 0.12 * np.exp(-((x - 0.5) / 0.18) ** 2)[None, :, None]
    base = np.concatenate([np.clip(col, 0, 1) * mask[..., None], mask[..., None]], -1).astype(np.float32)
    g = gblur(mask, thick * 3.0) * 0.9
    glow = np.concatenate([np.array([1.0, 0.8, 0.4], np.float32) * g[..., None] * 0.6,
                           np.zeros_like(g)[..., None]], -1)
    return {"base": base, "glow": glow, "pad": pad, "w": w, "h": h, "length": length}

# ---------------------------------------------------------------- layout (world px at 4K)

TOP_TEXT = "PENGHARGAAN"
TITLE = ["KEPATUHAN", "INVENTARISASI DATA EMISI", "GAS RUMAH KACA"]
BOTTOM = ["KANTOR OTORITAS BANDAR UDARA", "WILAYAH V MAKASSAR"]

TITLE_MAX_W = 0.64 * W                     # widest title line; x1.035 push-in -> 66% < 70%
_probe = font("Bold", 1000)
TITLE_SIZE = TITLE_MAX_W / max(_probe.getlength(s) for s in TITLE) * 1000
TITLE_CAP = TITLE_SIZE * 0.70
TITLE_PITCH = 0.080 * H                   # line spacing = 8% of frame height
TOP_SIZE = 0.030 * H / 0.70               # cap height 3% of frame
BOT_SIZE = 0.035 * H / 0.70               # cap height 3.5% of frame
BOT_PITCH = BOT_SIZE * 0.70 * 1.75

GAP_TOP = 0.044 * H
GAP_RULE = 0.034 * H
GAP_BOT = 0.036 * H
RULE_THICK = 4.0
RULE_LEN = 0.30 * W

block_h = (TOP_SIZE * 0.7 + GAP_TOP + 2 * TITLE_PITCH + TITLE_CAP + GAP_RULE + RULE_THICK
           + GAP_BOT + BOT_PITCH + BOT_SIZE * 0.7)
Y_TOP = 0.465 * H - block_h / 2
Y_TITLE = [Y_TOP + TOP_SIZE * 0.7 + GAP_TOP + i * TITLE_PITCH for i in range(3)]
Y_RULE = Y_TITLE[2] + TITLE_CAP + GAP_RULE
Y_BOT = [Y_RULE + RULE_THICK + GAP_BOT + i * BOT_PITCH for i in range(2)]
Y_END = Y_BOT[1] + BOT_SIZE * 0.7
HORIZON = Y_END + 0.115 * H

# ---------------------------------------------------------------- precompute (module level, shared by fork)

ASSETS = None
WORLD_HALF = None
BEAM_GRID = None
DUST = None
BOKEH = None


def build():
    global ASSETS, WORLD_HALF, BEAM_GRID, DUST, BOKEH
    S = SMAX
    ASSETS = {
        "top": make_text_asset(TOP_TEXT, "SemiBold", TOP_SIZE * S, 0.42, glow_gain=0.16),
        "title": [make_text_asset(s, "Bold", TITLE_SIZE * S, 0.01, glow_gain=0.20) for s in TITLE],
        "bot": [make_text_asset(s, "SemiBold", BOT_SIZE * S, 0.07, glow_gain=0.14) for s in BOTTOM],
        "rule": make_rule_asset(RULE_LEN * S, RULE_THICK * S),
    }

    # ---- static world at half resolution: gradient, vignette, ghost word, floor
    hw, hh = W // 2, H // 2
    yy, xx = np.mgrid[0:hh, 0:hw].astype(np.float32)
    nx = (xx - hw / 2) / (hw / 2)
    ny = (yy - hh * 0.45) / (hh / 2)
    r = np.sqrt(nx * nx * 0.62 + ny * ny * 0.85)
    lift = np.exp(-r * r * 1.4)[..., None]
    img = ROYAL * (0.90 + 0.26 * lift)
    cx = np.abs(xx - hw / 2) / (hw / 2)
    cy = np.abs(yy - hh / 2) / (hh / 2)
    corner = np.clip((np.sqrt(cx ** 2 + cy ** 2) - 1.05) / 0.36, 0, 1) ** 1.6   # extreme corners only
    img = img * (1 - corner[..., None]) + NAVY * corner[..., None]

    # glossy floor
    hz = HORIZON / 2
    below = np.clip((yy - hz) / (hh - hz), 0, 1)[..., None]
    floor_mask = (yy >= hz)[..., None].astype(np.float32)
    img = img * (1 - floor_mask * (0.10 + 0.14 * below))
    sheen = np.exp(-((xx - hw / 2) / (hw * 0.32)) ** 2) * np.exp(-((yy - hz) / (hh * 0.05)) ** 2)
    img = img + sheen[..., None] * floor_mask * np.array([0.10, 0.13, 0.22], np.float32)
    line = np.exp(-((yy - hz) / 1.6) ** 2) * np.exp(-((xx - hw / 2) / (hw * 0.38)) ** 2)
    img = img + line[..., None] * np.array([0.10, 0.12, 0.20], np.float32)

    # ghost word, blurred, ~6% opacity, above the text block
    gf = font("ExtraBold", 0.060 * H / 0.70 / 2)
    gmask, _ = text_mask("AWARDS", gf, gf.size * 0.22, 40)
    gmask = gblur(gmask, 9.0)
    gy0 = int((Y_TOP * 0.42) / 2 - gmask.shape[0] / 2)
    gx0 = int(hw / 2 - gmask.shape[1] / 2)
    g = np.zeros((hh, hw), np.float32)
    g[gy0:gy0 + gmask.shape[0], gx0:gx0 + gmask.shape[1]] = gmask
    img = img * (1 - 0.06 * g[..., None]) + np.array([0.85, 0.88, 1.0], np.float32) * (0.06 * g[..., None])
    WORLD_HALF = img.astype(np.float32)

    # ---- beam geometry grid (quarter res, screen space)
    qw, qh = W // 4, H // 4
    qy, qx = np.mgrid[0:qh, 0:qw].astype(np.float32)
    BEAM_GRID = (qx, qy, qw, qh)

    rng = np.random.default_rng(7)
    n = 300
    DUST = {
        "x": rng.uniform(0, W, n), "y": rng.uniform(0, H, n), "z": rng.uniform(0, 1, n) ** 1.4,
        "ph": rng.uniform(0, 6.28, n), "tw": rng.uniform(0.6, 2.2, n),
        "sw": rng.uniform(0.04, 0.14, n), "d": rng.uniform(0.15, 2.0, n),
        "warm": rng.uniform(0, 1, n),
    }
    bx, by = [], []
    while len(bx) < 26:
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        in_text = abs(x - W / 2) < 0.36 * W and Y_TOP - 80 < y < Y_END + 80
        if in_text and rng.uniform() < 0.75:
            continue
        bx.append(x)
        by.append(y)
    nb = len(bx)
    BOKEH = {
        "x": np.array(bx), "y": np.array(by), "r": rng.uniform(28, 105, nb),
        "a": rng.uniform(0.035, 0.11, nb), "vx": rng.uniform(-6, 6, nb), "vy": rng.uniform(-9, -2, nb),
        "warm": rng.uniform(0, 1, nb), "d": rng.uniform(0.3, 1.8, nb), "ph": rng.uniform(0, 6.28, nb),
    }

# ---------------------------------------------------------------- per-frame layers

BEAMS = [  # origin x (fraction of W), rest angle (rad from vertical), width (rad), strength, sweep side
    (0.16, 0.30, 0.050, 0.10, -1),
    (0.34, 0.12, 0.040, 0.13, -1),
    (0.50, 0.00, 0.060, 0.11, 1),
    (0.66, -0.12, 0.040, 0.13, 1),
    (0.84, -0.30, 0.050, 0.10, 1),
]


def beams(t):
    qx, qy, qw, qh = BEAM_GRID
    out = np.zeros((qh, qw), np.float32)
    sweep = 1.0 - ease_out(prog(t, 0.0, 2.6))
    oy = -0.30 * qh
    fall = np.exp(-qy / (0.95 * qh)) * (0.35 + 0.65 * np.clip(qy / (0.08 * qh), 0, 1))
    for i, (fx, th, wd, st, side) in enumerate(BEAMS):
        ox = fx * qw
        theta = th + side * 0.55 * sweep + 0.03 * math.sin(0.55 * t + i * 1.7)
        phi = np.arctan2(qx - ox, qy - oy)
        streak = 0.82 + 0.18 * np.sin(phi * 90.0 + i * 2.1)
        out += st * np.exp(-((phi - theta) / wd) ** 2) * streak
    return out * fall


def cam_scale(t):
    return 1.0 + CAM_PUSH * smooth(t / DUR)


def world(t):
    s = cam_scale(t)
    hw, hh = W // 2, H // 2
    cw, ch = hw / s, hh / s
    box = ((hw - cw) / 2, (hh - ch) / 2, (hw + cw) / 2, (hh + ch) / 2)
    img = resize_f(WORLD_HALF, (hw, hh), box=box, resample=Image.BILINEAR)
    b = resize_f(beams(t), (hw, hh), resample=Image.BILINEAR)
    beam_col = np.array([0.80, 0.86, 1.0], np.float32) * 0.8 + np.array([1.0, 0.92, 0.75], np.float32) * 0.2
    bstr = 0.55 + 0.45 * ease_out(prog(t, 0.0, 2.0))
    img = 1.0 - (1.0 - img) * (1.0 - b[..., None] * beam_col * bstr)
    fade = smooth(prog(t, 0.0, 2.0))
    img = img * (0.25 + 0.75 * fade) + DARK_START * (0.75 * (1 - fade))
    return resize_f(img, (W, H), resample=Image.BILINEAR)


def splat(frame, cx, cy, sigma, col, amp):
    r = int(math.ceil(sigma * 3.2)) + 1
    x0, y0 = int(cx) - r, int(cy) - r
    xs = np.arange(x0, x0 + 2 * r + 1, dtype=np.float32) - cx
    ys = np.arange(y0, y0 + 2 * r + 1, dtype=np.float32) - cy
    k = np.exp(-(ys[:, None] ** 2 + xs[None, :] ** 2) / (2 * sigma * sigma)) * amp
    _add(frame, k, col, x0, y0)


def disc(frame, cx, cy, rad, col, amp):
    r = int(math.ceil(rad + 3))
    x0, y0 = int(cx) - r, int(cy) - r
    xs = np.arange(x0, x0 + 2 * r + 1, dtype=np.float32) - cx
    ys = np.arange(y0, y0 + 2 * r + 1, dtype=np.float32) - cy
    d = np.sqrt(ys[:, None] ** 2 + xs[None, :] ** 2)
    edge = np.clip((rad - d) / (rad * 0.12), 0, 1)
    rim = 1.0 + 0.35 * np.exp(-((d - rad * 0.9) / (rad * 0.08)) ** 2)
    _add(frame, edge * rim * amp, col, x0, y0)


def _add(frame, k, col, x0, y0):
    h, w = k.shape
    fx0, fy0 = max(0, x0), max(0, y0)
    fx1, fy1 = min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    kk = k[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    frame[fy0:fy1, fx0:fx1] += kk[..., None] * col


def particles(frame, t):
    s = cam_scale(t)
    D = DUST
    gold_a = np.array([1.0, 0.80, 0.42], np.float32)
    gold_b = np.array([1.0, 0.93, 0.72], np.float32)
    for i in range(len(D["x"])):
        a_in = smooth(prog(t, D["d"][i], D["d"][i] + 1.2))
        if a_in <= 0:
            continue
        z = D["z"][i]
        y = (D["y"][i] - (10 + 34 * z) * t) % (H + 120) - 60
        x = D["x"][i] + (10 + 30 * z) * math.sin(2 * math.pi * D["sw"][i] * t + D["ph"][i]) + 6 * t
        par = 1 + (s - 1) * (1.0 + 1.5 * z)
        x = W / 2 + (x - W / 2) * par
        y = H / 2 + (y - H / 2) * par
        tw = 0.55 + 0.45 * math.sin(D["tw"][i] * 2 * math.pi * t + D["ph"][i])
        sigma = 1.3 + 3.6 * z
        col = gold_a * (1 - D["warm"][i]) + gold_b * D["warm"][i]
        amp = (0.25 + 0.75 * z) * tw * a_in * 0.85
        splat(frame, x, y, sigma, col, amp)
        if z > 0.55:
            splat(frame, x, y, sigma * 3.5, col, amp * 0.06)
    B = BOKEH
    warm = np.array([1.0, 0.82, 0.50], np.float32)
    cool = np.array([0.75, 0.82, 1.0], np.float32)
    for i in range(len(B["x"])):
        a_in = smooth(prog(t, B["d"][i], B["d"][i] + 1.6))
        if a_in <= 0:
            continue
        x = B["x"][i] + B["vx"][i] * t
        y = B["y"][i] + B["vy"][i] * t
        x = W / 2 + (x - W / 2) * s
        y = H / 2 + (y - H / 2) * s
        breathe = 0.8 + 0.2 * math.sin(0.6 * t + B["ph"][i])
        col = warm * B["warm"][i] + cool * (1 - B["warm"][i])
        disc(frame, x, y, B["r"][i], col, B["a"][i] * a_in * breathe)


TITLE_CY = (Y_TITLE[0] + Y_TITLE[2] + TITLE_CAP) / 2


def flare(frame, t):
    p = prog(t, 3.95, 5.55)
    if p <= 0 or p >= 1:
        return
    env = math.sin(math.pi * p) ** 1.5
    s = cam_scale(t)
    xc = -0.15 * W + 1.30 * W * smooth(p)
    yc = H / 2 + (TITLE_CY - H / 2) * s
    xs = np.arange(W, dtype=np.float32) - xc
    ys = np.arange(H, dtype=np.float32) - yc
    streak = np.exp(-(ys / 5.0) ** 2)[:, None] * np.exp(-(xs / 1300.0) ** 2)[None, :]
    wide = np.exp(-(ys / 40.0) ** 2)[:, None] * np.exp(-(xs / 900.0) ** 2)[None, :]
    core = np.exp(-(ys / 170.0) ** 2)[:, None] * np.exp(-(xs / 170.0) ** 2)[None, :]
    halo = np.exp(-(ys / 520.0) ** 2)[:, None] * np.exp(-(xs / 520.0) ** 2)[None, :]
    frame += env * (streak[..., None] * np.array([0.55, 0.68, 0.95], np.float32) * 0.85
                    + wide[..., None] * np.array([0.35, 0.45, 0.75], np.float32) * 0.18
                    + core[..., None] * np.array([1.0, 0.86, 0.58], np.float32) * 0.45
                    + halo[..., None] * np.array([0.9, 0.75, 0.45], np.float32) * 0.10)


def place_text(canvas, asset, cx_world, cap_top_world, opacity, dy=0.0, sx=1.0, sy=1.0,
               glow_mult=1.0, soft_mix=0.0):
    S = SMAX
    if opacity <= 0.002:
        return
    base = asset["base"]
    if soft_mix > 0.001:
        base = base * (1 - soft_mix) + asset["soft"] * soft_mix
    layer = base * opacity + asset["glow"] * (opacity * glow_mult)
    if opacity < 0.999:   # a little extra gold light mid-fade so the blend with blue stays warm
        layer += asset["warm"] * (0.6 * opacity * (1 - opacity))
    pad = asset["pad"]
    ax = asset["w"] / 2.0                      # anchor: horizontal centre, vertical centre of caps
    ay = pad + asset["cap_h"] / 2.0
    if abs(sx - 1) > 1e-4 or abs(sy - 1) > 1e-4:
        nw, nh = max(1, int(round(asset["w"] * sx))), max(1, int(round(asset["h"] * sy)))
        layer = resize_f(layer, (nw, nh), resample=Image.BICUBIC)
        ax, ay = ax * nw / asset["w"], ay * nh / asset["h"]
    x = int(round(cx_world * S - ax))
    y = int(round((cap_top_world + asset["cap_h"] / S / 2 + dy) * S - ay))
    over(canvas, layer, x, y)


def text_layer(t):
    """Premultiplied RGBA at SMAX scale (world coords * SMAX), or None before the text appears."""
    if t < 1.95:
        return None
    S = SMAX
    cw, ch = int(round(W * S)), int(round(H * S))
    canvas = np.zeros((ch, cw, 4), np.float32)
    A = ASSETS

    p = prog(t, 2.0, 2.9)
    place_text(canvas, A["top"], W / 2, Y_TOP, smooth(min(1.0, p * 2.0)), dy=18 * (1 - ease_out(p)))

    for i in range(3):
        p = prog(t, 2.45 + 0.42 * i, 2.45 + 0.42 * i + 1.05)
        if p <= 0:
            continue
        e = ease_out(p)
        bump = math.sin(math.pi * min(1.0, p * 1.15)) if p < 0.87 else 0.0
        place_text(canvas, A["title"][i], W / 2, Y_TITLE[i], smooth(min(1.0, p * 2.4)),
                   dy=70 * (1 - e), sx=1 + 0.06 * (1 - e), sy=0.62 + 0.38 * e,
                   glow_mult=1.0 + 2.2 * bump, soft_mix=(1 - e) ** 2)

    # reflection of the main title on the floor (built from what is on the canvas so far)
    y0 = int((Y_TITLE[0] - TITLE_CAP * 0.35) * S)
    y1 = int((Y_TITLE[2] + TITLE_CAP * 1.35) * S)
    x0, x1 = int(W * S * 0.16), int(W * S * 0.84)
    region = canvas[y0:y1, x0:x1].copy()
    if region[..., 3].max() > 0.01:
        ref = region[::-1]
        rh = int(ref.shape[0] * 0.55)
        ref = resize_f(ref, (ref.shape[1], rh), resample=Image.BILINEAR)
        ref = np.stack([gblur(ref[..., c], 5.0) for c in range(4)], -1)
        fade = (np.clip(1 - np.arange(rh, dtype=np.float32) / rh, 0, 1) ** 1.8)[:, None, None]
        ref *= fade * 0.06
        over(canvas, ref, x0, int(HORIZON * S) + 4)

    p = prog(t, 4.0, 4.9)
    if p > 0:
        r = A["rule"]
        e = ease_out(p)
        half = r["length"] / 2 * e
        cx = r["w"] / 2
        xs = np.arange(r["w"], dtype=np.float32)
        reveal = np.clip((half - np.abs(xs - cx)) / 6.0 + 0.5, 0, 1)[None, :, None]
        layer = (r["base"] + r["glow"]) * reveal
        rx = int(round(W / 2 * S - cx))
        ry = int(round(Y_RULE * S - r["pad"]))
        over(canvas, layer, rx, ry)
        if p < 1:
            spark = (1 - p) ** 0.7
            for sgn in (-1, 1):
                hx = W / 2 * S + sgn * half
                k_w = 120
                xs2 = np.arange(-k_w, k_w + 1, dtype=np.float32)
                k = np.exp(-(xs2[None, :] ** 2 + xs2[:, None] ** 2) / (2 * 14.0 ** 2)) * spark
                k += np.exp(-(xs2[:, None] / 2.0) ** 2) * np.exp(-(xs2[None, :] / 70.0) ** 2) * spark * 0.8
                patch = np.concatenate([k[..., None] * np.array([1.0, 0.9, 0.6], np.float32),
                                        np.zeros_like(k)[..., None]], -1)
                over(canvas, patch, int(hx) - k_w, int(Y_RULE * S + RULE_THICK * S / 2) - k_w)

    for i in range(2):
        p = prog(t, 4.3 + 0.18 * i, 5.1 + 0.18 * i)
        place_text(canvas, A["bot"][i], W / 2, Y_BOT[i], smooth(min(1.0, p * 2.0)), dy=22 * (1 - ease_out(p)))
    return canvas


def render_frame(i):
    t = i / FPS
    frame = world(t)
    particles(frame, t)
    flare(frame, t)
    tl = text_layer(t)
    if tl is not None:
        s = cam_scale(t)
        cw, ch = tl.shape[1], tl.shape[0]
        vw, vh = cw / s, ch / s
        box = ((cw - vw) / 2, (ch - vh) / 2, (cw + vw) / 2, (ch + vh) / 2)
        tl = resize_f(tl, (W, H), box=box, resample=Image.LANCZOS)
        frame = tl[..., :3] + frame * (1.0 - np.clip(tl[..., 3:4], 0, 1))
    rng = np.random.default_rng(1000 + i)
    grain = rng.standard_normal((H, W), dtype=np.float32) * 1.1
    out = np.clip(frame * 255.0 + grain[..., None] + 0.5, 0, 255).astype(np.uint8)
    return out.tobytes()

# ---------------------------------------------------------------- audio

SR = 48000
HIT = 2.45


def _saw_add(f, t, nh=14, rolloff=1.0):
    """Band-limited saw via additive synthesis; f may be an array (glide)."""
    ph = 2 * np.pi * np.cumsum(f) / SR if np.ndim(f) else 2 * np.pi * f * t
    out = np.zeros_like(t)
    for k in range(1, nh + 1):
        out += np.sin(k * ph) / k ** rolloff
    return out


def _onepole(x, cutoff):
    """Time-varying one-pole low-pass; cutoff in Hz (array or scalar)."""
    c = np.broadcast_to(np.asarray(cutoff, np.float64), x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x)
    acc = 0.0
    for n in range(len(x)):
        acc += a[n] * (x[n] - acc)
        y[n] = acc
    return y


def synth_audio(path):
    n = int(SR * DUR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(3)
    L = np.zeros(n)
    R = np.zeros(n)

    # riser: string-like glide A2 -> A3 with tremolo, plus a filtered noise swell
    rmask = t < HIT
    tr = t[rmask]
    x = tr / HIT
    env = x ** 2.4 * (1 - np.exp(-(HIT - tr) / 0.012))
    trem = 1 - 0.25 * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(5 + 9 * x) / SR))
    for det, pan in [(-0.006, 0.3), (0.0, 0.5), (0.007, 0.7)]:
        f = 110 * 2 ** (x ** 1.6) * (1 + det)
        v = _saw_add(f, tr, nh=10, rolloff=1.3) * env * trem * 0.10
        L[rmask] += v * (1 - pan)
        R[rmask] += v * pan
    noise = rng.standard_normal(len(tr))
    swell = _onepole(noise, 250 + 7000 * x ** 2.5)
    swell = swell - _onepole(swell, 120)
    L[rmask] += swell * env * 0.25
    R[rmask] += np.roll(swell, 37) * env * 0.25

    # soft hit at HIT: sub boom, timpani-like body, chord stab, cymbal wash
    hm = t >= HIT
    th = t[hm] - HIT
    boom = np.sin(2 * np.pi * np.cumsum(38 + 40 * np.exp(-th / 0.12)) / SR) * np.exp(-th / 0.9)
    timp = sum(np.sin(2 * np.pi * 98 * r * th) * np.exp(-th / (0.7 / r)) * a
               for r, a in [(1, 1.0), (1.5, 0.5), (1.99, 0.35), (2.44, 0.2)])
    atk = 1 - np.exp(-th / 0.004)
    hit = (boom * 0.55 + timp * 0.22) * atk
    chord = [146.83, 220.0, 293.66, 369.99, 440.0]
    stab = sum(_saw_add(f, th, nh=8, rolloff=1.5) for f in chord) / len(chord)
    stab = _onepole(stab, 900 + 2500 * np.exp(-th / 0.4)) * (1 - np.exp(-th / 0.015)) * np.exp(-th / 1.4) * 0.35
    wash = rng.standard_normal(len(th))
    wash = wash - _onepole(wash, 3500)
    wash = wash * (1 - np.exp(-th / 0.06)) * np.exp(-th / 1.6) * 0.05
    L[hm] += hit + stab + wash
    R[hm] += hit + stab + np.roll(wash, 53)

    # sustained pad: Dadd9 voicing, slow attack, gentle filter motion
    pad_notes = [(73.42, 0.5), (110.0, 0.35), (146.83, 0.65), (220.0, 0.45),
                 (293.66, 0.55), (329.63, 0.6), (369.99, 0.4), (440.0, 0.7)]
    penv = (1 - np.exp(-th / 1.1)) * np.clip((DUR - HIT - th) / 1.2, 0, 1) ** 1.5
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * th)
    padL = np.zeros(len(th))
    padR = np.zeros(len(th))
    for f, pan in pad_notes:
        for det in (-0.0035, 0.0035):
            v = _saw_add(f * (1 + det), th, nh=6, rolloff=1.8)
            padL += v * (1 - pan) * (1 + det * 60)
            padR += v * pan * (1 - det * 60)
    cut = 700 + 500 * lfo
    padL = _onepole(_onepole(padL, cut), cut) * penv * 0.05
    padR = _onepole(_onepole(padR, cut), cut) * penv * 0.05
    L[hm] += padL
    R[hm] += padR

    # reverb: exponentially decaying noise IR, FFT convolution
    irn = int(SR * 3.2)
    irt = np.arange(irn) / SR
    def ir(seed):
        r = np.random.default_rng(seed).standard_normal(irn) * np.exp(-irt / 0.75)
        r[: int(SR * 0.012)] = 0
        return _onepole(r, 5000)
    def conv(x, h):
        m = len(x) + len(h)
        nfft = 1 << (m - 1).bit_length()
        return np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)[: len(x)]
    irL, irR = ir(11), ir(12)
    wetL, wetR = conv(L, irL), conv(R, irR)
    wl = np.abs(wetL).max() + 1e-9
    dl = np.abs(L).max() + 1e-9
    L = L + wetL / wl * dl * 0.45
    R = R + wetR / wl * dl * 0.45

    fade_out = np.clip((DUR - t) / 0.6, 0, 1)
    st = np.stack([L, R], -1) * fade_out[:, None]
    st = np.tanh(st / np.abs(st).max() * 1.2) / np.tanh(1.2) * 0.89   # ~ -1 dBFS peak
    pcm = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "award_title_4k.mp4"))
    ap.add_argument("--still", type=float, nargs="*", help="write PNG stills at these times and exit")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--crf", type=int, default=15)
    args = ap.parse_args()

    build()
    print(f"title size {TITLE_SIZE:.1f}px cap {TITLE_CAP / H * 100:.2f}% H, widest line "
          f"{max(a['text_w'] for a in ASSETS['title']) / SMAX / W * 100:.1f}% W; "
          f"bottom widest {max(a['text_w'] for a in ASSETS['bot']) / SMAX / W * 100:.1f}% W; "
          f"block {Y_TOP:.0f}-{Y_END:.0f}, horizon {HORIZON:.0f}", flush=True)

    if args.still is not None:
        for ts in args.still:
            fr = np.frombuffer(render_frame(int(round(ts * FPS))), np.uint8).reshape(H, W, 3)
            Image.fromarray(fr).save(os.path.join(HERE, f"still_{ts:05.2f}.png"))
            print("still", ts, flush=True)
        return

    wav = os.path.join(HERE, "audio.wav")
    synth_audio(wav)
    print("audio done", flush=True)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav,
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf), "-profile:v", "high",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", args.out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(args.jobs) as pool:
        for k, buf in enumerate(pool.imap(render_frame, range(NFRAMES), chunksize=1)):
            ff.stdin.write(buf)
            if k % 30 == 0:
                print(f"frame {k}/{NFRAMES}", flush=True)
    ff.stdin.close()
    sys.exit(ff.wait())


if __name__ == "__main__":
    main()
