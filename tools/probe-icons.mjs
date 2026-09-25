// probe-icons.mjs — what is actually being served and rendered?
//
// Distinguishes three possibilities for "the cards have no icons":
//   a) the server is serving a different file than the one on disk
//   b) the markup is there but the DOM query is wrong
//   c) the icons render but are invisible
//
// Fetches the raw HTML over HTTP as well as querying the DOM, so a mismatch
// between the two is visible.

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, mkdtempSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5184;

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

// ── (a) what does the server actually send? ────────────────────────────────
const served = await (await fetch(`http://127.0.0.1:${PORT}/`)).text();
const disk = await readFile(join(SITE, 'index.html'), 'utf8');
console.log('  served html  : ' + served.length + ' bytes');
console.log('  disk html    : ' + disk.length + ' bytes');
console.log('  identical    : ' + (served === disk));
console.log('  "card-ico" in served : ' + (served.match(/card-ico/g) || []).length);
console.log('  "card-ico" in disk   : ' + (disk.match(/card-ico/g) || []).length);
console.log('');

const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);

const profile = mkdtempSync(join(tmpdir(), 'lw-probe-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9450',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900',
  `http://127.0.0.1:${PORT}/`,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9450/json/version');
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
await send('Runtime.enable', {}, sessionId);
await new Promise((r) => setTimeout(r, 2600));

const evalJs = async (expr) => {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId);
  if (r.exceptionDetails) return { __error: r.exceptionDetails.text + ' ' + (r.exceptionDetails.exception || {}).description };
  return r.result.value;
};

// ── (b) what is in the DOM? ────────────────────────────────────────────────
const dom = await evalJs(`(() => ({
  url: location.href,
  title: document.title,
  card_ico: document.querySelectorAll('.card-ico').length,
  cards: document.querySelectorAll('.card').length,
  articles: document.querySelectorAll('article').length,
  svg_total: document.querySelectorAll('svg').length,
  h3_total: document.querySelectorAll('h3').length,
  first_h3: (document.querySelector('h3') || {}).textContent || null,
}))()`);
console.log('  DOM:');
for (const [k, v] of Object.entries(dom)) console.log('    ' + k + ': ' + v);

// ── (c) if they exist, are they visible? ───────────────────────────────────
if (dom.card_ico > 0) {
  const vis = await evalJs(`(() => {
    const out = [];
    document.querySelectorAll('.card-ico').forEach((el, i) => {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      const svg = el.querySelector('svg');
      const ss = svg ? getComputedStyle(svg) : null;
      out.push({
        i,
        w: Math.round(r.width), h: Math.round(r.height),
        top: Math.round(r.top + scrollY),
        bg: cs.backgroundColor,
        color: cs.color,
        opacity: cs.opacity,
        display: cs.display,
        svg_w: svg ? Math.round(svg.getBoundingClientRect().width) : null,
        stroke: ss ? ss.stroke : null,
      });
    });
    return out;
  })()`);
  console.log('');
  console.log('  icons:');
  for (const v of vis) {
    console.log(`    #${v.i} ${v.w}x${v.h} at y=${v.top}  bg=${v.bg}  color=${v.color}  opacity=${v.opacity}  ${v.display}  svg=${v.svg_w}px  stroke=${v.stroke}`);
  }
}

sock.close();
chrome.kill();
srv.close();
process.exit(0);
