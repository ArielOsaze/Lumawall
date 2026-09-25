// check-crops.mjs — finds images that are cropped badly.
//
// A hero background was cropping the subject's head off because a portrait
// wallpaper was forced into a wide band. That class of mistake is invisible to a
// status check: the image loads, the page renders, and the composition is wrong.
//
// This reports, for every image on the page, how much of the source is being
// thrown away by object-fit and where the visible window sits.

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, mkdtempSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5191;

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

const profile = mkdtempSync(join(tmpdir(), 'lw-crop-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9455',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900',
  `http://127.0.0.1:${PORT}/`,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9455/json/version');
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
await new Promise((r) => setTimeout(r, 3000));

const evalJs = async (expr) =>
  (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;

const report = await evalJs(`(() => {
  const out = [];
  const imgs = Array.from(document.images);

  for (const im of imgs) {
    const r = im.getBoundingClientRect();
    const cs = getComputedStyle(im);
    const nw = im.naturalWidth || 0;
    const nh = im.naturalHeight || 0;
    if (!nw || !nh || !r.width || !r.height) {
      out.push({ src: im.getAttribute('src'), skipped: 'no natural size or zero box' });
      continue;
    }

    const srcRatio = nw / nh;
    const boxRatio = r.width / r.height;
    const fit = cs.objectFit;

    // How much of the source survives the crop.
    let kept = 1;
    if (fit === 'cover') {
      kept = srcRatio > boxRatio
        ? boxRatio / srcRatio   // cropped horizontally
        : srcRatio / boxRatio;  // cropped vertically
    }

    out.push({
      src: im.getAttribute('src'),
      src_size: nw + 'x' + nh,
      box: Math.round(r.width) + 'x' + Math.round(r.height),
      fit,
      position: cs.objectPosition,
      kept: Math.round(kept * 100) + '%',
      class: (im.className || '').toString().slice(0, 24),
    });
  }
  return out;
})()`);

if (!Array.isArray(report)) {
  console.log('  evaluation returned:', JSON.stringify(report).slice(0, 200));
  sock.close(); chrome.kill(); srv.close(); process.exit(1);
}
if (!report.length) {
  const n = await evalJs('document.images.length');
  console.log('  no images reported; document.images.length =', n);
}

console.log('  image                                   source        box        fit      kept   position');
for (const r of report) {
  if (r.skipped) {
    console.log('  ' + String(r.src).padEnd(38) + ' ' + r.skipped);
    continue;
  }
  const name = String(r.src).replace('assets/', '').slice(0, 38);
  const flag = r.fit === 'cover' && parseInt(r.kept) < 70 ? '  <-- heavy crop' : '';
  console.log(
    '  ' + name.padEnd(38) + ' ' + r.src_size.padEnd(12) + ' ' + r.box.padEnd(10) + ' ' +
    r.fit.padEnd(8) + ' ' + r.kept.padEnd(6) + ' ' + r.position + flag
  );
}

sock.close();
chrome.kill();
srv.close();
process.exit(0);
