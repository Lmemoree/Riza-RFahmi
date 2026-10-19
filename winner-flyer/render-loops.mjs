// Renders one seamless loop per winner: node render-loops.mjs [--fps=30] [--w=1,2,3]
// Frames t = 0 .. T-1/fps (frame T would equal frame 0), H.264, no audio track.
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
const arg = (k, d) => { const a = process.argv.find(x => x.startsWith(`--${k}=`)); return a ? a.split('=')[1] : d; };
const fps = +arg('fps', 30), winners = arg('w', '1,2,3').split(',').map(Number);
const NAMES = { 1: 'winner-1-mutiara-sis-al-jufri', 2: 'winner-2-syukuran-aminuddin-amir', 3: 'winner-3-haluoleo' };
fs.mkdirSync('render', { recursive: true }); fs.mkdirSync('videos', { recursive: true });
const browser = await chromium.launch({ args: ['--force-color-profile=srgb'] });
await Promise.all(winners.map(async w => {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1080 } });
  page.on('pageerror', e => { console.error(`w${w} pageerror:`, e.message); process.exitCode = 1; });
  await page.goto('file://' + path.resolve('flyer.html') + `?v=B&w=${w}`);
  await page.evaluate(() => window.__ready);
  const T = await page.evaluate(() => window.LOOP_T), n = Math.round(T * fps);
  const out = `videos/${NAMES[w]}.mp4`;
  const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.renderFrame(t), i / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 60 === 0) console.log(`w${w} frame ${i}/${n}`);
  }
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
  console.log('wrote', out, n, 'frames');
}));
await browser.close();
