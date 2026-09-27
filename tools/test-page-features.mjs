// test-page-features.mjs - do the new look and playback options actually reach the page?
//
// Why this exists:
//
// The options travel a long way: a C# struct, a JSON string, ExecuteScriptAsync, the
// page's apply(), and then a CSS filter and a transform. Every one of those steps can
// silently drop a value and leave a wallpaper that looks untouched - which is
// indistinguishable from a feature that was never implemented.
//
// So this reads the COMPUTED style back out of the live element. Not the settings the
// page was handed, and not the string it built: what Chromium resolved after applying
// them. A filter that was set but is invalid computes to 'none', and that is exactly the
// failure this catches.
//
// Usage:
//   node tools/test-page-features.mjs

import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, existsSync, rmSync, statSync, createReadStream } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { createServer } from 'node:http';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');

const argv = process.argv.slice(2);
function argValue(name, fallback) {
  const at = argv.indexOf('--' + name);
  return at >= 0 && argv[at + 1] ? argv[at + 1] : fallback;
}
const VIDEO = argValue('video', join(process.env.LOCALAPPDATA || '', 'LumaWall', 'Wallpapers', 'Prana System Error.mp4'));

// ── the page, extracted from the app ─────────────────────────────────────────
const program = readFileSync(join(root, 'LumaWall', 'Program.cs'), 'utf8');
const start = program.indexOf('private string BuildMediaHtml()');
const literalStart = program.indexOf('@"', start);
const literalEnd = program.indexOf('";', literalStart);
let html = program.slice(literalStart + 2, literalEnd).replace(/""/g, '"');

console.log('');
console.log('  do the new options reach the page?');
console.log('  ' + '-'.repeat(58));
console.log('  page       ' + html.length + ' bytes');
console.log('  video      ' + VIDEO);

if (!existsSync(VIDEO)) {
  console.error('  no video at that path - pass --video <path>');
  process.exit(2);
}

const server = createServer((req, res) => {
  const url = req.url.split('?')[0];
  if (url === '/' || url === '/page.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
    return;
  }
  if (url === '/video.mp4') {
    const size = statSync(VIDEO).size;
    const range = req.headers.range;
    if (range) {
      const m = /bytes=(\d+)-(\d*)/.exec(range);
      const from = parseInt(m[1], 10);
      const to = m[2] ? parseInt(m[2], 10) : size - 1;
      res.writeHead(206, {
        'Content-Range': `bytes ${from}-${to}/${size}`,
        'Accept-Ranges': 'bytes',
        'Content-Length': to - from + 1,
        'Content-Type': 'video/mp4',
      });
      createReadStream(VIDEO, { start: from, end: to }).pipe(res);
    } else {
      res.writeHead(200, { 'Content-Length': size, 'Accept-Ranges': 'bytes', 'Content-Type': 'video/mp4' });
      createReadStream(VIDEO).pipe(res);
    }
    return;
  }
  res.writeHead(404);
  res.end('not found');
});

await new Promise((r) => server.listen(0, '127.0.0.1', r));
const port = server.address().port;
const pageUrl = `http://127.0.0.1:${port}/page.html`;
const videoUrl = `http://127.0.0.1:${port}/video.mp4`;

const CANDIDATES = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
];
const chrome = CANDIDATES.find((c) => existsSync(c));
if (!chrome) { console.error('  no Chrome or Edge found'); process.exit(1); }

const profile = mkdtempSync(join(tmpdir(), 'lumawall-feat-'));
const child = spawn(chrome, [
  '--headless=new', '--remote-debugging-port=0', '--user-data-dir=' + profile,
  '--no-first-run', '--no-default-browser-check', '--disable-extensions',
  '--autoplay-policy=no-user-gesture-required', '--enable-accelerated-video-decode',
  '--window-size=1920,1080', 'about:blank',
], { stdio: ['ignore', 'pipe', 'pipe'] });

const wsUrl = await new Promise((res, rej) => {
  let buffer = '';
  const timer = setTimeout(() => rej(new Error('no DevTools port')), 30000);
  child.stderr.on('data', (c) => {
    buffer += c.toString();
    const m = /DevTools listening on (ws:\/\/\S+)/.exec(buffer);
    if (m) { clearTimeout(timer); res(m[1]); }
  });
  child.on('exit', (code) => { clearTimeout(timer); rej(new Error('Chromium exited ' + code)); });
});

class CDP {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.nextId = 1;
    this.pending = new Map();
    this.handlers = new Map();
    this.ready = new Promise((r) => { this.ws.onopen = r; });
    this.ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error))); else resolve(msg.result);
        return;
      }
      if (msg.method && this.handlers.has(msg.method)) for (const fn of this.handlers.get(msg.method)) fn(msg.params);
    };
  }
  send(method, params = {}, sessionId) {
    const id = this.nextId++;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    this.ws.send(JSON.stringify(payload));
    return new Promise((res, rej) => this.pending.set(id, { resolve: res, reject: rej }));
  }
  on(method, fn) {
    if (!this.handlers.has(method)) this.handlers.set(method, []);
    this.handlers.get(method).push(fn);
  }
}

