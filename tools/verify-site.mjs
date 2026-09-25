// verify-site.mjs — checks the site's animations in a real browser.
//
// Why a browser and not a review of the code: the headline reveal sets every
// character to opacity 0 and then animates it in. If the split or the observer
// fails, the hero text stays invisible — the page still loads, still returns 200,
// and still looks "fine" to a link checker, but the most important element on the
// page is gone. Only rendering it catches that.
//
// Run:  node tools/verify-site.mjs

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile, readdir, stat } from 'node:fs/promises';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5199;

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon', '.mp4': 'video/mp4',
  '.exe': 'application/octet-stream', '.zip': 'application/zip',
  '.msix': 'application/octet-stream', '.json': 'application/json',
};

const srv = createServer(async (req, res) => {
  try {
    let rel = decodeURIComponent(req.url.split('?')[0]);
    if (rel === '/' || rel.endsWith('/')) rel += 'index.html';
    const f = join(SITE, rel);
    if (!f.startsWith(SITE)) { res.writeHead(403).end(); return; }
    const body = await readFile(f);
    res.writeHead(200, { 'Content-Type': MIME[extname(f)] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404).end('not found');
  }
});
await new Promise((r) => srv.listen(PORT, '127.0.0.1', r));

const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);

if (!CHROME) { console.error('no browser found'); process.exit(1); }

const profile = mkdtempSync(join(tmpdir(), 'lw-verify-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9444',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--disable-extensions', '--hide-scrollbars',
  '--window-size=1440,900',
  `http://127.0.0.1:${PORT}/`,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9444/json/version');
      const j = await r.json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch { /* not up */ }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error('devtools endpoint never appeared');
}

const sock = new WebSocket(await wsUrl());
await new Promise((res, rej) => { sock.onopen = res; sock.onerror = rej; });

let id = 0;
const pending = new Map();
sock.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const { res, rej } = pending.get(m.id);
    pending.delete(m.id);
    m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
  }
};
const send = (method, params = {}, sessionId) => {
  const i = ++id;
  const p = { id: i, method, params };
  if (sessionId) p.sessionId = sessionId;
  return new Promise((res, rej) => { pending.set(i, { res, rej }); sock.send(JSON.stringify(p)); });
};

let target = null;
for (let i = 0; i < 60 && !target; i++) {
  const { targetInfos } = await send('Target.getTargets');
  target = targetInfos.find((t) => t.type === 'page' && t.url.includes(String(PORT)));
  if (!target) await new Promise((r) => setTimeout(r, 400));
}
const { sessionId } = await send('Target.attachToTarget', { targetId: target.targetId, flatten: true });
await send('Page.enable', {}, sessionId);
await send('Runtime.enable', {}, sessionId);

// Headless Chrome reports prefers-reduced-motion: reduce unless told otherwise,
// which makes the page disable its animations. Emulate an ordinary visitor for the
// main check, then a reduced-motion visitor separately.
await send('Emulation.setEmulatedMedia', {
  features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }],
}, sessionId);
await send('Page.reload', {}, sessionId);
await new Promise((r) => setTimeout(r, 2800));

const evalJs = async (expr) =>
  (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;

// ── 1. the hero must be readable ────────────────────────────────────────────
const hero = await evalJs(`(() => {
  const h1 = document.querySelector('h1');
  const ch = h1 && h1.querySelector('.ch');
  const cs = ch ? getComputedStyle(ch) : null;
  return {
    h1_text: h1 ? h1.textContent.replace(/\\s+/g, ' ').trim() : null,
    h1_chars: h1 ? h1.querySelectorAll('.ch').length : 0,
    first_char_opacity: cs ? cs.opacity : 'no-char',
    first_char_transform: cs ? cs.transform : 'no-char',
    grad_chars: document.querySelectorAll('.ch-grad').length,
    grad_bg: (() => { const g = document.querySelector('.ch-grad'); return g ? getComputedStyle(g).backgroundImage.slice(0, 48) : 'none'; })(),
  };
})()`);

console.log('  hero headline');
console.log('    text           :', hero.h1_text);
console.log('    split chars    :', hero.h1_chars);
console.log('    gradient chars :', hero.grad_chars);
console.log('    first char     : opacity', hero.first_char_opacity, '| transform', hero.first_char_transform);
console.log('');

// ── 2. scroll the whole page so every observer fires ───────────────────────
await evalJs(`(async () => {
  const step = 420;
  for (let y = 0; y <= document.body.scrollHeight; y += step) {
    window.scrollTo(0, y);
    await new Promise(r => setTimeout(r, 70));
  }
  window.scrollTo(0, 0);
  await new Promise(r => setTimeout(r, 1400));
  return true;
})()`);

const after = await evalJs(`(() => {
  const hidden = [];
  document.querySelectorAll('.reveal').forEach(el => {
    const o = getComputedStyle(el).opacity;
    if (parseFloat(o) < 0.05) {
      hidden.push((el.className || '').toString().slice(0, 40) + ' | ' + (el.textContent || '').trim().slice(0, 30));
    }
  });
  return {
    reveal_total: document.querySelectorAll('.reveal').length,
    reveal_in: document.querySelectorAll('.reveal.in').length,
    hidden,
    counters_total: document.querySelectorAll('[data-count]').length,
    counters_done: document.querySelectorAll('[data-count][data-counted="done"]').length,
    hero_stats: Array.from(document.querySelectorAll('.hero-stats b')).map(b => b.textContent.trim()),
    h2_chars: document.querySelectorAll('h2 .ch').length,
    shiny: document.querySelectorAll('.shiny').length,
  };
})()`);

console.log('  after scrolling the page');
console.log('    reveal elements :', after.reveal_in + '/' + after.reveal_total, 'visible');
console.log('    counters        :', after.counters_done + '/' + after.counters_total, 'completed');
console.log('    hero stats      :', after.hero_stats.join('  |  '));
console.log('    h2 chars        :', after.h2_chars);
console.log('    shiny labels    :', after.shiny);
if (after.hidden.length) {
  console.log('');
  console.log('    STILL HIDDEN:');
  after.hidden.forEach((h) => console.log('      ' + h));
}
console.log('');

// ── 3. screenshot the hero so the result can be seen ───────────────────────
await evalJs('window.scrollTo(0,0)');
await new Promise((r) => setTimeout(r, 700));
const shot = await send('Page.captureScreenshot', { format: 'png' }, sessionId);
const outShot = resolve(here, '..', 'build', 'site-hero.png');
const { writeFile } = await import('node:fs/promises');
await writeFile(outShot, Buffer.from(shot.data, 'base64'));
console.log('  screenshot:', outShot);

// ── verdict ────────────────────────────────────────────────────────────────
let pass = true;
const fail = (m) => { console.log('  FAIL ' + m); pass = false; };

if (!hero.h1_chars || hero.h1_chars < 10) fail('the h1 was not split into characters');
if (parseFloat(hero.first_char_opacity) < 0.9) fail('the first headline character is still invisible (opacity ' + hero.first_char_opacity + ')');
if (!hero.grad_chars) fail('no gradient characters found');
if (hero.grad_bg === 'none') fail('the gradient characters have no background image');
if (after.counters_done < after.counters_total) fail('some counters never ran');
if (after.hidden.length) fail(after.hidden.length + ' reveal element(s) stayed invisible');
if (!after.h2_chars) fail('no h2 headings were split');

console.log('');
console.log(pass ? '  PASS' : '  FAILED');

sock.close();
chrome.kill();
srv.close();
try { rmSync(profile, { recursive: true, force: true }); } catch { /* ignore */ }

process.exit(pass ? 0 : 1);
