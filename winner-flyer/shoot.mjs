// node shoot.mjs "v=A&w=1" out.png
import { chromium } from 'playwright';
import path from 'node:path';
const [, , qs, out] = process.argv;
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1080, height: 1080 } });
p.on('pageerror', e => console.error('pageerror', e.message));
await p.goto('file://' + path.resolve('flyer.html') + '?' + qs);
await p.evaluate(() => window.__ready);
await p.waitForTimeout(200);
await p.screenshot({ path: out });
await b.close();
console.log('wrote', out);
