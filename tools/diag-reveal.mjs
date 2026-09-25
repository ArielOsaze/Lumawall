// diag-reveal.mjs — why does hero-meta stay hidden?
//
// Reports the element's position, its computed style, and whether the observer
// ever fired, so the cause is measured rather than guessed.

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const PORT = 5179;
const server = spawn('python', ['-m', 'http.server', String(PORT)], {
  cwd: new URL('../site', import.meta.url).pathname.replace(/^\//, ''),
  stdio: 'ignore',
});
await sleep(1500);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(`http://127.0.0.1:${PORT}/`);
await page.waitForTimeout(2500);

const before = await page.evaluate(() => {
  const el = document.querySelector('.hero-meta');
  const r = el.getBoundingClientRect();
  return {
    class: el.className,
    top: Math.round(r.top),
    bottom: Math.round(r.bottom),
    viewport_h: window.innerHeight,
    effective_bottom: window.innerHeight * 0.88,
    opacity: getComputedStyle(el).opacity,
    scroll_behavior: getComputedStyle(document.documentElement).scrollBehavior,
    doc_height: document.body.scrollHeight,
  };
});

console.log('  before scrolling:');
for (const [k, v] of Object.entries(before)) console.log(`    ${k}: ${v}`);

// Scroll in the same way the test does.
await page.evaluate(async () => {
  for (let y = 0; y <= document.body.scrollHeight; y += 300) {
    window.scrollTo(0, y);
    await new Promise((r) => setTimeout(r, 120));
  }
  window.scrollTo(0, 0);
});
await page.waitForTimeout(2600);

const after = await page.evaluate(() => {
  const el = document.querySelector('.hero-meta');
  return {
    class: el.className,
    opacity: getComputedStyle(el).opacity,
    scroll_y_at_end: window.scrollY,
  };
});

console.log('  after scrolling:');
for (const [k, v] of Object.entries(after)) console.log(`    ${k}: ${v}`);

console.log('');
console.log('  DIAGNOSIS:');
if (!after.class.includes('in')) {
  if (before.scroll_behavior === 'smooth') {
    console.log('    smooth scrolling: window.scrollTo animates, so repeated calls');
    console.log('    every 120ms interrupt each other and the page never settles at');
    console.log('    the intermediate offsets the observer needs.');
  } else {
    console.log('    the observer never saw the element intersect.');
  }
} else {
  console.log('    the element did reveal; the earlier failure was a timing artifact.');
}

await browser.close();
server.kill();
