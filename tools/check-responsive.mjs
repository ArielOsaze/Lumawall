// check-responsive.mjs — checks the page at the sizes people actually use.
//
// A crop that looks right at 1440x900 can slice the subject at 2560x1080, and a
// layout that fits at 1440 can overflow at 375. This measures the things that
// broke before: image crops, horizontal overflow, and text that runs off its box.

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, mkdtempSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5193;

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

const profile = mkdtempSync(join(tmpdir(), 'lw-resp-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9457',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900',
  `http://127.0.0.1:${PORT}/`,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9457/json/version');
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

const evalJs = async (expr) =>
  (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;

// The sizes worth checking: a small laptop, a common desktop, an ultrawide, and a
// phone. The ultrawide is the one that exposes crop problems, because a 16:9
// image in a 21:9 band loses a lot of its height.
const SIZES = [
  { w: 1366, h: 768, name: 'laptop 1366x768' },
  { w: 1440, h: 900, name: 'desktop 1440x900' },
  { w: 2560, h: 1080, name: 'ultrawide 2560x1080' },
  { w: 390, h: 844, name: 'phone 390x844' },
];

let failures = 0;

for (const size of SIZES) {
  await send('Emulation.setDeviceMetricsOverride', {
    width: size.w, height: size.h, deviceScaleFactor: 1, mobile: size.w < 500,
  }, sessionId);
  await send('Page.reload', {}, sessionId);
  await new Promise((r) => setTimeout(r, 2500));

  const report = await evalJs(`(async () => {
    await document.fonts.ready;
    for (let y = 0; y <= document.body.scrollHeight; y += 400) {
      window.scrollTo({ top: y, behavior: 'instant' });
      await new Promise(r => setTimeout(r, 60));
    }
    window.scrollTo({ top: 0, behavior: 'instant' });
    await new Promise(r => setTimeout(r, 800));

    const hero = document.querySelector('.hero-bg img');
    let kept = null;
    if (hero && hero.naturalWidth) {
      const r = hero.getBoundingClientRect();
      const sr = hero.naturalWidth / hero.naturalHeight;
      const br = r.width / r.height;
      kept = Math.round((sr > br ? br / sr : sr / br) * 100);
    }

    // Anything wider than the viewport means the page scrolls sideways, which is
    // always a bug on a site like this.
    const overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;

    // Text that overflows its own box, which clipping hides.
    const clipped = [];
    document.querySelectorAll('h1, h2, h3, p, .btn, .perf-pair b').forEach(el => {
      if (el.scrollWidth > el.clientWidth + 2 && el.clientWidth > 0) {
        clipped.push((el.textContent || '').trim().slice(0, 30));
      }
    });

    return {
      hero_kept: kept,
      h_overflow: overflow,
      clipped,
      nav_visible: !!document.querySelector('.nav'),
      video_w: (() => {
        const v = document.getElementById('promo');
        return v ? Math.round(v.getBoundingClientRect().width) : null;
      })(),
    };
  })()`);

  const ok = report.h_overflow <= 1 && report.clipped.length === 0 &&
             (report.hero_kept === null || report.hero_kept >= 60);

  console.log('  ' + size.name.padEnd(22) +
    ' hero kept ' + String(report.hero_kept).padStart(4) + '%' +
    '  h-overflow ' + String(report.h_overflow).padStart(3) + 'px' +
    '  video ' + String(report.video_w).padStart(4) + 'px' +
    '  ' + (ok ? 'OK' : 'PROBLEM'));

  if (report.clipped.length) {
    console.log('      clipped text: ' + report.clipped.join(' | '));
  }
  if (!ok) failures++;
}

console.log('');
console.log(failures ? '  ' + failures + ' size(s) have problems' : '  every size renders cleanly');

sock.close();
chrome.kill();
srv.close();
process.exit(failures ? 1 : 0);
