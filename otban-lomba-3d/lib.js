// Shared papercraft-3D toolkit for the Rakorwil 2026 3D opening.
// Everything is deterministic: geometry from seeded randoms, animation from render(t).
import * as THREE from 'three';
import { TTFLoader } from './vendor/jsm/loaders/TTFLoader.js';
import { Font } from './vendor/jsm/loaders/FontLoader.js';
import { TextGeometry } from './vendor/jsm/geometries/TextGeometry.js';
export { THREE };

export const PAL = {
  navy: '#1F3375', navyDeep: '#152657', navyMid: '#2A4597', blue: '#3B5BB5', sky: '#8FD3FF',
  cream: '#F3EFE4', paper: '#FBF8F1', green: '#7BE0A1', greenDeep: '#3FAF7A', amber: '#F2C14E', coral: '#E8794A', teal: '#4FB3A6',
};

export function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

export function makeRenderer(canvasParent) {
  const r = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  r.setPixelRatio(1); r.setSize(1920, 1080);
  r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFShadowMap;
  r.outputColorSpace = THREE.SRGBColorSpace; r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = 1.05;
  canvasParent.appendChild(r.domElement);
  return r;
}

// paper fibre: a tiny tiling noise texture used as bump map → reads as card stock under raking light
let _paperTex = null;
export function paperBump() {
  if (_paperTex) return _paperTex;
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'); const R = rng(11);
  const img = g.createImageData(256, 256);
  for (let i = 0; i < img.data.length; i += 4) { const v = 118 + R() * 22 + (R() < .02 ? 30 : 0); img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
  g.putImageData(img, 0, 0);
  _paperTex = new THREE.CanvasTexture(c); _paperTex.wrapS = _paperTex.wrapT = THREE.RepeatWrapping; _paperTex.repeat.set(6, 6);
  return _paperTex;
}
export function paperMat(color, opts = {}) {
  return new THREE.MeshStandardMaterial({ color: new THREE.Color(color), roughness: .92, metalness: 0, bumpMap: paperBump(), bumpScale: .6, ...opts });
}
export function mesh(geo, mat, { cast = true, receive = true } = {}) { const m = new THREE.Mesh(geo, mat); m.castShadow = cast; m.receiveShadow = receive; return m; }
export const extrude = (shape, depth = .04) => new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false, curveSegments: 48 });

