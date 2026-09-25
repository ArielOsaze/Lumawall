// shoot-size.mjs — captures the page at a given viewport size.
//
// The crop percentage only says how much of the source survives, which is fixed
// by the aspect ratio. Whether the SUBJECT survives is a question about pixels,
// so the answer is a screenshot.
//
// Run:  node tools/shoot-size.mjs <width> <height> <outfile> [selector]

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, mkdtempSync, writeFileSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5194;

const W = parseInt(process.argv[2] || '390', 10);
const H = parseInt(process.argv[3] || '844', 10);
const OUT = resolve(here, process.argv[4] || '../build/size.png');
const SELECTOR = process.argv[5] || 'section#top';

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.webp': 'image/webp', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
  '.mp4': 'video/mp4', '.woff2': 'font/woff2', '.json': 'application/json',
};

const srv = createServer(async (req, res) => {
  try {
    let rel = decodeURIComponent(req.url.split('?')[0]);
    if (rel === '/' || rel.endsWith('/')) rel += 'index.html';
    const b = await readFile(join(SITE, rel));
    res.writeHead(200, { 'Content-Type': MIME[extname(rel)] || 'application/octet-stream' });
    res.end(b);
  } catch { res.writeHead(404).end('nf'); }
});
await new Promise((r) => srv.listen(PORT, '127.0.0.1', r));

const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);

const profile = mkdtempSync(join(tmpdir(), 'lw-sz-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9458',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', `--window-size=${W},${H}`,
  `http://127.0.0.1:${PORT}/`,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9458/json/version');
      const j = await r.json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch { /* not up */ }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error('no cdp');
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
  const i = ++id; const p = { id: i, method, params };
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

await send('Emulation.setDeviceMetricsOverride', {
  width: W, height: H, deviceScaleFactor: 1, mobile: W < 500,
}, sessionId);
await send('Page.reload', {}, sessionId);
await new Promise((r) => setTimeout(r, 3000));

const evalJs = async (expr) =>
  (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;

await evalJs('(async () => { await document.fonts.ready; return true; })()');
await evalJs(`(async () => {
  for (let y = 0; y <= document.body.scrollHeight; y += 400) {
    window.scrollTo({ top: y, behavior: 'instant' });
    await new Promise(r => setTimeout(r, 60));
  }
  await new Promise(r => setTimeout(r, 900));
  return true;
})()`);

const info = await evalJs(`(() => {
  const el = document.querySelector(${JSON.stringify(SELECTOR)});
  if (!el) return null;
  const r = el.getBoundingClientRect();
  const top = r.top + window.scrollY;
  window.scrollTo({ top: Math.max(0, top - 8), behavior: 'instant' });
  return { top: Math.round(top), height: Math.round(r.height) };
})()`);

if (!info) {
  console.log('  element not found: ' + SELECTOR);
  sock.close(); chrome.kill(); srv.close(); process.exit(1);
}

await new Promise((r) => setTimeout(r, 700));

const { data } = await send('Page.captureScreenshot', {
  format: 'png',
  clip: { x: 0, y: 0, width: W, height: Math.min(H, info.height), scale: 1 },
}, sessionId);
writeFileSync(OUT, Buffer.from(data, 'base64'));

console.log('  viewport : ' + W + 'x' + H);
console.log('  element  : ' + SELECTOR + '  h=' + info.height);
console.log('  saved    : ' + OUT);

sock.close();
chrome.kill();
srv.close();
process.exit(0);
