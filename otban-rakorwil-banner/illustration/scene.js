// Isometric "ekosistem antarmoda" for the Rakorwil 2026 banner — our own low-poly model (client ref: flat isometric airport).
// One island = one ecosystem: runway + departing aircraft with green contrail, terminal with rooftop solar, gates, control tower,
// rail + train, road with buses/cars, port with ship + containers, onshore wind on a headland, solar-canopy e-bus depot,
// and a green dotted energy line (wind → terminal, branch → depot).
// buildScene(THREE, W, H) → { renderer, update(t, loop), anchors() }. Every motion uses whole cycles per loop → t=loop ≡ t=0.
export function buildScene(THREE, W, H) {
  const TAU = Math.PI * 2;
  const r = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  r.setPixelRatio(1); r.setSize(W, H, false); r.setClearColor(0x000000, 0);
  r.localClippingEnabled = true;   // land traffic is clipped at the island's x-edges (see below); the ship + tug are not
  r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap; r.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  const VS = 24.5, cam = new THREE.OrthographicCamera(-VS * W / H, VS * W / H, VS, -VS, -200, 400);
  cam.position.set(60, 62, 60); cam.lookAt(0, 0, 0); cam.updateMatrixWorld();
  scene.add(new THREE.HemisphereLight('#ffffff', '#5a6fae', 1.25));
  const sun = new THREE.DirectionalLight('#ffffff', 2.1); sun.position.set(18, 40, -6); sun.castShadow = true;
  sun.shadow.mapSize.set(4096, 4096); Object.assign(sun.shadow.camera, { left: -34, right: 34, top: 34, bottom: -34, near: 1, far: 120 }); sun.shadow.bias = -.0006; sun.shadow.normalBias = .02;
  scene.add(sun);
  const M = {}; const mat = c => M[c] || (M[c] = new THREE.MeshLambertMaterial({ color: c }));
  const C = { white: '#F4F6FB', grey: '#D5DEEF', mid: '#9FB0D6', glass: '#2F6FD0', glassD: '#1F4FA8', red: '#E5483B', navy: '#1F3375', green: '#5DB87A', greenD: '#3E9A5E',
    yellow: '#F2C14E', ground: '#4F7BCB', groundSide: '#22397F', apron: '#6189D4', asphalt: '#2A3F80', water: '#35A6DE', rail: '#C9D3EA', trunk: '#7A5A3A', teal: '#4FB3A6', orange: '#E8794A', solar: '#18306E' };
  function box(w, h, d, c, x, y, z, parent = scene, shadow = true) { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(c)); m.position.set(x, y + h / 2, z); m.castShadow = shadow; m.receiveShadow = true; parent.add(m); return m }
  function cyl(rt, rb, h, c, x, y, z, parent = scene, seg = 24) { const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat(c)); m.position.set(x, y + h / 2, z); m.castShadow = true; m.receiveShadow = true; parent.add(m); return m }
  function prism(pts, depth, c, parent) { const s = new THREE.Shape(pts.map(p => new THREE.Vector2(...p))); const g = new THREE.ExtrudeGeometry(s, { depth, bevelEnabled: false }); g.translate(0, 0, -depth / 2); const m = new THREE.Mesh(g, mat(c)); m.castShadow = true; m.receiveShadow = true; parent.add(m); return m }
  const G = () => { const g = new THREE.Group(); scene.add(g); return g };
  const flat = (w, d, c, x, z, y = 0) => box(w, .04, d, c, x, y, z, scene, false);

  /* ---------- island: land, headland, port water ---------- */
  box(29, 1.6, 28, C.ground, -5.5, -1.6, 0);                 // main land x[-20,9]
  box(11, 1.6, 10, C.ground, 14.5, -1.6, 9);                 // land strip by the port x[9,20] z[4,14]
  box(11, 1.6, 7, C.ground, 14.5, -1.6, -10.5);              // headland x[9,20] z[-14,-7] — onshore wind
  box(11, 1.2, 11, C.water, 14.5, -1.6, -1.5, scene, false); // port water x[9,20] z[-7,4], sits lower
  box(40.2, .5, 28.2, C.groundSide, 0, -2.1, 0, scene, false);
  flat(10.4, 6.4, C.green, 14.5, -10.5, 0);                  // headland grass
  flat(4, 27, C.asphalt, -16, 0);                            // runway along z
  for (let z = -12; z <= 12; z += 2.4) flat(.22, 1.2, C.white, -16, z, .05);
  [-1.4, -.7, .7, 1.4].forEach(dx => flat(.3, 1.8, C.white, -16 + dx, 12.2, .05));
  flat(16, 9.5, C.apron, -4, -8, 0); flat(2.2, 5, C.apron, -12.8, -8, 0);
  flat(40, 2.6, C.asphalt, 0, 10.2, 0); for (let x = -19; x <= 19; x += 2.2) flat(1.1, .14, C.white, x, 10.2, .05);
  flat(2.4, 7.5, C.asphalt, -4, 5.4, 0);
  flat(29.6, 1.4, '#3B5498', -5.2, 6.6, 0); [-.32, .32].forEach(dz => flat(29.6, .12, C.rail, -5.2, 6.6 + dz, .06));
  for (let x = -19.6; x <= 9.2; x += .8) flat(.14, 1.1, '#6E7FAE', x, 6.6, .03);
  flat(9, 1.2, C.grey, -3, 5.1, 0).scale.y = 6;
  flat(40, 2.2, C.green, 0, 12.9, 0); flat(3, 26, C.green, -12.9, -1, 0).scale.x = .6;
  flat(2, 11, '#8A98BF', 8, -1.5, 0);                        // pier x[7,9] z[-7,4]
  box(.5, .7, 1.6, C.grey, 9.9, 0, 6.6);                     // rail buffer stop at the port
  /* ---------- terminal (rooftop solar), gates, tower ---------- */
  const T = G(); T.position.set(-4, 0, -.2);
  box(16, 3.2, 5, C.white, 0, 0, 0, T); box(15.2, 2.4, .2, C.glass, 0, .4, 2.52, T, false);
  for (let x = -7.2; x <= 7.2; x += 1.2) box(.12, 2.4, .24, C.white, x, .4, 2.55, T, false);
  box(.2, 2.4, 4.2, C.glass, 8.02, .4, 0, T, false); box(17, .35, 6, C.grey, 0, 3.2, 0, T);
  for (let i = 0; i < 6; i++) for (let j = 0; j < 2; j++) { const p = box(2, .12, 1.6, C.solar, -5.6 + i * 2.25, 3.6, -1.1 + j * 2.1, T); p.rotation.x = -.18 }
  box(4, 4.6, 4, C.white, -9.5, 0, -.5, T); box(3.4, 3.4, .2, C.glass, -9.5, .6, 1.52, T, false);
  [-7.5, .5].forEach(x => { box(.9, .9, 3.4, C.grey, x, 1.6, -4.2); box(.5, 1.6, .5, C.mid, x, 0, -5.6) });
  const TW = G(); TW.position.set(-13.2, 0, 4.2);
  cyl(.9, 1.2, 7.5, C.white, 0, 0, 0, TW); cyl(1.9, 1.4, .8, C.white, 0, 7.5, 0, TW); cyl(1.8, 1.8, 1.3, C.glass, 0, 8.3, 0, TW); cyl(2.1, 2.1, .25, C.white, 0, 9.6, 0, TW);
  cyl(.06, .06, 1.4, C.mid, .6, 9.85, .2, TW, 6); cyl(.06, .06, 1, C.mid, -.5, 9.85, -.3, TW, 6);
  /* ---------- aircraft ---------- */
  function plane(tail = C.navy, s = 1) { const g = G(); g.scale.setScalar(s);
    const f = new THREE.Mesh(new THREE.CylinderGeometry(.6, .6, 8, 24), mat(C.white)); f.rotation.z = Math.PI / 2; f.castShadow = true; g.add(f);
    const n = new THREE.Mesh(new THREE.SphereGeometry(.6, 24, 16), mat(C.white)); n.scale.set(1.7, 1, 1); n.position.x = 4; n.castShadow = true; g.add(n);
    const tc = new THREE.Mesh(new THREE.ConeGeometry(.6, 2.4, 24), mat(C.white)); tc.rotation.z = Math.PI / 2; tc.position.set(-5.2, .12, 0); tc.castShadow = true; g.add(tc);
    box(6.2, .12, 1.22, C.glassD, -.2, .12, 0, g, false); const ck = box(.5, .22, 1.0, C.navy, 4.55, .16, 0, g, false); ck.rotation.z = -.5;
    const wing = prism([[1.4, .6], [-1.6, 6.2], [-2.5, 6.2], [-1, .6], [-1, -.6], [-2.5, -6.2], [-1.6, -6.2], [1.4, -.6]], .14, C.white, g); wing.rotation.x = Math.PI / 2; wing.position.y = -.2;
    const hs = prism([[-4.6, .3], [-5.9, 2.5], [-6.5, 2.5], [-6.1, .3], [-6.1, -.3], [-6.5, -2.5], [-5.9, -2.5], [-4.6, -.3]], .1, C.white, g); hs.rotation.x = Math.PI / 2; hs.position.y = .3;
    prism([[-3.8, .4], [-5.9, 3.1], [-6.7, 3.1], [-6.2, .4]], .14, tail, g);
    [-2.4, 2.4].forEach(z => { const e = new THREE.Mesh(new THREE.CylinderGeometry(.36, .32, 1.5, 20), mat(C.grey)); e.rotation.z = Math.PI / 2; e.position.set(.3, -.55, z); e.castShadow = true; g.add(e) });
    return g }
  const p1 = plane(C.navy); p1.position.set(-7.5, 1.05, -8.4); p1.rotation.y = -Math.PI / 2;
  const p2 = plane(C.red); p2.position.set(.5, 1.05, -8.4); p2.rotation.y = -Math.PI / 2;
  const p3 = plane(C.navy, 1.05); p3.rotation.order = 'YZX'; p3.rotation.set(0, Math.PI / 2, .22);
  /* ---------- train ---------- */
  function car(x, lead, dir = 1) { const g = G(); g.position.set(x, .15, 6.6);
    if (lead) { const m = prism([[0, 0], [5, 0], [5, .55], [4.1, 1.45], [0, 1.45]], 1.2, C.white, g); m.position.x = -2.5; if (dir < 0) g.rotation.y = Math.PI;
      const st = prism([[0, .35], [5.02, .35], [5.02, .6], [0, .6]], 1.24, C.red, g); st.position.x = -2.5; const wn = prism([[.3, .85], [4.2, .85], [3.95, 1.15], [.3, 1.15]], 1.24, C.glassD, g); wn.position.x = -2.5 }
    else { box(5, 1.45, 1.2, C.white, 0, 0, 0, g); box(5.02, .25, 1.24, C.red, 0, .35, 0, g, false); box(4.4, .3, 1.24, C.glassD, 0, .85, 0, g, false) }
    return g }
  // push-pull airport rail link (cabs at both ends): arrives from the west edge, dwells at the terminal station, departs west
  const TR = new THREE.Group(); scene.add(TR);
  [car(3.3, true), car(-1.9, false), car(-7.1, true, -1)].forEach(c => TR.attach(c));
  /* ---------- road traffic (moves in the loop) ---------- */
  function bus(c = C.red) { const g = G(); box(3.4, 1.25, 1.1, C.white, 0, .15, 0, g); box(3.42, .3, 1.12, c, 0, .15, 0, g, false); box(3.0, .38, 1.14, C.glassD, 0, .75, 0, g, false);
    [-1.1, 1.1].forEach(dx => [-.56, .56].forEach(dz => { const w = cyl(.2, .2, .12, '#1b2240', dx, 0, dz, g, 12); w.rotation.x = Math.PI / 2; w.position.y = .2 })); return g }
  function auto(c) { const g = G(); box(1.8, .45, .9, c, 0, .12, 0, g); box(1, .38, .8, C.glassD, -.1, .57, 0, g, false); return g }
  const traffic = [  // [object, lane z, direction, laps per loop, phase]
    [bus(), 9.6, 1, 1, .0], [bus(C.teal), 10.8, -1, 1, .35], [auto(C.red), 9.6, 1, 2, .55], [auto(C.yellow), 9.6, 1, 2, .2], [auto(C.white), 10.8, -1, 2, .75], [bus(C.green), 10.8, -1, 1, .82]];
  const fb = bus(); fb.position.set(-4, 0, 4.3); fb.rotation.y = Math.PI / 2;     // parked at the terminal kerb
  /* ---------- port: ship (along x), containers, crane ---------- */
  const S = G(); S.scale.setScalar(.62); const SH = new THREE.Group(); scene.add(SH); SH.add(S); S.rotation.y = Math.PI;   // bow toward the pier
  prism([[-6, 0], [5.2, 0], [6.6, 1.5], [-6, 1.5]], 3, C.navy, S); prism([[-6, 0], [5.2, 0], [5.5, .4], [-6, .4]], 3.04, C.red, S);
  box(2.4, 2.6, 2.6, C.white, -4.4, 1.5, 0, S); box(2.6, .25, 2.8, C.grey, -4.4, 4.1, 0, S); box(2.2, .5, 2.64, C.glassD, -4.4, 3.3, 0, S, false); cyl(.35, .35, 1.2, C.red, -5, 4.35, 0, S, 12);
  const CC = [C.red, C.teal, C.yellow, C.orange, C.glass, C.green];
  for (let i = 0; i < 4; i++) for (let j = 0; j < 2; j++) for (let k = 0; k < (i % 2 ? 2 : 1); k++) box(1.9, .8, 1.25, CC[(i * 2 + j + k) % 6], -1.6 + i * 1.95, 1.5 + k * .8, -.66 + j * 1.32, S);
  for (let i = 0; i < 2; i++) for (let k = 0; k < 2; k++) box(1.25, .8, 1.9, CC[(i + k + 2) % 6], 8.2, k * .8, -6 + i * 2.1);
  // tugboat (bow +x) on a towline from the ship's stern: pulls it out stern-first, holds back as it comes in bow-first
  const TUG = new THREE.Group(); scene.add(TUG);
  prism([[-1, 0], [.65, 0], [1.05, .5], [1.05, .6], [-1, .6]], .95, C.orange, TUG); prism([[-1, 0], [.65, 0], [.75, .14], [-1, .14]], .99, C.navy, TUG);
  box(1.95, .12, 1.0, '#1b2240', 0, .48, 0, TUG, false);                                  // rubber fender line
  box(.75, .5, .64, C.white, .15, .6, 0, TUG); box(.6, .14, .66, C.glassD, .2, .86, 0, TUG, false); box(.8, .08, .7, C.navy, .15, 1.1, 0, TUG);
  cyl(.12, .12, .45, C.yellow, -.4, .6, 0, TUG, 10); box(.12, .12, .5, C.navy, -.85, .6, 0, TUG, false);   // funnel + towing bitt
  const rope = new THREE.Mesh(new THREE.CylinderGeometry(.035, .035, 1, 6), mat('#E9EEF8')); scene.add(rope);
  const ropeA = new THREE.Vector3(), ropeB = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
  const crane = G(); crane.position.set(8.3, 0, -2.4);
  [[-.6, -.6], [.6, -.6], [-.6, .6], [.6, .6]].forEach(([x, z]) => box(.25, 5, .25, C.yellow, x, 0, z, crane)); box(6.5, .35, .5, C.yellow, 2.4, 5, 0, crane);
  /* ---------- onshore wind on the headland ---------- */
  const rotors = [];
  function turbine(x, z, h) { const g = G(); g.position.set(x, 0, z);
    cyl(.6, .7, .3, C.grey, 0, 0, 0, g, 16); cyl(.18, .34, h, C.white, 0, 0, 0, g, 16);
    const head = new THREE.Group(); head.position.y = h; head.rotation.y = -Math.PI / 4; g.add(head);   // rotor faces the iso camera
    box(1.3, .5, .55, C.white, -.2, -.25, 0, head); const hub = new THREE.Mesh(new THREE.SphereGeometry(.28, 12, 8), mat(C.white)); hub.position.x = .55; head.add(hub);
    const rot = new THREE.Group(); rot.position.x = .62; head.add(rot);
    for (let i = 0; i < 3; i++) { const b = new THREE.Mesh(new THREE.BoxGeometry(.1, h * .48, .34), mat(C.white)); b.geometry.translate(0, h * .24, 0); b.rotation.x = i * TAU / 3; b.castShadow = true; rot.add(b) }
    rotors.push(rot); return g }
  turbine(10.6, -8.6, 7.6); turbine(13.6, -12.6, 9.6); turbine(18.8, -12.8, 8.6);   // spread in screen x (x−z = 19, 26, 32)
  /* ---------- e-bus depot under a solar canopy ---------- */
  const dep = G(); dep.position.set(14.6, 0, 6.6); flat(9.6, 4.2, '#3D63B5', 14.6, 6.6, .02);
  for (let i = 0; i < 3; i++) for (const dz of [-1.7, 1.7]) box(.18, 2.6, .18, C.grey, -3.6 + i * 3.6, 0, dz, dep);
  for (let i = 0; i < 5; i++) for (let j = 0; j < 3; j++) { const p = box(1.8, .1, 1.15, C.solar, -3.7 + i * 1.85, 2.62, -1.2 + j * 1.2, dep); p.rotation.x = -.12 }
  const eb1 = bus(C.green); eb1.position.set(12.4, 0, 5.7); const eb2 = bus(C.green); eb2.position.set(16.6, 0, 7.5);
  [[10.6, 5.7], [14.8, 7.5]].forEach(([x, z]) => { box(.35, 1.1, .35, C.white, x, 0, z); box(.37, .25, .37, C.green, x, 1.1, z) });
  /* ---------- trees ---------- */
  function tree(x, z, s = 1) { cyl(.12 * s, .15 * s, .7 * s, C.trunk, x, 0, z, scene, 8); const t = new THREE.Mesh(new THREE.SphereGeometry(.75 * s, 10, 8), mat(C.greenD)); t.position.set(x, 1.25 * s, z); t.castShadow = true; scene.add(t) }
  for (let x = -19; x <= 19; x += 2.6) tree(x, 12.9 + (x % 2 ? .4 : -.3), .9 + ((x * 7) % 3) * .1);
  [[-13, -13], [-12.6, -1], [-12.7, 8.2], [6, -12.5], [2.5, -12.6], [17, 12.8], [12.6, -8.4], [16.2, -9.0], [19.2, -9.4]].forEach(([x, z]) => tree(x, z, 1));
  /* ---------- green energy line: wind → along the pier → terminal; branch → depot. Pulses travel along it in the loop ---------- */
  const energy = []; { const dot = new THREE.SphereGeometry(.15, 10, 8), gm = new THREE.MeshBasicMaterial({ color: '#7BE0A1' });
    const run = pts => { for (let i = 0; i < pts.length - 1; i++) { const [x1, z1] = pts[i], [x2, z2] = pts[i + 1], L = Math.hypot(x2 - x1, z2 - z1), n = Math.max(1, Math.round(L / .5));
      for (let k = 0; k < n; k++) { const t = k / n, m = new THREE.Mesh(dot, gm); m.position.set(x1 + (x2 - x1) * t, .12, z1 + (z2 - z1) * t); scene.add(m); energy.push(m) } } };
    run([[18.8, -12.8], [13.6, -12.6], [10.6, -8.6], [7.25, -7.4], [7.25, -1.2], [4.3, -1.2]]); run([[7.25, -1.2], [7.25, 3.4], [10.2, 4.6]]); }
  /* ---------- contrail (dots flow toward the aircraft, shrink and turn green) ---------- */
  const g0 = new THREE.Color('#C9D3EA'), g1 = new THREE.Color('#7BE0A1'), NC = 46, trail = [];
  for (let i = 0; i < NC; i++) { const m = new THREE.Mesh(new THREE.SphereGeometry(1, 12, 8), new THREE.MeshBasicMaterial({ color: '#fff' })); scene.add(m); trail.push(m) }
  const sm = (a, b, x) => { const u = Math.min(1, Math.max(0, (x - a) / (b - a))); return u * u * (3 - 2 * u) };

  /* ---------- clipping + fades ----------
     Train and road traffic slide in/out of the island edge (clip planes on their materials).
     The ship + tug are NOT clipped: the harbour mouth opens onto a strip of sea that fades into the background,
     and they fade out with distance as they sail into it (own material copies, transparent). */
  const PLANES = [new THREE.Plane(new THREE.Vector3(1, 0, 0), 20.12), new THREE.Plane(new THREE.Vector3(-1, 0, 0), 20.12)];
  const shipMats = [], tugMats = [], fadeSet = new Set();
  const own = (root, list) => root.traverse(m => { if (m.isMesh) { m.material = m.material.clone(); m.material.transparent = true; list.push(m.material); fadeSet.add(m) } });
  own(SH, shipMats); own(TUG, tugMats); own(rope, tugMats);
  scene.traverse(m => { if (m.isMesh && !fadeSet.has(m)) m.material.clippingPlanes = PLANES });
  { // open sea beyond the harbour mouth: wide plane whose alpha falls off away from the island (x) and toward its sides (z)
    const N = 256, c = document.createElement('canvas'); c.width = c.height = N; const g = c.getContext('2d'), id = g.createImageData(N, N);
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) { const u = i / (N - 1), v = j / (N - 1);
      const ax = Math.pow(1 - u, 1.6), az = sm(0, .22, v) * (1 - sm(.78, 1, v)), k = (j * N + i) * 4;
      id.data[k] = id.data[k + 1] = id.data[k + 2] = 255; id.data[k + 3] = Math.round(255 * ax * az) }
    g.putImageData(id, 0, 0);
    const sea = new THREE.Mesh(new THREE.PlaneGeometry(16, 34), new THREE.MeshLambertMaterial({ color: C.water, map: new THREE.CanvasTexture(c), transparent: true }));
    sea.material.map.colorSpace = THREE.SRGBColorSpace; sea.rotation.x = -Math.PI / 2; sea.position.set(28.05, -.4, -1.5); sea.renderOrder = -1; scene.add(sea); }
  // ship + tug recede into the distance: colour sinks to the background navy, opacity only goes at the very end (no see-through ghosting)
  const NAVY = new THREE.Color('#1F3375'), baseCol = new Map();
  [...shipMats, ...tugMats].forEach(m => { baseCol.set(m, m.color.clone()); if (!m.emissive) m.emissive = new THREE.Color(0) });
  const recede = (mats, k) => mats.forEach(m => { m.color.copy(baseCol.get(m)).multiplyScalar(k); m.emissive.copy(NAVY).multiplyScalar(.85 * (1 - k)); m.opacity = Math.min(1, k * 4) });
  const fade = (a, b, x) => 1 - sm(a, b, x);
  function update(t, loop) {
    const u = t / loop;
    rotors.forEach((rt, i) => rt.rotation.x = .35 + i * .9 + u * TAU * 4);                     // 4 turns per loop
    p3.position.set(-16, 8.5 + .22 * Math.sin(u * TAU * 2), -15.5); p3.rotation.x = .03 * Math.sin(u * TAU);
    trail.forEach((m, i) => { const k = ((i + u * NC) % NC) / NC;                           // one full traversal per loop
      const s = (.34 - .22 * k) * sm(0, .06, k) * (1 - sm(.95, 1, k)); m.scale.setScalar(Math.max(1e-4, s));
      m.position.set(-16, .45 + 6.5 * k * k, 4 - 13.2 * k); m.material.color.copy(g0).lerp(g1, k) });
    traffic.forEach(([o, z, dir, laps, ph]) => { let x = ((ph + u * laps) % 1) * 45 - 22.5; if (dir < 0) x = -x;   // clipped at the map edge
      o.position.set(x, 0, z); o.rotation.y = dir < 0 ? Math.PI : 0 });
    // train: dwell 10→2 s (wraps), depart west 2–6 s (accelerating), off-map 6–7 s, arrive from west 7–10 s (braking)
    const tr = t < 2 ? 0 : t < 6 ? -30 * Math.pow((t - 2) / 4, 2) : t < 7 ? -30 : t < 10 ? -30 * Math.pow(1 - (t - 7) / 3, 2) : 0;
    TR.position.x = tr;
    // ship: berthed 10.5→2.5 s, backs out east 2.5–6 s, off-map 6–6.5 s, arrives bow-first 6.5–10.5 s
    const sx = t < 2.5 ? 0 : t < 6 ? 12 * Math.pow((t - 2.5) / 3.5, 2) : t < 6.5 ? 12 : t < 10.5 ? 12 * Math.pow(1 - (t - 6.5) / 4, 2) : 0;
    // tug lead grows with ship speed (0 at rest → line goes slack-short at the berth, taut and long while towing)
    const lead = t < 2.5 ? 0 : t < 6 ? 0.8 * (t - 2.5) / 3.5 : t < 6.5 ? 0.8 : t < 10.5 ? 0.8 * (1 - (t - 6.5) / 4) : 0;
    const stern = 13.3 + sx + 6 * .62, by = -.55 + .07 * Math.sin(u * TAU * 2);
    TUG.position.set(stern + .3 + 1 + lead, -.5 + .06 * Math.sin(u * TAU * 2 + 1.3), -2.0); TUG.rotation.x = .02 * Math.sin(u * TAU * 3 + .7);
    ropeA.set(stern - .1, by + 1.1, -2.4); ropeB.set(TUG.position.x - .85, TUG.position.y + .66, -2.0);
    rope.position.copy(ropeA).add(ropeB).multiplyScalar(.5); rope.scale.y = ropeA.distanceTo(ropeB);
    rope.quaternion.setFromUnitVectors(up, ropeB.clone().sub(ropeA).normalize());
    const so = fade(20.4, 29.5, stern), to = fade(20.8, 29.5, TUG.position.x + 1.05);
    recede(shipMats, so); recede(tugMats, to);
    SH.visible = so > .002; TUG.visible = rope.visible = to > .002;
    SH.position.set(13.3 + sx, -.55 + .07 * Math.sin(u * TAU * 2), -2.4); SH.rotation.x = .012 * Math.sin(u * TAU * 3);
    energy.forEach((m, i) => { const w = .5 + .5 * Math.sin((u * 6 - i / 14) * TAU); m.scale.setScalar(.8 + .9 * Math.pow(w, 6)) });
    r.render(scene, cam);
  }
  const proj = v => { const p = new THREE.Vector3(...v).project(cam); return [(p.x + 1) / 2, (1 - p.y) / 2] };   // fractions of the canvas
  const anchors = () => ({ wind: proj([13.6, 10.2, -12.6]), depot: proj([14.6, 2.8, 6.6]), roof: proj([-4, 3.8, -.2]) });
  return { renderer: r, update, anchors };
}