// Ring seen from inside a tunnel: plain outer circle, decorative INNER (hole) edge — the edge the viewer sees.
// kind: 'scallop' | 'zigzag' | 'wave' | 'plain'; teeth bumps point inward by amp.
export function ringShape(rOut, rIn, kind = 'scallop', teeth = 36, amp = .06, phase = 0) {
  const s = new THREE.Shape(); s.absarc(0, 0, rOut, 0, Math.PI * 2, false);
  const h = new THREE.Path(), N = Math.max(1, teeth) * 16;
  if (kind === 'plain') { h.absarc(0, 0, rIn, 0, Math.PI * 2, true); s.holes.push(h); return s; }
  for (let i = 0; i <= N; i++) {
    const a = -(i / N) * Math.PI * 2 + phase, u = (i / N * teeth) % 1;
    let k = 0;
    if (kind === 'scallop') k = Math.sin(u * Math.PI);
    else if (kind === 'zigzag') k = 1 - Math.abs(u * 2 - 1);
    else if (kind === 'wave') k = .5 + .5 * Math.sin(u * Math.PI * 2);
    const r = rIn - amp * k;
    i ? h.lineTo(Math.cos(a) * r, Math.sin(a) * r) : h.moveTo(Math.cos(a) * r, Math.sin(a) * r);
  }
  s.holes.push(h); return s;
}
// Horizontal strip with a decorative TOP edge (landscape layers): width w, height h, kind as ringShape
export function stripShape(w, h, kind = 'wave', teeth = 8, amp = .2, seed = 0) {
  const s = new THREE.Shape(), N = Math.max(1, teeth) * 16, R = rng(seed + 1);
  s.moveTo(-w / 2, -h);
  for (let i = 0; i <= N; i++) {
    const x = -w / 2 + w * i / N, u = (i / N * teeth) % 1; let k = 0;
    if (kind === 'scallop') k = Math.sin(u * Math.PI); else if (kind === 'zigzag') k = 1 - Math.abs(u * 2 - 1);
    else if (kind === 'wave') k = .5 + .5 * Math.sin(u * Math.PI * 2); else if (kind === 'hills') k = Math.pow(Math.sin(u * Math.PI), 1.6) * (.6 + .4 * Math.sin(i / N * 7 + seed));
    s.lineTo(x, amp * k);
  }
  s.lineTo(w / 2, -h); s.lineTo(-w / 2, -h); return s;
}
// Cloud bank: bumpy top edge made of arcs, flat-ish bottom. width w, base y, bump radii from rng
export function cloudShape(w, h, seed = 1, bumps = 6) {
  const R = rng(seed), s = new THREE.Shape(); s.moveTo(-w / 2, -h);
  s.lineTo(-w / 2, 0); let x = -w / 2; const step = w / bumps;
  for (let i = 0; i < bumps; i++) { const r = step * (.55 + R() * .35); const cx = x + step / 2, cy = (R() - .3) * h * .35; s.absarc(cx, cy, r, Math.PI, 0, true); x += step; }
  s.lineTo(w / 2, -h); s.lineTo(-w / 2, -h); return s;
}
// airport-pictogram airliner (same drawing as the 2D bumpers), nose → +x, ~1 unit long
export function planeShape() {
  const s = new THREE.Shape(), k = 1 / 100;
  const P = (pts) => { const sh = new THREE.Shape(); pts.forEach(([x, y], i) => i ? sh.lineTo(x * k, y * k) : sh.moveTo(x * k, y * k)); return sh; };
  const body = new THREE.Shape(); body.absellipse(.01, 0, .47, .045, 0, Math.PI * 2);
  return [body, P([[8, -4], [-8, -40], [-16, -40], [-10, -4]]), P([[8, 4], [-8, 40], [-16, 40], [-10, 4]]), P([[-34, -4], [-42, -18], [-48, -18], [-44, -4]]), P([[-34, 4], [-42, 18], [-48, 18], [-44, 4]])];
}
export function planeMesh(color = PAL.paper, depth = .02) {
  const g = new THREE.Group(); planeShape().forEach(sh => g.add(mesh(extrude(sh, depth), paperMat(color)))); return g;
}

const fontCache = {};
export async function loadFont(url) {
  if (fontCache[url]) return fontCache[url];
  const json = await new Promise((res, rej) => new TTFLoader().load(url, res, undefined, rej));
  return (fontCache[url] = new Font(json));
}
// centred 3D text; returns mesh with width in .userData.w
export function text3D(font, str, { size = 1, depth = .12, color = PAL.paper, side = null, bevel = .008, letterSpacing = 0, mats: matsOverride = null } = {}) {
  const geo = new TextGeometry(str, { font, size, height: depth, depth, curveSegments: 10, bevelEnabled: bevel > 0, bevelThickness: bevel, bevelSize: bevel * .8, bevelSegments: 2 });
  geo.computeBoundingBox(); const bb = geo.boundingBox;
  geo.translate(-(bb.max.x + bb.min.x) / 2, -(bb.max.y + bb.min.y) / 2, 0);
  const mats = matsOverride || (side ? [paperMat(color), paperMat(side)] : paperMat(color));
  const m = mesh(geo, mats); m.userData.w = bb.max.x - bb.min.x; m.userData.h = bb.max.y - bb.min.y; return m;
}

export function lights(scene, { key = [3, 4, 6], intensity = 2.4, hemi = .9, shadowBox = 6 } = {}) {
  scene.add(new THREE.HemisphereLight('#dfe8ff', '#1a2550', hemi));
  const d = new THREE.DirectionalLight('#fff6e8', intensity); d.position.set(...key); d.castShadow = true;
  d.shadow.mapSize.set(1024, 1024); d.shadow.radius = 3; d.shadow.bias = -.0004; d.shadow.normalBias = .01;
  Object.assign(d.shadow.camera, { left: -shadowBox, right: shadowBox, top: shadowBox, bottom: -shadowBox, near: .1, far: 60 });
  scene.add(d); scene.add(d.target); return d;
}

