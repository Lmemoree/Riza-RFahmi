// Shared helpers for the Rakorwil 2026 banners. Each design page: 1920x1080 #stage, ?v=1 (RAN GRK) | ?v=2 (Antarmoda).
window.V = +(new URLSearchParams(location.search).get('v') || 1);
window.COPY = {
  1: { tag: 'Program', title: ['RAN GRK di Sektor', 'Transportasi Udara'], sub: 'Rencana Aksi Nasional Penurunan Emisi Gas Rumah Kaca' },
  2: { tag: 'Sinergi', title: ['Sinergi Transportasi', 'Antarmoda'], sub: 'Udara · Laut · Darat · Perkeretaapian' },
}[window.V];
window.EVENT = {
  name: 'Rapat Koordinasi Wilayah',
  theme: 'Sinergi Transportasi Antarmoda dan Penurunan Emisi Gas Rumah Kaca di Kawasan Bandar Udara',
  org: ['Kementerian Perhubungan', 'Direktorat Jenderal Perhubungan Udara', 'Kantor Otoritas Bandar Udara Wilayah V Makassar'],
  place: 'Makassar', date: 'Selasa, 20 Oktober 2026',
};
const NS = 'http://www.w3.org/2000/svg';
window.el = (tag, attrs = {}, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
// Indonesia outline into an <svg> group: s = scale, (x,y) = top-left of the 1600x620 map box
window.drawMap = (g, { x = 0, y = 0, s = 1, fill = '#2E4A9A', stroke = 'none', sw = 1 } = {}) => {
  g.setAttribute('transform', `translate(${x} ${y}) scale(${s})`);
  el('path', { d: IDN.d, fill, stroke, 'stroke-width': sw / s, 'vector-effect': 'non-scaling-stroke' }, g);
  return name => { const [px, py] = IDN.pts[name]; return [x + px * s, y + py * s]; };
};
// MDI icon (24x24) placed centred at (cx,cy) with size sz
window.icon = (parent, name, cx, cy, sz, fill, rot = 0) => {
  const g = el('g', { transform: `translate(${cx} ${cy}) rotate(${rot}) scale(${sz / 24}) translate(-12 -12)` }, parent);
  el('path', { d: ICON[name], fill }, g); return g;
};
// quadratic arc between two points, bulging by k * distance (perpendicular, to the left)
window.arcPath = ([x1, y1], [x2, y2], k = .25) => {
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2, dx = x2 - x1, dy = y2 - y1;
  return `M${x1} ${y1} Q${mx + dy * k} ${my - dx * k} ${x2} ${y2}`;
};
// scale the 1920x1080 stage to the window (letterboxed)
window.fit = () => { const s = Math.min(innerWidth / 1920, innerHeight / 1080); document.getElementById('stage').style.transform = `scale(${s})`; };
addEventListener('resize', () => fit());
