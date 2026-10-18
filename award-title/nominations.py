"""43-second nomination video: 3840x2160, 60 fps, gold 2.5D text on royal blue, synthesized score.

Usage:  python3 nominations.py [--still t ...] [--jobs n] [--crf n]
Reuses the text / gold / blur helpers from render.py.
"""
import argparse
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import cv2

cv2.setNumThreads(1)

import render as R
from render import gblur, resize_f, over, smooth, ease_out, prog

HERE = R.HERE
W, H = R.W, R.H
FPS = 60
DUR = 43.0
NFR = int(round(FPS * DUR))
SA = 1.10                 # text assets are rasterised at 110 % so placement only downsamples
HORIZON = 0.835 * H

GLOW_COL = np.array([1.0, 0.76, 0.34], np.float32)
SHADOW_COL = np.array([0.02, 0.04, 0.14], np.float32)
SHINE_COL = np.array([1.0, 0.97, 0.85], np.float32)
EDGE_COL = np.array([1.0, 0.80, 0.42], np.float32)
CORE_COL = np.array([1.0, 0.86, 0.52], np.float32)
PGLOW_COL = np.array([1.0, 0.66, 0.22], np.float32)

TOP = "PENGHARGAAN"
TITLE = ["KEPATUHAN", "INVENTARISASI DATA EMISI", "GAS RUMAH KACA"]
BOTTOM = ["KANTOR OTORITAS BANDAR UDARA", "WILAYAH V MAKASSAR"]
NOMS = [
    ("NOMINASI 1", "UNIT PENYELENGGARA BANDAR UDARA", "LAGALIGO-BUA"),
    ("NOMINASI 2", "BANDAR UDARA INTERNASIONAL", "SULTAN HASANUDDIN-MAKASSAR"),
    ("NOMINASI 3", "UNIT PENYELENGGARA BANDAR UDARA", "HALUOLEO-KENDARI"),
    ("NOMINASI 4", "UNIT PENYELENGGARA BANDAR UDARA", "MUTIARA SIS AL-JUFRI-PALU"),
    ("NOMINASI 5", "UNIT PENYELENGGARA BANDAR UDARA", "SYUKURAN AMINUDDIN AMIR-LUWUK"),
]

# ---------------------------------------------------------------- small helpers


def max_shift_into(dst, src, dx, dy):
    """dst = max(dst, src shifted by integer (dx, dy)), in place."""
    h, w = src.shape
    if abs(dx) >= w or abs(dy) >= h:
        return
    sx0, dx0 = (0, dx) if dx >= 0 else (-dx, 0)
    sy0, dy0 = (0, dy) if dy >= 0 else (-dy, 0)
    ww, hh = w - abs(dx), h - abs(dy)
    d = dst[dy0:dy0 + hh, dx0:dx0 + ww]
    np.maximum(d, src[sy0:sy0 + hh, sx0:sx0 + ww], out=d)