// standard stage: scale-to-fit preview, __seek/__ready recorder hooks
export function stage(renderer, scene, camera, render, duration) {
  const fit = () => { const k = Math.min(innerWidth / 1920, innerHeight / 1080); renderer.domElement.style.cssText = `width:${1920 * k}px;height:${1080 * k}px`; };
  addEventListener('resize', fit); fit();
  const draw = t => { render(t); renderer.render(scene, camera); };
  window.__duration = duration; window.__seek = t => draw(t);
  const qs = new URLSearchParams(location.search); const still = qs.has('t') ? parseFloat(qs.get('t')) : null;
  let t0 = performance.now();
  const tick = now => { if (window.__recording) return; draw(still ?? ((now - t0) / 1000) % duration); if (still == null) requestAnimationFrame(tick); };
  draw(still ?? 0); window.__ready = true; requestAnimationFrame(tick);
}

// ---------- animation helpers ----------
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const P = (t, a, b) => clamp((t - a) / (b - a));
export const lerp = (a, b, p) => a + (b - a) * p;
export const expoOut = p => p >= 1 ? 1 : 1 - Math.pow(2, -10 * p);
export const expoIn = p => p <= 0 ? 0 : Math.pow(2, 10 * (p - 1));
export const cubicIO = p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
export const backOut = p => { const c = 1.70158; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
// smooth piecewise keyframes [[t,v],...] with cubic in-out between keys
export function keys(K, t) { if (t <= K[0][0]) return K[0][1]; for (let i = 1; i < K.length; i++) if (t <= K[i][0]) return lerp(K[i - 1][1], K[i][1], cubicIO(P(t, K[i - 1][0], K[i][0]))); return K[K.length - 1][1]; }

// A row of per-letter 3D meshes, each hinged at its baseline (pivot group) so it can flip up like a paper tab.
// Returns {group, letters:[pivot], w, h}. Row is centred unless align='left'.
export function letterRow(font, str, { size = .5, depth = .06, color = PAL.paper, side = null, bevel = .006, tracking = 0, align = 'center', mats: matsOverride = null } = {}) {
  const g = new THREE.Group(), res = font.data.resolution || 1000, letters = []; let x = 0, h = size * .72;
  const mats = matsOverride || (side ? [paperMat(color), paperMat(side)] : paperMat(color));
  for (const ch of str) {
    const glyph = font.data.glyphs[ch] || font.data.glyphs['?']; const adv = (glyph ? glyph.ha : res / 2) * size / res;
    if (ch !== ' ') {
      // geometry keeps the font's own baseline (y=0) so descenders hang below it
      const geo = new TextGeometry(ch, { font, size, height: depth, depth, curveSegments: 8, bevelEnabled: bevel > 0, bevelThickness: bevel, bevelSize: bevel * .8, bevelSegments: 2 });
      const m = new THREE.Mesh(geo, mats); m.castShadow = false; m.receiveShadow = false;   // no cast/receive: avoids ghost copies on far layers
      const pivot = new THREE.Group(); pivot.position.x = x; pivot.add(m); g.add(pivot); letters.push(pivot);
    }
    x += adv + tracking * size;
  }
  const w = x - tracking * size; const off = align === 'center' ? -w / 2 : 0;
  g.children.forEach(c => c.position.x += off);
  return { group: g, letters, w, h };
}
// flip letters up (in) and away (out). stagger in seconds per letter.
export function animRow(row, t, tin, tout, { stagger = .045, dur = .55, outDur = .4 } = {}) {
  const n = row.letters.length; let any = false;
  row.letters.forEach((L, i) => {
    const pi = backOut(P(t, tin + i * stagger, tin + i * stagger + dur));
    const po = expoIn(P(t, tout + i * stagger * .5, tout + i * stagger * .5 + outDur));
    const vis = t >= tin + i * stagger && t < tout + i * stagger * .5 + outDur;
    L.visible = vis; if (vis) any = true;
    L.rotation.x = (-Math.PI / 2) * (1 - Math.min(1, pi)) + (Math.PI / 2) * po;  // lies flat → stands up → falls back
    L.scale.setScalar(.6 + .4 * Math.min(1, P(t, tin + i * stagger, tin + i * stagger + dur * .5)));
  });
  row.group.visible = any;
}
// Logo as a thin paper card with the PNG on its face (keeps alpha). height in world units.
export function logoCard(url, height) {
  const tex = new THREE.TextureLoader().load(url); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 4;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshStandardMaterial({ map: tex, transparent: true, roughness: .8, alphaTest: .02 }));
  m.castShadow = true; m.userData.ready = new Promise(res => { const chk = () => tex.image ? (m.scale.set(height * tex.image.width / tex.image.height, height, 1), res()) : setTimeout(chk, 20); chk(); });
  return m;
}
