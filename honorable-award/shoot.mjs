// node shoot.mjs <t> <out.png>
import { chromium } from 'playwright';
import path from 'node:path';
const [, , t, out] = process.argv;
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1080, height: 1528 } });
p.on('pageerror', e => console.error('pageerror', e.message));
await p.goto('file://' + path.resolve('poster.html') + '?t=' + t);
await p.evaluate(() => window.__ready);
await p.screenshot({ path: out });
await b.close(); console.log('wrote', out);