def bil(buf, x, y, w):
    """Bilinear point splat into a 2-D buffer via bincount."""
    if len(x) == 0:
        return
    hb, wb = buf.shape
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = (x - x0).astype(np.float32)
    fy = (y - y0).astype(np.float32)
    idx, ws = [], []
    for ddx, ddy, ww in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                         (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        xi, yi = x0 + ddx, y0 + ddy
        ok = (xi >= 0) & (xi < wb) & (yi >= 0) & (yi < hb)
        idx.append(yi[ok] * wb + xi[ok])
        ws.append((ww * w)[ok])
    buf += np.bincount(np.concatenate(idx), np.concatenate(ws), minlength=hb * wb).reshape(hb, wb).astype(np.float32)


class PBuf:
    """Particle light: sharp cores at half res, glow and defocused particles at quarter res."""

    def __init__(self):
        self.core = np.zeros((H // 2, W // 2), np.float32)
        self.glow = np.zeros((H // 4, W // 4), np.float32)
        self.soft = np.zeros((H // 4, W // 4), np.float32)
        self.used = False

    def sharp(self, x, y, w):
        if len(x):
            self.used = True
            bil(self.core, x / 2 - 0.5, y / 2 - 0.5, w)
            bil(self.glow, x / 4 - 0.5, y / 4 - 0.5, w * 0.5)

    def defocus(self, x, y, w):
        if len(x):
            self.used = True
            bil(self.soft, x / 4 - 0.5, y / 4 - 0.5, w)

    def light(self):
        """Half-res RGB light, or None."""
        if not self.used:
            return None
        q = (gaussian_filter(self.glow, 1.5) * 1.6 + gaussian_filter(self.glow, 5.0) * 1.2
             + gaussian_filter(self.soft, 4.0) * 3.0)
        q = cv2.resize(q, (W // 2, H // 2), interpolation=cv2.INTER_LINEAR)
        return self.core[..., None] * CORE_COL + q[..., None] * PGLOW_COL


_BUFS = {}


def pbuf(name, shape):
    """Per-process persistent buffer: first-touch page faults on fresh 100 MB arrays dominate otherwise."""
    b = _BUFS.get(name)
    if b is None:
        b = _BUFS[name] = np.zeros(shape, np.float32)
    return b


def up2(a, name):
    out = pbuf(name, (H, W, a.shape[2]))
    cv2.resize(a, (W, H), dst=out, interpolation=cv2.INTER_LINEAR)
    return out


def disc_half(img, cx, cy, rad, col, amp):
    """Soft bokeh disc drawn into a half-res buffer; coordinates in 4K px."""
    cx, cy, rad = cx / 2, cy / 2, rad / 2
    r = int(math.ceil(rad + 3))
    x0, y0 = int(cx) - r, int(cy) - r
    xs = np.arange(x0, x0 + 2 * r + 1, dtype=np.float32) - cx
    ys = np.arange(y0, y0 + 2 * r + 1, dtype=np.float32) - cy
    d = np.sqrt(ys[:, None] ** 2 + xs[None, :] ** 2)
    k = np.clip((rad - d) / (rad * 0.12), 0, 1) * (1.0 + 0.35 * np.exp(-((d - rad * 0.9) / (rad * 0.08)) ** 2)) * amp
    hh, ww = img.shape[:2]
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(ww, x0 + k.shape[1]), min(hh, y0 + k.shape[0])
    if fx1 > fx0 and fy1 > fy0:
        img[fy0:fy1, fx0:fx1] += k[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0, None] * col

# ---------------------------------------------------------------- text assets


def make_el(text, weight, cap_px, tracking_em, npts, seed):
    fnt = R.font(weight, cap_px / 0.70 * SA)
    pad = int(cap_px * SA * 0.95) + 12
    mask, cap_h = R.text_mask(text, fnt, tracking_em * fnt.size, pad)
    fill = R.gold_fill(mask, pad, cap_h)
    h, w = mask.shape
    u = (np.arange(h, dtype=np.float32) - pad) / cap_h
    side = np.stack([np.interp(u, [0, 1], [a, b]) for a, b in
                     [(0.70, 0.32), (0.48, 0.18), (0.16, 0.04)]], -1).astype(np.float32)
    off = max(1, int(round(cap_h * 0.06)))
    sh = np.zeros_like(mask)
    max_shift_into(sh, mask, 0, off)
    shadow = gblur(sh, cap_h * 0.08) * 0.5
    glow = gblur(mask, cap_h * 0.09) * 0.55 + gblur(mask, cap_h * 0.30) * 0.45
    rng = np.random.default_rng(seed)
    nz = rng.random((max(3, h // 20 + 2), max(3, w // 20 + 2))).astype(np.float32)
    nz = resize_f(nz, (w, h), resample=Image.BICUBIC)
    nz = (nz - nz.min()) / (nz.max() - nz.min() + 1e-6)
    xn = (np.arange(w, dtype=np.float32) / w)[None, :]
    n = (0.62 * xn + 0.38 * nz).astype(np.float32)
    yv = (np.arange(h, dtype=np.float32) - pad)[:, None]
    q = ((np.arange(w, dtype=np.float32)[None, :] + 0.5 * yv) / w).astype(np.float32)
    idx = np.flatnonzero(mask.ravel() > 0.6)
    sel = rng.choice(idx, size=min(npts, len(idx)), replace=False)
    ty, tx = np.divmod(sel, w)
    k = len(sel)
    upper = np.flatnonzero((ty - pad) < cap_h * 0.3)
    glints = rng.choice(upper, size=min(5, len(upper)), replace=False)
    return {
        "fill": fill, "mask": mask, "side": side, "shadow": shadow, "glow": glow, "n": n, "q": q,
        "w": w, "h": h, "pad": pad, "cap_h": cap_h,
        "tx": tx + rng.random(k), "ty": ty + rng.random(k), "tn": n.ravel()[sel],
        "r0": rng.uniform(0.25, 1.0, k) * w * 0.45 + 150, "a0": rng.uniform(0, 2 * np.pi, k),
        "spin": rng.choice([-1.0, 1.0]) * rng.uniform(1.6, 2.8, k), "dly": rng.uniform(0, 0.12, k),
        "z": rng.uniform(0, 1, k), "vx": rng.uniform(-160, 160, k), "vy": rng.uniform(-420, -90, k),
        "ph": rng.uniform(0, 6.28, k), "glint": glints,
    }


def compose(el, alpha, glow_k=1.0, shine=None, diss=None, ext=(0.0, 1.0)):
    m = el["mask"]
    keep = 1.0
    if diss is not None:
        d = el["n"] - diss
        mv = m * np.clip(d / 0.05, 0, 1)
        edge = np.exp(-(d / 0.03) ** 2) * m
        keep = float(np.clip(1.0 - diss, 0, 1))
    else:
        mv = m
    depth = el["cap_h"] * 0.075
    ex = np.zeros_like(mv)
    for k in range(1, 7):
        max_shift_into(ex, mv, int(round(ext[0] * depth * k / 6)), int(round(ext[1] * depth * k / 6)))
    sh = el["shadow"] * keep
    inv = (1.0 - mv)[..., None]
    rgb = el["fill"] * mv[..., None] + (el["side"][:, None, :] * ex[..., None]
                                        + SHADOW_COL * (sh * (1 - ex))[..., None]) * inv
    a = mv + (ex + sh * (1 - ex)) * (1 - mv)
    if shine is not None and -0.2 < shine < 1.3:
        band = np.exp(-((el["q"] - shine) / 0.045) ** 2) * mv
        rgb += band[..., None] * SHINE_COL * 0.85
    rgb += GLOW_COL * (el["glow"] * (0.2 * glow_k * keep))[..., None]
    if diss is not None:
        rgb += edge[..., None] * EDGE_COL * 1.6
    return np.concatenate([rgb, a[..., None]], -1) * alpha


def make_rule(length, thick):
    r = R.make_rule_asset(length * SA, thick * SA)
    r["layer"] = r["base"] + r["glow"]
    return r


def place(buf, layer, ax, ay, cx, cy, f):
    """Draw premultiplied layer so asset point (ax, ay) lands on screen (cx, cy), scaled by f (sub-pixel)."""
    h, w = layer.shape[:2]
    X, Y = cx - ax * f, cy - ay * f
    X0, Y0 = math.floor(X), math.floor(Y)
    ow, oh = int(math.ceil(w * f)) + 2, int(math.ceil(h * f)) + 2
    M = np.array([[f, 0, X - X0], [0, f, Y - Y0]], np.float64)
    interp = cv2.INTER_CUBIC if f > 0.6 else cv2.INTER_LINEAR
    out = cv2.warpAffine(layer, M, (ow, oh), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if interp == cv2.INTER_CUBIC:
        np.clip(out, 0, None, out=out)
        np.minimum(out[..., 3], 1.0, out=out[..., 3])
    over(buf, out, X0, Y0)


# ---------------------------------------------------------------- shots

SHOTS = []
WORLD_HALF = None
BEAM_GRID = None
DUST = None
BOKEH = None
GRAIN = None
STAR = None
_bf = R.font("Bold", 1000)
_sf = R.font("SemiBold", 1000)


def title_block(t0, maxw, top_cap, bot_cap, pitch, cy, grand):
    """Intro / finale title card elements. Returns element list and title centre y."""
    size = maxw / max(_bf.getlength(s) for s in TITLE) * 1000
    cap = size * 0.70
    g_top, g_rule, g_bot = 0.042 * H, 0.032 * H, 0.034 * H
    bot_pitch = bot_cap * 1.75
    total = top_cap + g_top + 2 * pitch + cap + g_rule + 4 + g_bot + bot_pitch + bot_cap
    y = cy - total / 2
    els = []
    seed = int(t0 * 10) + 100
    els.append({"el": make_el(TOP, "SemiBold", top_cap, 0.42, 500, seed), "y": y, "kind": "rise"})
    yt = y + top_cap + g_top
    for i, s in enumerate(TITLE):
        els.append({"el": make_el(s, "Bold", cap, 0.01, 2600 if grand else 2000, seed + 1 + i),
                    "y": yt + i * pitch, "kind": "swirl", "big": True})
    yr = yt + 2 * pitch + cap + g_rule
    els.append({"rule": make_rule(0.30 * W, 4.0), "y": yr, "kind": "rule"})
    yb = yr + 4 + g_bot
    for i, s in enumerate(BOTTOM):
        els.append({"el": make_el(s, "SemiBold", bot_cap, 0.07, 700, seed + 10 + i),
                    "y": yb + i * bot_pitch, "kind": "rise"})
    return els, yt + pitch + cap / 2


def build():
    global WORLD_HALF, BEAM_GRID, DUST, BOKEH, GRAIN, STAR
    # --- intro 0-7
    els, tcy = title_block(0, 0.68 * W, 0.030 * H, 0.033 * H, 0.080 * H, 0.45 * H, False)
    top, t1, t2, t3, rule, b1, b2 = els
    top.update(r=(1.7, 2.4))
    for i, e in enumerate((t1, t2, t3)):
        e.update(r=(1.85 + 0.25 * i, 3.0 + 0.25 * i))
    rule.update(r=(3.5, 4.1))
    b1.update(r=(3.7, 4.3))
    b2.update(r=(3.85, 4.45))
    for i, e in enumerate(els):
        e["x"] = 0.0
        e["exit"] = (6.40 + 0.02 * i, 6.95)
    SHOTS.append({"t0": 0.0, "t1": 7.0, "kind": "intro", "els": els, "sign": 1, "flare": (3.6, 5.2, tcy),
                  "bursts": [(0.5, 1.0)], "flashes": [(0.5, 0.9), (3.5, 0.35)]})
    # --- nominations
    for k, (lab, cat, name) in enumerate(NOMS):
        t0 = 7.0 + 6.0 * k
        lab_cap, cat_cap = 0.028 * H, 0.033 * H
        name_cap = min(0.075 * H, 0.74 * W / _bf.getlength(name) * 1000 * 0.70)
        g1, g2, g3 = 0.035 * H, 0.040 * H, 0.048 * H
        total = lab_cap + g1 + 4 + g2 + cat_cap + g3 + name_cap
        y = 0.46 * H - total / 2
        seed = 300 + 10 * k
        e_lab = {"el": make_el(lab, "SemiBold", lab_cap, 0.50, 450, seed), "y": y, "kind": "rise",
                 "r": (0.30, 0.95)}
        yr = y + lab_cap + g1
        e_rule = {"rule": make_rule(0.22 * W, 4.0), "y": yr, "kind": "rule", "r": (0.55, 1.15)}
        yc = yr + 4 + g2
        e_cat = {"el": make_el(cat, "SemiBold", cat_cap, 0.06, 900, seed + 1), "y": yc, "kind": "rise",
                 "r": (0.75, 1.40)}
        yn = yc + cat_cap + g3
        fly = k % 2 == 1
        e_name = {"el": make_el(name, "Bold", name_cap, 0.01, 2400, seed + 2), "y": yn,
                  "kind": "fly" if fly else "swirl", "r": (1.75, 2.5) if fly else (1.2, 2.5), "big": True}
        els = [e_lab, e_rule, e_cat, e_name]
        for i, e in enumerate(els):
            e["x"] = 0.0
            e["r"] = (t0 + e["r"][0], t0 + e["r"][1])
            e["exit"] = (t0 + 5.25 + 0.04 * i, t0 + 5.95)
        SHOTS.append({"t0": t0, "t1": t0 + 6.0, "kind": "nom", "els": els, "sign": -1 if k % 2 == 0 else 1,
                      "flare": None, "bursts": [(t0 + 2.5, 0.55)],
                      "flashes": [(t0, 0.55), (t0 + 2.5, 0.30)], "streak": (t0 - 0.05, 0.7)})
    # --- finale 37-43
    t0 = 37.0
    els, tcy = title_block(t0, 0.75 * W, 0.032 * H, 0.035 * H, 0.085 * H, 0.45 * H, True)
    top, t1, t2, t3, rule, b1, b2 = els
    top.update(r=(0.3, 0.9))
    for i, e in enumerate((t1, t2, t3)):
        e.update(r=(0.45 + 0.25 * i, 1.5 + 0.25 * i))
    rule.update(r=(2.0, 2.6))
    b1.update(r=(2.15, 2.75))
    b2.update(r=(2.27, 2.87))
    for e in els:
        e["x"] = 0.0
        e["r"] = (t0 + e["r"][0], t0 + e["r"][1])
        e["exit"] = None
    SHOTS.append({"t0": t0, "t1": 43.0, "kind": "finale", "els": els, "sign": 1,
                  "flare": (t0 + 1.9, t0 + 3.5, tcy), "bursts": [(t0, 0.9), (t0 + 2.0, 1.3)],
                  "flashes": [(t0, 0.6), (t0 + 2.0, 0.6)], "streak": (t0 - 0.05, 0.7)})

    # --- static world (half res): royal blue, centre lift, corner vignette, glossy floor, ghost word
    hw, hh = W // 2, H // 2
    yy, xx = np.mgrid[0:hh, 0:hw].astype(np.float32)
    nx = (xx - hw / 2) / (hw / 2)
    ny = (yy - hh * 0.45) / (hh / 2)
    lift = np.exp(-(nx * nx * 0.62 + ny * ny * 0.85) * 1.4)[..., None]
    img = R.ROYAL * (0.90 + 0.26 * lift)
    cx_ = np.abs(xx - hw / 2) / (hw / 2)
    cy_ = np.abs(yy - hh / 2) / (hh / 2)
    corner = np.clip((np.sqrt(cx_ ** 2 + cy_ ** 2) - 1.0) / 0.40, 0, 1) ** 1.5
    img = img * (1 - corner[..., None]) + R.NAVY * corner[..., None]
    hz = HORIZON / 2
    floor = (yy >= hz)[..., None].astype(np.float32)
    below = np.clip((yy - hz) / (hh - hz), 0, 1)[..., None]
    img = img * (1 - floor * (0.12 + 0.12 * below))
    sheen = np.exp(-((xx - hw / 2) / (hw * 0.34)) ** 2) * np.exp(-((yy - hz) / (hh * 0.05)) ** 2)
    img = img + sheen[..., None] * floor * np.array([0.10, 0.13, 0.22], np.float32)
    line = np.exp(-((yy - hz) / 1.6) ** 2) * np.exp(-((xx - hw / 2) / (hw * 0.40)) ** 2)
    img = img + line[..., None] * np.array([0.12, 0.14, 0.22], np.float32)
    gf = R.font("ExtraBold", 0.055 * H / 0.70 / 2)
    gmask, _ = R.text_mask("AWARDS", gf, gf.size * 0.22, 40)
    gmask = gblur(gmask, 10.0)
    gy0 = int(0.105 * hh - gmask.shape[0] / 2)
    gx0 = int(hw / 2 - gmask.shape[1] / 2)
    g = np.zeros((hh, hw), np.float32)
    g[gy0:gy0 + gmask.shape[0], gx0:gx0 + gmask.shape[1]] = gmask
    img = img * (1 - 0.06 * g[..., None]) + np.array([0.85, 0.88, 1.0], np.float32) * (0.06 * g[..., None])
    WORLD_HALF = img.astype(np.float32)

    qw, qh = W // 4, H // 4
    qy, qx = np.mgrid[0:qh, 0:qw].astype(np.float32)
    BEAM_GRID = (qx, qy, qw, qh)

    rng = np.random.default_rng(7)
    n = 420
    DUST = {"x": rng.uniform(0, W, n), "y": rng.uniform(0, H, n), "z": rng.uniform(0, 1, n),
            "ph": rng.uniform(0, 6.28, n), "tw": rng.uniform(0.5, 2.0, n), "sw": rng.uniform(0.04, 0.14, n)}
    bx, by = [], []
    while len(bx) < 28:
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        if abs(x - W / 2) < 0.38 * W and 0.2 * H < y < 0.75 * H and rng.uniform() < 0.75:
            continue
        bx.append(x)
        by.append(y)
    nb = len(bx)
    BOKEH = {"x": np.array(bx), "y": np.array(by), "r": rng.uniform(28, 110, nb), "a": rng.uniform(0.035, 0.10, nb),
             "vx": rng.uniform(-7, 7, nb), "vy": rng.uniform(-9, -2, nb), "warm": rng.uniform(0, 1, nb),
             "ph": rng.uniform(0, 6.28, nb), "z": rng.uniform(0.3, 1.0, nb)}
    GRAIN = [np.random.default_rng(50 + i).standard_normal((H, W), dtype=np.float32) * 0.9 for i in range(4)]
    s = np.arange(-60, 61, dtype=np.float32)
    STAR = (np.exp(-(s[:, None] ** 2 + s[None, :] ** 2) / (2 * 3.0 ** 2))
            + np.exp(-(s[:, None] / 1.3) ** 2) * np.exp(-np.abs(s[None, :]) / 16.0) * 0.8
            + np.exp(-(s[None, :] / 1.3) ** 2) * np.exp(-np.abs(s[:, None]) / 16.0) * 0.8).astype(np.float32)


def shot_at(t):
    for s in SHOTS:
        if s["t0"] <= t < s["t1"]:
            return s
    return SHOTS[-1]


def camera(t):
    """(scale, text x-offset, background x-offset, extrusion direction) for time t."""
    s = shot_at(t)
    tau, L = t - s["t0"], s["t1"] - s["t0"]
    if s["kind"] == "nom":
        sc = 0.955 + 0.045 * ease_out(prog(tau, 0, 2.6)) + 0.02 * tau / L
    else:
        sc = 0.91 + 0.09 * ease_out(prog(tau, 0, 4.0)) + 0.025 * tau / L
    phi = s["sign"] * (2 * smooth(tau / L) - 1)
    return sc, -24.0 * phi, 60.0 * phi, (0.45 * phi, 0.9)

# ---------------------------------------------------------------- background layers


BEAMS = [(0.14, 0.32, 0.050, 0.10), (0.32, 0.13, 0.040, 0.13), (0.50, 0.0, 0.060, 0.11),
         (0.68, -0.13, 0.040, 0.13), (0.86, -0.32, 0.050, 0.10)]
SWEEPS = [0.5, 7.0, 13.0, 19.0, 25.0, 31.0, 37.0, 39.0]


def beams(t):
    qx, qy, qw, qh = BEAM_GRID
    out = np.zeros((qh, qw), np.float32)
    sweep, boost = 0.0, 0.0
    for k, T in enumerate(SWEEPS):
        p = prog(t, T - 0.15, T + 1.6)
        if 0 < p < 1:
            sweep += (1 if k % 2 == 0 else -1) * 0.5 * math.sin(math.pi * p) * (1 - p)
            boost += 0.6 * math.sin(math.pi * p) ** 2
    oy = -0.30 * qh
    fall = np.exp(-qy / (0.95 * qh)) * (0.35 + 0.65 * np.clip(qy / (0.08 * qh), 0, 1))
    for i, (fx, th, wd, st) in enumerate(BEAMS):
        theta = th + sweep * (1 if i % 2 == 0 else 0.7) + 0.035 * math.sin(0.5 * t + i * 1.7)
        phi = np.arctan2(qx - fx * qw, qy - oy)
        streak = 0.82 + 0.18 * np.sin(phi * 90.0 + i * 2.1)
        out += st * np.exp(-((phi - theta) / wd) ** 2) * streak
    return out * fall * (1.0 + boost)


def world_brightness(t):
    if t < 0.5:
        return 0.10
    return 0.10 + 0.90 * smooth(prog(t, 0.5, 2.0))


def world(t, cam):
    sc, _, obg, _ = cam
    hw, hh = W // 2, H // 2
    s = 1.05 + (sc - 0.9) * 0.5              # background is far: half the dolly, opposite orbit offset
    M = np.array([[s, 0, (1 - s) * hw / 2 + obg / 2], [0, s, (1 - s) * hh / 2]], np.float64)
    img = cv2.warpAffine(WORLD_HALF, M, (hw, hh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    b = cv2.resize(beams(t), (hw, hh), interpolation=cv2.INTER_LINEAR)
    beam_col = np.array([0.84, 0.88, 1.0], np.float32)
    img = 1.0 - (1.0 - img) * (1.0 - b[..., None] * beam_col)
    k = world_brightness(t)
    return img * k + R.NAVY * (1 - k) * 0.45


def ambient(back, frame, t, cam):
    sc, otx, obg, _ = cam
    D = DUST
    a_in = smooth(prog(t, 0.4, 2.2))
    if a_in <= 0:
        return
    z = D["z"]
    y = (D["y"] - (10 + 40 * z) * t) % (H + 120) - 60
    x = D["x"] + (10 + 34 * z) * np.sin(2 * np.pi * D["sw"] * t + D["ph"]) + 5 * t
    par = 1 + (sc - 1) * (0.5 + 1.5 * z)
    x = W / 2 + (x - W / 2) * par + obg * (0.5 - 1.2 * z)
    y = H / 2 + (y - H / 2) * par
    tw = 0.55 + 0.45 * np.sin(D["tw"] * 2 * np.pi * t + D["ph"])
    amp = (0.25 + 0.75 * z) * tw * a_in
    near = z > 0.82
    back.sharp(x[~near], y[~near], amp[~near] * 0.9)
    back.defocus(x[near], y[near], amp[near] * 0.9)
    B = BOKEH
    warm = np.array([1.0, 0.82, 0.50], np.float32)
    cool = np.array([0.75, 0.82, 1.0], np.float32)
    for i in range(len(B["x"])):
        xb = B["x"][i] + B["vx"][i] * t
        yb = B["y"][i] + B["vy"][i] * t
        p = 1 + (sc - 1) * (1 + B["z"][i])
        xb = W / 2 + (xb - W / 2) * p - obg * B["z"][i]
        yb = H / 2 + (yb - H / 2) * p
        col = warm * B["warm"][i] + cool * (1 - B["warm"][i])
        br = 0.8 + 0.2 * math.sin(0.6 * t + B["ph"][i])
        disc_half(frame, xb, yb, B["r"][i], col, B["a"][i] * a_in * br)


def gauss_light(frame, cx, cy, sx, sy, col, amp, rows=None):
    """Separable gaussian light added to a half-res buffer; all arguments in 4K px."""
    cx, cy, sx, sy = cx / 2, cy / 2, sx / 2, sy / 2
    hh, ww = frame.shape[:2]
    xs = np.arange(ww, dtype=np.float32) - cx
    if rows is None:
        y0, y1 = 0, hh
    else:
        rows = rows / 2
        y0, y1 = max(0, int(cy - rows)), min(hh, int(cy + rows))
    if y1 <= y0:
        return
    ys = np.arange(y0, y1, dtype=np.float32) - cy
    g = np.exp(-(ys / sy) ** 2)[:, None] * np.exp(-(xs / sx) ** 2)[None, :]
    frame[y0:y1] += g[..., None] * (col * amp)


def lens_flare(frame, t, t0, t1, cy):
    p = prog(t, t0, t1)
    if p <= 0 or p >= 1:
        return
    env = math.sin(math.pi * p) ** 1.5
    xc = -0.15 * W + 1.30 * W * smooth(p)
    gauss_light(frame, xc, cy, 1300, 5.0, np.array([0.55, 0.68, 0.95], np.float32), 0.85 * env, rows=30)
    gauss_light(frame, xc, cy, 900, 40.0, np.array([0.35, 0.45, 0.75], np.float32), 0.18 * env, rows=200)
    gauss_light(frame, xc, cy, 170, 170, np.array([1.0, 0.86, 0.58], np.float32), 0.45 * env, rows=700)
    gauss_light(frame, xc, cy, 520, 520, np.array([0.9, 0.75, 0.45], np.float32), 0.10 * env)


def streak(frame, t, t0, dur, cy, direction):
    p = prog(t, t0, t0 + dur)
    if p <= 0 or p >= 1:
        return
    env = math.sin(math.pi * p)
    xc = (-0.2 + 1.4 * p) * W if direction > 0 else (1.2 - 1.4 * p) * W
    gauss_light(frame, xc, cy, 1500, 3.5, np.array([1.0, 0.85, 0.50], np.float32), 0.9 * env, rows=25)
    gauss_light(frame, xc, cy, 700, 28.0, np.array([1.0, 0.75, 0.35], np.float32), 0.15 * env, rows=150)


def flash(frame, t, T, amp):
    if t < T - 0.06 or t > T + 1.2:
        return
    e = (t - T + 0.06) / 0.06 if t < T else math.exp(-(t - T) / 0.22)
    gauss_light(frame, W / 2, 0.45 * H, 0.55 * W, 0.45 * H, np.array([1.0, 0.88, 0.62], np.float32), amp * e)


def burst(front, t, T, power, seed):
    a = t - T
    if a < 0 or a > 2.2:
        return
    rng = np.random.default_rng(seed)
    n = int(1600 * power)
    ang = rng.uniform(0, 2 * np.pi, n)
    v = rng.uniform(300, 2600, n) * power ** 0.5
    drag = 1.8
    d = v * (1 - np.exp(-drag * a)) / drag
    x = W / 2 + np.cos(ang) * d * 1.35
    y = 0.45 * H + np.sin(ang) * d * 0.8 + 90 * a * a
    life = rng.uniform(0.8, 2.0, n)
    w = np.clip(1 - a / life, 0, 1) ** 1.5 * rng.uniform(0.5, 1.4, n) * (0.6 + 0.4 * np.sin(rng.uniform(5, 14, n) * a))
    z = rng.uniform(0, 1, n)
    near = z > 0.85
    front.sharp(x[~near], y[~near], w[~near])
    front.defocus(x[near], y[near], w[near] * 1.5)

# ---------------------------------------------------------------- text per frame


def el_transform(e, cam, t):
    """Screen anchor (cx, cy) of the element's cap centre and its scale factor f (screen px / asset px)."""
    sc, otx, _, _ = cam
    el = e.get("el") or e["rule"]
    cap = el["cap_h"] / SA if "cap_h" in el else 4.0
    wx = W / 2 + e["x"]
    wy = e["y"] + cap / 2
    if e["kind"] == "rise":
        p = prog(t, *e["r"])
        wy += 26 * (1 - ease_out(p))
    cx = W / 2 + (wx - W / 2) * sc + otx
    cy = H / 2 + (wy - H / 2) * sc
    return cx, cy, sc / SA


def draw_text(t, cam, tbuf, front):
    """Composite all visible text into tbuf; spawn formation / dissolve particles into front."""
    any_text = False
    for shot in SHOTS:
        if not (shot["t0"] - 0.1 <= t < shot["t1"] + 1.6):
            continue
        in_shot = shot["t0"] <= t < shot["t1"]
        for e in shot["els"]:
            r0, r1 = e["r"]
            ex = e["exit"]
            if t < r0 - 0.05:
                continue
            cx, cy, f = el_transform(e, cam, t)
            if e["kind"] == "rule":
                if not in_shot:
                    continue
                r = e["rule"]
                p = ease_out(prog(t, r0, r1))
                fade = 1.0 if ex is None else 1 - smooth(prog(t, ex[0], ex[1]))
                xs = np.arange(r["w"], dtype=np.float32)
                half = r["length"] / 2 * p
                reveal = np.clip((half - np.abs(xs - r["w"] / 2)) / 6.0 + 0.5, 0, 1)[None, :, None]
                place(tbuf, r["layer"] * reveal * fade, r["w"] / 2, r["pad"] + r["h"] / 2 - r["pad"],
                      cx, cy, f)
                if 0 < p < 1:
                    for sgn in (-1, 1):
                        hx = cx + sgn * half * f
                        front.sharp(np.array([hx]), np.array([cy]), np.array([6.0 * (1 - p) + 2]))
                any_text = True
                continue
            el = e["el"]
            ax, ay = el["w"] / 2, el["pad"] + el["cap_h"] / 2
            X, Y = cx - ax * f, cy - ay * f
            alpha, glow_k, shine, diss = 1.0, 1.0, None, None
            kind = e["kind"]
            if kind == "rise":
                p = prog(t, r0, r1)
                alpha = smooth(min(1.0, p * 2.0))
                shine = -0.2 + 1.5 * prog(t, r1 - 0.15, r1 + 0.65)
            elif kind == "swirl":
                pg = prog(t, r0, r1)
                alpha = smooth(prog(pg, 0.62, 0.95))
                glow_k = 1.0 + 3.5 * math.exp(-((t - r1) / 0.14) ** 2)
                shine = -0.2 + 1.5 * prog(t, r1, r1 + 0.75)
                if pg < 1 or t < r1 + 0.4:
                    xn = el["tx"] / el["w"]
                    d = 0.32 * xn + el["dly"]
                    pi_ = np.clip((pg - d) / 0.56, 0, 1)
                    e3 = 1 - (1 - pi_) ** 3
                    ang = el["a0"] + el["spin"] * (1 - e3)
                    rad = el["r0"] * (1 - e3) ** 1.3 * f
                    tx = X + el["tx"] * f + np.cos(ang) * rad
                    ty = Y + el["ty"] * f + np.sin(ang) * rad * 0.6
                    w = np.clip(pi_ / 0.08, 0, 1) * (0.35 + 0.65 * np.sin(np.pi * np.clip(pi_, 0, 1)) ** 0.5)
                    w = w * np.clip(1 - (t - r1) / 0.4, 0, 1) * (1 if not e.get("big") else 0.8)
                    land = (pi_ >= 1)
                    w = np.where(land, w * 0.35, w)
                    near = el["z"] > 0.88
                    front.sharp(tx[~near], ty[~near], w[~near] * 0.9)
                    front.defocus(tx[near], ty[near], w[near] * 1.2)
            elif kind == "fly":
                pg = prog(t, r0, r1)
                alpha = smooth(min(1.0, pg * 3.0))
                glow_k = 1.0 + 3.5 * math.exp(-((t - r1) / 0.14) ** 2)
                shine = -0.2 + 1.5 * prog(t, r1, r1 + 0.75)
            if ex is not None and t >= ex[0]:
                pe = prog(t, ex[0], ex[1])
                diss = -0.08 + 1.16 * pe
                # released particles
                trel = ex[0] + (el["tn"] + 0.08) / 1.16 * (ex[1] - ex[0])
                a = t - trel
                live = (a > 0) & (a < 1.4)
                if live.any():
                    aa = a[live]
                    px = X + el["tx"][live] * f + el["vx"][live] * aa + 40 * np.sin(aa * 4 + el["ph"][live]) * aa
                    py = Y + el["ty"][live] * f + el["vy"][live] * aa - 60 * aa * aa
                    w = (0.5 + 1.2 * np.exp(-aa / 0.08)) * np.exp(-aa / 0.5)
                    near = el["z"][live] > 0.85
                    front.sharp(px[~near], py[~near], w[~near])
                    front.defocus(px[near], py[near], w[near] * 1.3)
                if pe >= 1:
                    continue
            if not in_shot or alpha <= 0.003:
                continue
            ext = cam[3]
            layer = compose(el, alpha, glow_k, shine, diss, ext)
            if kind == "fly" and t < r1:
                pg = prog(t, r0, r1)
                samples = [0.0, 0.035, 0.07, 0.105] if pg < 1 else [0.0]
                tot = 0
                for k, dt in enumerate(samples):
                    pk = prog(t - dt, r0, r1)
                    fk = f * (0.10 + 0.90 * ease_out(pk) ** 1.5)
                    wk = 1.0 / (1 + k)
                    tot += wk
                    place(tbuf, layer * (wk / sum(1.0 / (1 + j) for j in range(len(samples)))),
                          ax, ay, cx, cy, fk)
            else:
                place(tbuf, layer, ax, ay, cx, cy, f)
            any_text = True
            # specular glints during the hold
            if e.get("big") and t > r1 + 0.8 and (ex is None or t < ex[0]):
                for gi, gidx in enumerate(el["glint"]):
                    gy_, gx_ = divmod(int(gidx), el["w"])
                    tw = max(0.0, math.sin(2 * math.pi * (t * 0.45 + gi * 0.37 + shot["t0"] * 0.1))) ** 12
                    if tw > 0.02:
                        GLINTS.append((X + gx_ * f, Y + gy_ * f, 0.9 * tw))
    return any_text


GLINTS = []


def reflect(frame, tbuf):
    """Faint glossy-floor reflection of the text, built at half res."""
    th = tbuf[::2, ::2]
    a = th[..., 3]
    rows = np.flatnonzero(a.max(axis=1) > 0.02)
    if len(rows) == 0:
        return
    top, bot = rows[0], rows[-1] + 1
    hz = int(HORIZON / 2) + 2
    src = th[top:bot][::-1]
    rh = int(src.shape[0] * 0.5)
    if rh < 2:
        return
    ref = cv2.resize(np.ascontiguousarray(src), (src.shape[1], rh), interpolation=cv2.INTER_AREA)
    ref = cv2.GaussianBlur(ref, (0, 0), 3.0)
    fade = (np.clip(1 - np.arange(rh, dtype=np.float32) / rh, 0, 1) ** 1.8)[:, None, None]
    ref *= fade * 0.08
    ref = ref[:H // 2 - hz]
    d = frame[hz:hz + ref.shape[0]]
    d *= (1 - ref[..., 3:4])
    d += ref[..., :3]

# ---------------------------------------------------------------- frame


def render_frame(i):
    t = i / FPS
    cam = camera(t)
    half = world(t, cam)                       # everything soft lives at half res
    back, front = PBuf(), PBuf()
    ambient(back, half, t, cam)
    tbuf = pbuf("tbuf", (H, W, 4))
    last = _BUFS.get("tbuf_rows")
    if last is not None:
        tbuf[last[0]:last[1]] = 0
    GLINTS.clear()
    has_text = draw_text(t, cam, tbuf, front)
    if has_text:
        reflect(half, tbuf)
    bl = back.light()
    if bl is not None:
        half += bl
    for s in SHOTS:
        if s.get("flare"):
            lens_flare(half, t, s["flare"][0], s["flare"][1], H / 2 + (s["flare"][2] - H / 2) * cam[0])
        if s.get("streak"):
            streak(half, t, s["streak"][0], s["streak"][1], 0.30 * H, 1 if s["sign"] > 0 else -1)
            streak(half, t, s["streak"][0] + 0.12, s["streak"][1], 0.74 * H, -1 if s["sign"] > 0 else 1)
        for T, amp in s["flashes"]:
            flash(half, t, T, amp)
    for k, s in enumerate(SHOTS):
        for j, (T, pw) in enumerate(s["bursts"]):
            burst(front, t, T, pw, 900 + 10 * k + j)
    frame = up2(half, "frame")
    _BUFS["tbuf_rows"] = None
    if has_text:
        rows = np.flatnonzero(tbuf[::8, ::16, 3].max(axis=1) > 0) * 8
        if len(rows) == 0:
            rows = np.array([0, 8])
        y0, y1 = max(0, rows[0] - 8), min(H, rows[-1] + 16)
        _BUFS["tbuf_rows"] = (0, H)   # glow/shadow can extend beyond the alpha rows: clear all touched
        tb = tbuf[y0:y1]
        f = frame[y0:y1]
        f *= 1.0 - np.clip(tb[..., 3:4], 0, 1)
        f += tb[..., :3]
        star_col = np.array([1.0, 0.95, 0.82], np.float32)
        for gx, gy, amp in GLINTS:
            R._add(frame, STAR * amp, star_col, int(gx) - 60, int(gy) - 60)
    fl = front.light()
    if fl is not None:
        frame += up2(fl, "front")
    fade_out = 1.0 - smooth(prog(t, 41.9, 43.0))
    frame *= 255.0 * fade_out
    frame += GRAIN[i % 4][..., None]
    np.clip(frame, 0, 255, out=frame)
    return frame.astype(np.uint8).tobytes()


# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "nominations_4k60.mp4"))
    ap.add_argument("--still", type=float, nargs="*")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--crf", type=int, default=18)
    args = ap.parse_args()
    build()
    for s in SHOTS:
        for e in s["els"]:
            if "el" in e:
                el = e["el"]
                print(f"{s['kind']:7s} cap {el['cap_h'] / SA / H * 100:4.2f}%H  width "
                      f"{(el['w'] - 2 * el['pad']) / SA / W * 100:5.1f}%W", flush=True)
    if args.still is not None:
        for ts in args.still:
            fr = np.frombuffer(render_frame(int(round(ts * FPS))), np.uint8).reshape(H, W, 3)
            Image.fromarray(fr).save(os.path.join(HERE, f"nstill_{ts:05.2f}.png"))
            print("still", ts, flush=True)
        return
    import audio43
    wav = os.path.join(HERE, "audio43.wav")
    audio43.render(wav, DUR)
    print("audio done", flush=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav,
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf), "-profile:v", "high",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest", args.out]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(args.jobs) as pool:
        for k, buf in enumerate(pool.imap(render_frame, range(NFR), chunksize=2)):
            ff.stdin.write(buf)
            if k % 120 == 0:
                print(f"frame {k}/{NFR}", flush=True)
    ff.stdin.close()
    sys.exit(ff.wait())


if __name__ == "__main__":
    main()
