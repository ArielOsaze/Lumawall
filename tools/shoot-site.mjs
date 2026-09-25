// shoot-site.mjs — captures the whole page in viewport-sized slices.
//
// One tall screenshot is unreadable when scaled down for review, so this captures
// each screenful at full width and writes a PNG per slice.
//
// Uses the Chrome DevTools Protocol directly, the same way verify-site.mjs does,
// so there is no extra dependency to install.
//
// Run:  node tools/shoot-site.mjs [outdir]

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5181;
const OUT = resolve(here, process.argv[2] || '../build/shots');
mkdirSync(OUT, { recursive: true });

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp',
  '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.mp4': 'video/mp4',
  '.woff2': 'font/woff2', '.json': 'application/json',
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

const profile = mkdtempSync(join(tmpdir(), 'lw-shoot-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9447',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--disable-extensions', '--hide-scrollbars',
  '--window-size=1440,900',
  `http://127.0.0.1:${PORT}/`,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9447/json/version');
      const j = await r.json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch { /* not up yet */ }
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
await send('Emulation.setEmulatedMedia', {
  features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }],
}, sessionId);
await send('Page.reload', {}, sessionId);
await new Promise((r) => setTimeout(r, 2500));

const evalJs = async (expr) =>
  (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;

await evalJs('(async () => { await document.fonts.ready; return true; })()');

// Reveal everything first, so no slice is captured mid-animation.
await evalJs(`(async () => {
  for (let y = 0; y <= document.body.scrollHeight; y += 300) {
    window.scrollTo({ top: y, behavior: 'instant' });
    await new Promise(r => setTimeout(r, 90));
  }
  window.scrollTo({ top: 0, behavior: 'instant' });
  await new Promise(r => setTimeout(r, 2400));
  return true;
})()`);

const info = await evalJs(`(() => ({
  height: document.body.scrollHeight,
  sections: Array.from(document.querySelectorAll('section, footer')).map((el, i) => {
    const r = el.getBoundingClientRect();
    return {
      i,
      name: el.id || (el.className || el.tagName.toLowerCase()).toString().split(' ')[0],
      top: Math.round(r.top + window.scrollY),
      h: Math.round(r.height),
    };
  }),
}))()`);

console.log('  page height:', info.height);
console.log('  sections:');
for (const s of info.sections) {
  console.log(`    ${String(s.i).padStart(2)}  ${s.name.slice(0, 22).padEnd(24)} y=${String(s.top).padStart(5)}  h=${s.h}`);
}

const H = 900;
let n = 0;
for (let y = 0; y < info.height; y += H) {
  await evalJs(`window.scrollTo({ top: ${y}, behavior: 'instant' })`);
  await new Promise((r) => setTimeout(r, 420));

  const { data } = await send('Page.captureScreenshot', { format: 'png' }, sessionId);
  const name = join(OUT, `slice-${String(n).padStart(2, '0')}.png`);
  writeFileSync(name, Buffer.from(data, 'base64'));
  n++;
}

console.log(`  captured ${n} slices to ${OUT}`);

sock.close();
chrome.kill();
srv.close();
process.exit(0);
