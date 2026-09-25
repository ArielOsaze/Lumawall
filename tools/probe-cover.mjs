// probe-cover.mjs — why is the video cover not visible?
//
// Reports the cover's computed style, the video's playback state and any media
// error, so the cause is measured rather than guessed.

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, mkdtempSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5188;

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
    const b = await readFile(f);
    res.writeHead(200, { 'Content-Type': MIME[extname(f)] || 'application/octet-stream' });
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

const profile = mkdtempSync(join(tmpdir(), 'lw-cov-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9453',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900',
  `http://127.0.0.1:${PORT}/`,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9453/json/version');
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
await new Promise((r) => setTimeout(r, 2500));

const ev = async (expr) =>
  (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;

// Scroll to the video and give the observer time to fire.
await ev(`(async () => {
  for (let y = 0; y <= document.body.scrollHeight; y += 300) {
    window.scrollTo({ top: y, behavior: 'instant' });
    await new Promise(r => setTimeout(r, 90));
  }
  const v = document.getElementById('promo');
  if (v) v.scrollIntoView({ block: 'center' });
  await new Promise(r => setTimeout(r, 2500));
  return 1;
})()`);

const state = await ev(`(() => {
  const c = document.querySelector('.video-cover');
  const v = document.getElementById('promo');
  return {
    cover_exists: !!c,
    cover_class: c ? c.className : null,
    cover_opacity: c ? getComputedStyle(c).opacity : null,
    cover_visibility: c ? getComputedStyle(c).visibility : null,
    cover_display: c ? getComputedStyle(c).display : null,
    cover_z: c ? getComputedStyle(c).zIndex : null,
    video_paused: v ? v.paused : null,
    video_time: v ? Math.round(v.currentTime * 100) / 100 : null,
    video_ready: v ? v.readyState : null,
    video_error: v && v.error ? v.error.code + ' ' + v.error.message : null,
    video_autoplay_attr: v ? v.hasAttribute('autoplay') : null,
  };
})()`);

console.log('  cover / video state after scrolling to it:');
for (const [k, val] of Object.entries(state)) console.log('    ' + k.padEnd(20) + ': ' + val);

sock.close();
chrome.kill();
srv.close();
process.exit(0);
