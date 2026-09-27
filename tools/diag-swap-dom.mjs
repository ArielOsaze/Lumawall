// Report what the wallpaper page's stage actually contains during a swap, in an occluded
// window. A pixel probe cannot tell "the wallpaper is black" apart from "the probe cannot
// see the video", and those need different fixes - so this records the DOM instead.

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { resolve, dirname, extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');

function pageFromApp() {
  const program = readFileSync(join(root, 'LumaWall', 'Program.cs'), 'utf8');
  const start = program.indexOf('private string BuildMediaHtml()');
  const literalStart = program.indexOf('@"', start);
  const literalEnd = program.indexOf('";', literalStart);
  return program.slice(literalStart + 2, literalEnd).replace(/""/g, '"');
}

function mp4s(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter((f) => f.toLowerCase().endsWith('.mp4')).map((f) => join(dir, f));
}

const user = mp4s(join(process.env.LOCALAPPDATA || '', 'LumaWall', 'Wallpapers'));
const clips = user.length >= 2 ? [user[0], user[1]] : mp4s(join(root, 'LumaWall', 'assets')).slice(0, 2);
if (clips.length < 2) { console.log('  need two clips'); process.exit(1); }

const server = createServer((req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  if (url.pathname === '/') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(pageFromApp());
    return;
  }
  const file = url.pathname === '/a' ? clips[0] : url.pathname === '/b' ? clips[1] : null;
  if (!file) { res.writeHead(404); res.end(); return; }
  const size = statSync(file).size;
  const range = req.headers.range;
  const type = 'video/mp4';
  if (range) {
    const m = /bytes=(\d*)-(\d*)/.exec(range);
    const start = m[1] ? Number(m[1]) : 0;
    const end = m[2] ? Number(m[2]) : size - 1;
    res.writeHead(206, { 'Content-Type': type, 'Content-Range': `bytes ${start}-${end}/${size}`, 'Content-Length': end - start + 1 });
    res.end(readFileSync(file).subarray(start, end + 1));
    return;
  }
  res.writeHead(200, { 'Content-Type': type, 'Content-Length': size, 'Accept-Ranges': 'bytes' });
  res.end(readFileSync(file));
});

await new Promise((d) => server.listen(0, '127.0.0.1', d));
const port = server.address().port;

const chrome = spawn('C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', '--remote-debugging-port=0',
  '--user-data-dir=' + join(root, 'build', 'diag-profile'),
  '--no-first-run', '--autoplay-policy=no-user-gesture-required',
  '--window-size=1280,720', 'about:blank',
], { stdio: ['ignore', 'pipe', 'pipe'] });

let stderr = '';
chrome.stderr.on('data', (c) => { stderr += c.toString(); });
const wsUrl = await new Promise((done, fail) => {
  const t = setTimeout(() => fail(new Error('no port')), 20000);
  const check = () => { const m = /ws:\/\/[^\s]+/.exec(stderr); if (m) { clearTimeout(t); done(m[0]); } };
  chrome.stderr.on('data', check); check();
});

const socket = new WebSocket(wsUrl);
await new Promise((d, f) => { socket.addEventListener('open', d); socket.addEventListener('error', f); });
let nextId = 1; const pending = new Map();
socket.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const { done, fail } = pending.get(m.id); pending.delete(m.id);
    if (m.error) fail(new Error(m.error.message)); else done(m.result);
  }
});
function send(method, params = {}, sessionId) {
  const id = nextId++;
  return new Promise((done, fail) => { pending.set(id, { done, fail }); socket.send(JSON.stringify({ id, method, params, sessionId })); });
}

const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
await send('Page.enable', {}, sessionId);
await send('Runtime.enable', {}, sessionId);
await send('Page.navigate', { url: `http://127.0.0.1:${port}/` }, sessionId);
await new Promise((d) => setTimeout(d, 1200));

async function ev(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }, sessionId);
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text);
  return r.result.value;
}

// Reproduce the occluded case.
await ev(`HTMLVideoElement.prototype.requestVideoFrameCallback = function(){ return 0; };`);

// Watch the DOM across a swap.
await ev(`(() => {
  const stage = document.getElementById('stage');
  window.__log = [];
  window.__watching = true;
  function tick() {
    if (!window.__watching) return;
    const els = [];
    for (const el of stage.querySelectorAll('video, img')) {
      els.push({
        tag: el.tagName,
        opacity: getComputedStyle(el).opacity,
        inlineOpacity: el.style.opacity,
        transition: getComputedStyle(el).transitionDuration,
        z: getComputedStyle(el).zIndex,
        readyState: el.tagName === 'VIDEO' ? el.readyState : null,
        videoWidth: el.tagName === 'VIDEO' ? el.videoWidth : null,
        paused: el.tagName === 'VIDEO' ? el.paused : null,
        src: (el.getAttribute('src') || '').slice(-2),
      });
    }
    window.__log.push({ at: Math.round(performance.now()), count: els.length, els });
    setTimeout(tick, 50);
  }
  tick();
})()`);

await ev(`window.luma.prepare('/a', false, true, 1)`);
await new Promise((d) => setTimeout(d, 1500));
await ev(`window.luma.prepare('/b', false, true, 2)`);
await new Promise((d) => setTimeout(d, 2500));

const log = await ev('(() => { window.__watching = false; return window.__log })()');

socket.close(); chrome.kill(); server.close();

// ── report ───────────────────────────────────────────────────────────────────

const around = log.filter((e) => e.at > 1400 && e.at < 2600);
console.log('');
console.log('  the stage during a swap in an occluded window');
console.log('  ' + '-'.repeat(72));
console.log('   at(ms)  elements  what is on the stage');
for (const entry of around) {
  const parts = entry.els.map((el) => {
    const vis = Number(el.opacity) > 0.01 ? 'VISIBLE' : 'invisible';
    return `${el.src} ${el.tag} op=${el.opacity} ${vis} rs=${el.readyState} ${el.videoWidth}px${el.paused ? ' PAUSED' : ''}`;
  });
  console.log(`  ${String(entry.at).padStart(6)}  ${String(entry.count).padStart(8)}  ${parts.join('  |  ')}`);
}

// Was there any moment with nothing visible?
const gaps = around.filter((e) => !e.els.some((el) => Number(el.opacity) > 0.01));
console.log('');
console.log(`  samples with NOTHING visible: ${gaps.length} of ${around.length}`);
if (gaps.length) {
  console.log('  the first few:');
  for (const gap of gaps.slice(0, 6)) {
    console.log(`    ${gap.at}ms: ${gap.count} element(s), all at opacity 0`);
    for (const el of gap.els) console.log(`        ${el.src} ${el.tag} inline=${el.inlineOpacity} computed=${el.opacity} rs=${el.readyState}`);
  }
}
