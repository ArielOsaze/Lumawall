// measure-gaps.mjs — finds vertical dead space on the page.
//
// A design review flagged a large empty band between the features and the
// performance section. This measures where the space actually is, instead of
// guessing from the section heights.

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, mkdtempSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5182;

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
  } catch { res.writeHead(404).end('not found'); }
});
await new Promise((r) => srv.listen(PORT, '127.0.0.1', r));

const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);

const profile = mkdtempSync(join(tmpdir(), 'lw-gap-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9448',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900',
  `http://127.0.0.1:${PORT}/`,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9448/json/version');
      const j = await r.json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch { /* not up */ }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error('no devtools');
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
await new Promise((r) => setTimeout(r, 2600));

const evalJs = async (expr) =>
  (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;

// Walk down the page in 50px bands and record which bands contain no painted
// content, so dead space is measured rather than inferred.
const report = await evalJs(`(() => {
  const secs = Array.from(document.querySelectorAll('section, footer'));
  const out = [];
  for (const el of secs) {
    const r = el.getBoundingClientRect();
    const top = Math.round(r.top + window.scrollY);
    const name = el.id || (el.className || el.tagName).toString().split(' ')[0];

    // The first and last painted child, ignoring the section's own padding.
    const kids = Array.from(el.children).map(k => k.getBoundingClientRect());
    const first = kids.length ? Math.round(Math.min(...kids.map(k => k.top)) + window.scrollY) : top;
    const last = kids.length ? Math.round(Math.max(...kids.map(k => k.bottom)) + window.scrollY) : top;

    out.push({
      name,
      top,
      height: Math.round(r.height),
      pad_top: first - top,
      pad_bottom: Math.round(r.bottom + window.scrollY) - last,
      content: last - first,
    });
  }
  return out;
})()`);

console.log('  section            top   height  pad-top  content  pad-bottom');
for (const s of report) {
  const flag = s.pad_bottom > 180 ? '  <-- large bottom padding' : '';
  console.log(
    `  ${s.name.slice(0, 18).padEnd(18)} ${String(s.top).padStart(5)} ${String(s.height).padStart(7)} ${String(s.pad_top).padStart(8)} ${String(s.content).padStart(8)} ${String(s.pad_bottom).padStart(11)}${flag}`
  );
}

sock.close();
chrome.kill();
srv.close();
process.exit(0);
