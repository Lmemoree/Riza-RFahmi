// Gold/award toolkit for the Lomba Kebersihan winners loops. Builds on lib.js (papercraft toolkit).
import * as THREE from 'three';
import { RoomEnvironment } from './vendor/jsm/environments/RoomEnvironment.js';
import { PAL, rng } from './lib.js';

// studio reflections so metal reads as metal (no HDR file needed)
export function useStudioEnv(renderer, scene, intensity = 1) {
  const pm = new THREE.PMREMGenerator(renderer);
  scene.environment = pm.fromScene(new RoomEnvironment(), .04).texture;
  scene.environmentIntensity = intensity;
}
export const GOLD = { face: '#F4C15A', side: '#B9781E', deep: '#8C5A12' };
export const goldMat = (c = GOLD.face, rough = .32) => new THREE.MeshStandardMaterial({ color: new THREE.Color(c), metalness: 1, roughness: rough });

// floating gold sparks/embers rising (deterministic, loop-safe when LOOP divides their period)
export function sparks(scene, n = 120, seed = 3, area = [16, 9, 6]) {
  const R = rng(seed), geo = new THREE.SphereGeometry(1, 6, 4);
  const mat = new THREE.MeshBasicMaterial({ color: '#FFD27A', transparent: true, opacity: 1, toneMapped: false });
  const mesh = new THREE.InstancedMesh(geo, mat, n); scene.add(mesh);
  const P = [...Array(n)].map(() => ({ x: (R() - .5) * area[0], z: (R() - .5) * area[2] - 1, s: .015 + R() * .035, ph: R(), sway: R() * 6.28 }));
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), v = new THREE.Vector3(), sc = new THREE.Vector3();
  return (t, period) => {                                  // each spark rises through the frame once per `period`
    P.forEach((p, i) => {
      const u = ((t / period + p.ph) % 1);
      v.set(p.x + Math.sin(u * 6.28 + p.sway) * .35, -area[1] / 2 + u * area[1], p.z);
      const fade = Math.sin(u * Math.PI);                  // grow in/out so nothing pops at the loop seam
      sc.setScalar(p.s * fade); m4.compose(v, q, sc); mesh.setMatrixAt(i, m4);
    });
    mesh.instanceMatrix.needsUpdate = true;
  };
}
// soft fog band at the bottom (stacked translucent planes with a radial alpha texture)
export function fogBand(scene, color = '#3B5BB5', y = -3.6, layers = 5) {
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  const gr = g.createRadialGradient(64, 64, 4, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  const tex = new THREE.CanvasTexture(c); const R = rng(9); const puffs = [];
  for (let i = 0; i < layers * 6; i++) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: tex, color, transparent: true, depthWrite: false, opacity: .5 }));
    const s = 3 + R() * 4; m.scale.set(s * 1.8, s, 1); m.userData = { x0: (R() - .5) * 22, y: y + R() * 1.2, z: -2 + R() * 3, v: (R() - .5) * .3, ph: R() };
    scene.add(m); puffs.push(m);
  }
  return (t, period) => puffs.forEach(p => { const u = p.userData; p.position.set(u.x0 + Math.sin((t / period + u.ph) * 6.28) * 1.2, u.y, u.z); });
}
// lathe-turned trophy cup: profile points (radius, height) → LatheGeometry
export function trophy(mat) {
  const pts = [[0, 0], [.95, 0], [.95, .16], [.7, .2], [.62, .5], [.3, .62], [.18, .78], [.16, 1.15], [.3, 1.28], [.12, 1.4],
    [.2, 1.48], [.62, 1.6], [.92, 2.1], [1.02, 2.75], [.98, 2.8], [.9, 2.75], [.82, 2.2], [.5, 1.75], [0, 1.7]].map(([r, h]) => new THREE.Vector2(r, h));
  const g = new THREE.Group(); const cup = new THREE.Mesh(new THREE.LatheGeometry(pts, 96), mat); g.add(cup);
  // handles: half-tori whose open side faces the cup
  [-1, 1].forEach(s => { const h = new THREE.Mesh(new THREE.TorusGeometry(.4, .07, 16, 48, Math.PI), mat); h.position.set(s * .98, 2.3, 0); h.rotation.z = s > 0 ? -Math.PI / 2 : Math.PI / 2; g.add(h); });
  g.traverse(o => { o.castShadow = true; o.receiveShadow = true; });
  return g;
}
export { PAL };
