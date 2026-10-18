// usage: node shoot.mjs <html> <outPrefix> [shots...]
import { chromium } from 'playwright';
import path from 'node:path';
const [, , html, out, ...shots] = process.argv;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('pageerror', e => console.error('pageerror:', e.message));
for (const s of shots.length ? shots : ['title', 'card']) {
  await page.goto('file://' + path.resolve(html) + '#' + s);
  await page.reload();
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${out}-${s}.png` });
  console.log('wrote', `${out}-${s}.png`);
}
await browser.close();
