// node render-loop.mjs [--fps=30] → videos/honorable-award-sultan-hasanuddin.mp4 (seamless loop, no audio)
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
const arg = (k, d) => { const a = process.argv.find(x => x.startsWith(`--${k}=`)); return a ? a.split('=')[1] : d; };
const fps = +arg('fps', 30), out = 'videos/honorable-award-sultan-hasanuddin.mp4', N = 4;
fs.mkdirSync('render', { recursive: true });
const browser = await chromium.launch({ args: ['--force-color-profile=srgb'] });
const T = 8, total = T * fps, per = Math.ceil(total / N);
await Promise.all(Array.from({ length: N }, async (_, k) => {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1528 } });
  page.on('pageerror', e => { console.error('pageerror', e.message); process.exitCode = 1; });
  await page.goto('file://' + path.resolve('poster.html'));
  await page.evaluate(() => window.__ready);
  const f0 = k * per, f1 = Math.min(total, f0 + per);
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', `render/c${k}.mp4`], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = f0; i < f1; i++) {
    await page.evaluate(t => window.renderFrame(t), i / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
}));
await browser.close();
fs.writeFileSync('render/list.txt', Array.from({ length: N }, (_, k) => `file 'c${k}.mp4'`).join('\n'));
await new Promise(r => spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', 'render/list.txt', '-c', 'copy', '-movflags', '+faststart', out], { stdio: 'inherit' }).on('close', r));
console.log('wrote', out);