const browser = new CDP(wsUrl);
await browser.ready;
const { targetId } = await browser.send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await browser.send('Target.attachToTarget', { targetId, flatten: true });
await browser.send('Page.enable', {}, sessionId);
await browser.send('Runtime.enable', {}, sessionId);
await browser.send('Page.addScriptToEvaluateOnNewDocument', {
  source: `window.__lumaMessages=[];window.chrome=window.chrome||{};window.chrome.webview={postMessage:function(m){window.__lumaMessages.push(String(m));}};`,
}, sessionId);
await browser.send('Page.navigate', { url: pageUrl }, sessionId);
await new Promise((r) => setTimeout(r, 900));

async function evaluate(expression) {
  const r = await browser.send('Runtime.evaluate', { expression, returnByValue: true }, sessionId);
  if (r.exceptionDetails) return { __error: r.exceptionDetails.text + ' ' + (r.exceptionDetails.exception?.description || '') };
  return r.result.value;
}

// Load a video so there is an element to style, then wait for it.
await evaluate(`window.luma.prepare(${JSON.stringify(videoUrl)}, false, true, 1, 24)`);
{
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    const raw = await evaluate('JSON.stringify(window.__lumaMessages||[])');
    let msgs = [];
    try { msgs = JSON.parse(raw || '[]'); } catch {}
    if (msgs.some((m) => m.startsWith('media-ready'))) break;
    await new Promise((r) => setTimeout(r, 300));
  }
}

// What did the element actually resolve to?
async function computed() {
  const raw = await evaluate(`(function(){
    var v=document.querySelector('video');
    if(!v) return '{}';
    var cs=getComputedStyle(v);
    return JSON.stringify({
      filter: cs.filter,
      transform: cs.transform,
      objectFit: cs.objectFit,
      objectPosition: cs.objectPosition,
      width: Math.round(v.getBoundingClientRect().width),
      height: Math.round(v.getBoundingClientRect().height),
      left: Math.round(v.getBoundingClientRect().left),
      top: Math.round(v.getBoundingClientRect().top),
      rate: v.playbackRate,
      loop: v.loop,
    });
  })()`);
  try { return JSON.parse(raw || '{}'); } catch { return {}; }
}

// A settings object shaped exactly like the one the host sends.
function options(overrides) {
  return Object.assign({
    brightness: 1, contrast: 1, saturation: 1, hue: 0, gamma: 1, filter: 'none',
    flipHorizontal: false, flipVertical: false,
    hdrToneMap: false, hdrExposure: 0, hdrHighlight: 0.7,
    fit: 'cover', zoom: 1, offsetX: 0, offsetY: 0,
    playbackRate: 1, pingPong: false,
  }, overrides || {});
}

const results = [];
function check(name, condition, detail) {
  results.push({ name, ok: !!condition, detail });
  console.log('    ' + (condition ? 'PASS' : 'FAIL') + '  ' + name + (detail ? '   ' + detail : ''));
}

// ── 1. neutral settings change nothing ───────────────────────────────────────
console.log('');
console.log('  neutral settings are the identity');
await evaluate(`window.luma.apply(${JSON.stringify(options())})`);
await new Promise((r) => setTimeout(r, 200));
let c = await computed();
check('no filter', c.filter === 'none', 'filter=' + c.filter);
check('no transform', c.transform === 'none' || c.transform === 'matrix(1, 0, 0, 1, 0, 0)', 'transform=' + c.transform);
check('cover fit', c.objectFit === 'cover', 'objectFit=' + c.objectFit);
check('rate 1', Math.abs(c.rate - 1) < 0.001, 'rate=' + c.rate);
check('loops', c.loop === true, 'loop=' + c.loop);

