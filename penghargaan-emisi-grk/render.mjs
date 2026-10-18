// Deterministic frame-by-frame renderer for promo.html.
// usage: node render.mjs [--fps=30] [--out=render/video.mp4] [--stills=5,12.3,...] [--f0=0 --f1=<frames>]
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

const arg = (k, d) => { const a = process.argv.find(x => x.startsWith(`--${k}=`)); return a ? a.split('=')[1] : d; };
const fps = +arg('fps', 30);
const out = arg('out', 'render/video-silent.mp4');
const stills = arg('stills', null);
const html = 'file://' + path.resolve('promo.html');

fs.mkdirSync(path.dirname(out), { recursive: true });
const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--force-color-profile=srgb'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
page.on('pageerror', e => { console.error('pageerror:', e.message); process.exitCode = 1; });
page.on('console', m => { if (m.type() === 'error') console.error('console:', m.text()); });
await page.goto(html);
await page.evaluate(() => window.__ready);

if (stills) {
  for (const s of stills.split(',')) {
    await page.evaluate(t => window.renderFrame(t), +s);
    const f = path.join(path.dirname(out), `still-${(+s).toFixed(2)}.jpg`);
    await page.screenshot({ path: f, type: 'jpeg', quality: 90 });
    console.log('still', f);
  }
  await browser.close(); process.exit();
}

const END = await page.evaluate(() => window.END);
const total = Math.round(END * fps);
const f0 = +arg('f0', 0), f1 = Math.min(+arg('f1', total), total);   // frame range [f0, f1)
const n = f1 - f0;
const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
const t0 = Date.now();
for (let i = 0; i < n; i++) {
  await page.evaluate(t => window.renderFrame(t), (f0 + i) / fps);
  const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % 60 === 0) console.log(`frame ${i}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));
await browser.close();
console.log('wrote', out, n, 'frames in', ((Date.now() - t0) / 1000).toFixed(0), 's');
