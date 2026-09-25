// check-icons.mjs — are the card icons actually painted?
//
// A design review said the feature cards had no icons. The markup has six of
// them, so either the review was wrong or they render invisibly. This measures
// the boxes and the computed colours rather than trusting either.

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, mkdtempSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5183;

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

const profile = mkdtempSync(join(tmpdir(), 'lw-icons-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9449',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900',
  `http://127.0.0.1:${PORT}/`,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9449/json/version');
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

const report = await evalJs(`(() => {
  const out = [];
  document.querySelectorAll('.card-ico').forEach((el, i) => {
    const r = el.getBoundingClientRect();
    const svg = el.querySelector('svg');
    const sr = svg ? svg.getBoundingClientRect() : null;
    const cs = getComputedStyle(el);
    const ss = svg ? getComputedStyle(svg) : null;
    out.push({
      i,
      box: r.width + 'x' + r.height,
      visible: r.width > 0 && r.height > 0,
      bg: cs.backgroundColor,
      color: cs.color,
      svg_box: sr ? Math.round(sr.width) + 'x' + Math.round(sr.height) : null,
      stroke: ss ? ss.stroke : null,
      stroke_width: ss ? ss.strokeWidth : null,
      opacity: cs.opacity,
    });
  });
  return out;
})()`);

console.log('  card icons:');
for (const r of report) {
  console.log(`    #${r.i}  box=${r.box.padEnd(9)} svg=${String(r.svg_box).padEnd(7)} visible=${r.visible}`);
  console.log(`         bg=${r.bg}  color=${r.color}  opacity=${r.opacity}`);
  console.log(`         stroke=${r.stroke}  stroke-width=${r.stroke_width}`);
}

// Is the icon actually distinguishable from the card behind it?
const contrast = await evalJs(`(() => {
  const el = document.querySelector('.card-ico');
  const card = el.closest('.card');
  const parse = (c) => {
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const over = (fg, bg) => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
  });
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const ratio = (a, b) => {
    const la = lum(a), lb = lum(b);
    return ((Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)).toFixed(2);
  };
  const rgb = (c) => Math.round(c.r) + ',' + Math.round(c.g) + ',' + Math.round(c.b);
  const pageBg = parse(getComputedStyle(document.body).backgroundColor) || { r: 8, g: 10, b: 12, a: 1 };
  const cardBg = parse(getComputedStyle(card).backgroundColor);
  const icoBg = parse(getComputedStyle(el).backgroundColor);
  const icoFg = parse(getComputedStyle(el).color);
  const cardEff = cardBg ? over(cardBg, pageBg) : pageBg;
  const icoEff = icoBg ? over(icoBg, cardEff) : cardEff;
  return {
    page: rgb(pageBg),
    card_bg: rgb(cardEff),
    ico_bg: rgb(icoEff),
    icon_vs_card: ratio(icoFg, icoEff),
    tile_vs_card: ratio(icoEff, cardEff),
  };
})()`);

if (!contrast) {
  console.log('  contrast: evaluation failed');
} else {
  console.log('');
  console.log('  contrast:');
  console.log('    icon stroke vs its tile : ' + contrast.icon_vs_card + ':1');
  console.log('    tile vs card background : ' + contrast.tile_vs_card + ':1');
  console.log('    page rgb                : ' + contrast.page);
  console.log('    card rgb (composited)   : ' + contrast.card_bg);
  console.log('    tile rgb (composited)   : ' + contrast.ico_bg);
}

sock.close();
chrome.kill();
srv.close();
process.exit(0);