// ── 2. brightness and contrast reach the compositor ──────────────────────────
console.log('');
console.log('  colour controls');
await evaluate(`window.luma.apply(${JSON.stringify(options({ brightness: 1.4, contrast: 0.8, saturation: 1.5, hue: 45 }))})`);
await new Promise((r) => setTimeout(r, 200));
c = await computed();
check('brightness applied', /brightness\(1\.4/.test(c.filter), c.filter);
check('contrast applied', /contrast\(0\.8/.test(c.filter), '');
check('saturation applied', /saturate\(1\.5/.test(c.filter), '');
check('hue applied', /hue-rotate\(45/.test(c.filter), '');
check('filter is valid', c.filter !== 'none' && !/invalid/i.test(c.filter), '');

// ── 3. a named filter is added, and combines with the sliders ────────────────
console.log('');
console.log('  named filters');
for (const [name, marker] of [['grayscale', 'grayscale(1)'], ['sepia', 'sepia('], ['noir', 'grayscale(1) contrast(1.35)'], ['vivid', 'saturate(1.45)']]) {
  await evaluate(`window.luma.apply(${JSON.stringify(options({ filter: name }))})`);
  await new Promise((r) => setTimeout(r, 150));
  c = await computed();
  check('filter ' + name, c.filter.includes(marker), c.filter);
}

// ── 4. flip ──────────────────────────────────────────────────────────────────
console.log('');
console.log('  flip');
await evaluate(`window.luma.apply(${JSON.stringify(options({ flipHorizontal: true }))})`);
await new Promise((r) => setTimeout(r, 200));
c = await computed();
check('horizontal flip is a negative X scale', /matrix\(-1/.test(c.transform), c.transform);

await evaluate(`window.luma.apply(${JSON.stringify(options({ flipVertical: true }))})`);
await new Promise((r) => setTimeout(r, 200));
c = await computed();
check('vertical flip is a negative Y scale', /matrix\(1, 0, 0, -1/.test(c.transform), c.transform);

await evaluate(`window.luma.apply(${JSON.stringify(options({ flipHorizontal: true, flipVertical: true }))})`);
await new Promise((r) => setTimeout(r, 200));
c = await computed();
check('both flips is a 180 turn', /matrix\(-1, 0, 0, -1/.test(c.transform), c.transform);

// ── 5. fit modes ─────────────────────────────────────────────────────────────
console.log('');
console.log('  fit modes');
for (const [fit, expected] of [['cover', 'cover'], ['contain', 'contain'], ['fill', 'fill'], ['center', 'none']]) {
  await evaluate(`window.luma.apply(${JSON.stringify(options({ fit }))})`);
  await new Promise((r) => setTimeout(r, 150));
  c = await computed();
  check('fit ' + fit, c.objectFit === expected, 'objectFit=' + c.objectFit);
}

// ── 6. zoom and pan ──────────────────────────────────────────────────────────
console.log('');
console.log('  zoom and pan');
await evaluate(`window.luma.apply(${JSON.stringify(options({ zoom: 1.5 }))})`);
await new Promise((r) => setTimeout(r, 200));
c = await computed();
check('zoom scales', /matrix\(1\.5/.test(c.transform), c.transform);

await evaluate(`window.luma.apply(${JSON.stringify(options({ offsetX: 0.5, offsetY: -0.5 }))})`);
await new Promise((r) => setTimeout(r, 200));
c = await computed();
// Chromium normalises the computed value, so 75.00% comes back as "75% 25%". Comparing
// the numbers rather than the string is what makes this check about the position instead
// of about formatting.
{
  const parts = String(c.objectPosition).trim().split(/\s+/).map((p) => parseFloat(p));
  check('pan moves object-position',
    parts.length === 2 && Math.abs(parts[0] - 75) < 0.5 && Math.abs(parts[1] - 25) < 0.5,
    c.objectPosition);
}

// ── 7. the tone curve ────────────────────────────────────────────────────────
console.log('');
console.log('  HDR tone mapping and gamma');
await evaluate(`window.luma.apply(${JSON.stringify(options({ hdrToneMap: true, hdrExposure: 0.5 }))})`);
await new Promise((r) => setTimeout(r, 250));
c = await computed();
check('tone map adds the SVG filter', c.filter.includes('url("#lumaTone")') || c.filter.includes('url(#lumaTone)'), c.filter);

// The table must have actually changed - a filter reference with the identity table is a
// no-op that looks identical in the computed style.
const table = await evaluate(`(function(){var n=document.getElementById('toneR');return n?n.getAttribute('tableValues'):'missing';})()`);
const tableValues = String(table).trim().split(/\s+/).map(Number);
const isIdentity = tableValues.length > 1 && tableValues.every((v, i) => Math.abs(v - i / (tableValues.length - 1)) < 0.002);
check('the tone table is not the identity', !isIdentity, 'first=' + tableValues.slice(0, 4).join(',') + '...');
check('the tone table is monotonic', tableValues.every((v, i) => i === 0 || v >= tableValues[i - 1]), '');

await evaluate(`window.luma.apply(${JSON.stringify(options({ gamma: 1.8 }))})`);
await new Promise((r) => setTimeout(r, 250));
const gammaTable = await evaluate(`(function(){var n=document.getElementById('toneR');return n?n.getAttribute('tableValues'):'missing';})()`);
check('gamma alone rebuilds the table', String(gammaTable) !== String(table), '');

// ── 8. playback rate and ping-pong ───────────────────────────────────────────
console.log('');
console.log('  playback rate and ping-pong');
await evaluate(`window.luma.apply(${JSON.stringify(options({ playbackRate: 2.5 }))})`);
await new Promise((r) => setTimeout(r, 200));
c = await computed();
check('rate reaches the element', Math.abs(c.rate - 2.5) < 0.01, 'rate=' + c.rate);

await evaluate(`window.luma.apply(${JSON.stringify(options({ playbackRate: 0.5 }))})`);
await new Promise((r) => setTimeout(r, 200));
c = await computed();
check('a slow rate reaches the element', Math.abs(c.rate - 0.5) < 0.01, 'rate=' + c.rate);

await evaluate(`window.luma.apply(${JSON.stringify(options({ pingPong: true }))})`);
await new Promise((r) => setTimeout(r, 200));
c = await computed();
check('ping-pong turns looping off', c.loop === false, 'loop=' + c.loop);

await evaluate(`window.luma.apply(${JSON.stringify(options({ pingPong: false }))})`);
await new Promise((r) => setTimeout(r, 200));
c = await computed();
check('turning ping-pong off restores looping', c.loop === true, 'loop=' + c.loop);

// ── 9. the span geometry ─────────────────────────────────────────────────────
console.log('');
console.log('  one wallpaper across two monitors');
//
// Two 1920x1080 monitors side by side: the picture is 3840x1080, and the LEFT monitor
// must show the left half. The element is therefore 3840 wide and shifted 0; the right
// monitor shifts it by -1920. Getting the sign wrong is the classic bug here - it makes
// the two halves swap, which looks plausible until you look at it.
await evaluate(`window.luma.apply(${JSON.stringify(options({ span: { totalW: 3840, totalH: 1080, x: 0, y: 0 } }))})`);
await new Promise((r) => setTimeout(r, 250));
c = await computed();
check('left slice is the full width of the union', c.width === 3840, 'width=' + c.width);
check('left slice starts at 0', c.left === 0, 'left=' + c.left);
check('left slice is not zoomed by the transform', !/matrix\(1\.5/.test(c.transform), c.transform);
check('span uses fill, not cover', c.objectFit === 'fill', 'objectFit=' + c.objectFit);

await evaluate(`window.luma.apply(${JSON.stringify(options({ span: { totalW: 3840, totalH: 1080, x: 1920, y: 0 } }))})`);
await new Promise((r) => setTimeout(r, 250));
c = await computed();
check('right slice is shifted left by one screen', c.left === -1920, 'left=' + c.left);
check('right slice still spans the union', c.width === 3840, 'width=' + c.width);

// Zoom inside a span scales the union, so each monitor shows a magnified slice.
await evaluate(`window.luma.apply(${JSON.stringify(options({ zoom: 2, span: { totalW: 3840, totalH: 1080, x: 1920, y: 0 } }))})`);
await new Promise((r) => setTimeout(r, 250));
c = await computed();
check('zoom inside a span doubles the union', c.width === 7680, 'width=' + c.width);
check('zoom inside a span recentres', c.left === -1920 - 1920, 'left=' + c.left);

// ── 10. the filter survives a wallpaper change ───────────────────────────────
console.log('');
console.log('  a new wallpaper keeps the settings');
await evaluate(`window.luma.apply(${JSON.stringify(options({ brightness: 1.3, flipHorizontal: true, playbackRate: 1.5 }))})`);
await new Promise((r) => setTimeout(r, 200));
await evaluate(`window.luma.prepare(${JSON.stringify(videoUrl)}, false, true, 99, 24)`);
{
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    const raw = await evaluate('JSON.stringify(window.__lumaMessages||[])');
    let msgs = [];
    try { msgs = JSON.parse(raw || '[]'); } catch {}
    if (msgs.some((m) => m === 'media-ready:99')) break;
    await new Promise((r) => setTimeout(r, 300));
  }
}
c = await computed();
check('filter survives the swap', /brightness\(1\.3/.test(c.filter), c.filter);
check('flip survives the swap', /matrix\(-1/.test(c.transform), c.transform);
check('rate survives the swap', Math.abs(c.rate - 1.5) < 0.01, 'rate=' + c.rate);

// ── verdict ──────────────────────────────────────────────────────────────────
console.log('');
console.log('  ' + '-'.repeat(58));
const failed = results.filter((r) => !r.ok);
for (const r of results) console.log('  ' + (r.ok ? 'PASS' : 'FAIL') + '  ' + r.name);
console.log('');
if (failed.length === 0) {
  console.log('  all ' + results.length + ' feature checks passed');
} else {
  console.log('  ' + failed.length + ' of ' + results.length + ' checks failed:');
  for (const r of failed) console.log('    · ' + r.name + '   ' + (r.detail || ''));
}

try { child.kill(); } catch {}
try { rmSync(profile, { recursive: true, force: true }); } catch {}
server.close();
process.exit(failed.length === 0 ? 0 : 1);
