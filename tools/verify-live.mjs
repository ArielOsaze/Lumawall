// verify-live.mjs — loads the deployed site in a real browser and checks the
// things a file check cannot: that the animations run, the video plays, and the
// layout holds at a real viewport size.
//
// Why this matters: the site can return 200 for every asset and still be broken
// for a visitor. The headline reveal sets its characters to opacity 0 before
// animating them in, so a JavaScript failure leaves the hero invisible while every
// HTTP check stays green.
//
// Run:  node tools/verify-live.mjs [url]

import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const URL_ = process.argv[2] || 'https://lumawall.xinet.id/';

const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);

if (!CHROME) { console.error('no browser'); process.exit(1); }

console.log('  url:', URL_);
console.log('');

const profile = mkdtempSync(join(tmpdir(), 'lw-live-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9455',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--disable-extensions', '--hide-scrollbars', '--window-size=1440,900',
  '--autoplay-policy=no-user-gesture-required',
  URL_,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 120; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9455/json/version');
      const j = await r.json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch { /* not up */ }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error('devtools never came up');
}

const sock = new WebSocket(await wsUrl());
await new Promise((res, rej) => { sock.onopen = res; sock.onerror = rej; });

let id = 0;
const pending = new Map();
const netFailures = [];
sock.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const { res, rej } = pending.get(m.id);
    pending.delete(m.id);
    m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
  } else if (m.method === 'Network.loadingFailed') {
    netFailures.push(m.params.errorText + ' ' + (m.params.requestId || ''));
  }
};
const send = (method, params = {}, sessionId) => {
  const i = ++id;
  const p = { id: i, method, params };
  if (sessionId) p.sessionId = sessionId;
  return new Promise((res, rej) => { pending.set(i, { res, rej }); sock.send(JSON.stringify(p)); });
};

let target = null;
for (let i = 0; i < 80 && !target; i++) {
  const { targetInfos } = await send('Target.getTargets');
  target = targetInfos.find((t) => t.type === 'page' && t.url.startsWith('http'));
  if (!target) await new Promise((r) => setTimeout(r, 500));
}
const { sessionId } = await send('Target.attachToTarget', { targetId: target.targetId, flatten: true });
await send('Page.enable', {}, sessionId);
await send('Runtime.enable', {}, sessionId);
await send('Network.enable', {}, sessionId);

await send('Emulation.setEmulatedMedia', {
  features: [{ name: 'prefers-reduced-motion', value: 'no-preference' }],
}, sessionId);
await send('Page.reload', {}, sessionId);
await new Promise((r) => setTimeout(r, 4000));

const evalJs = async (expr) =>
  (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;

const hero = await evalJs(`(() => {
  const h1 = document.querySelector('h1');
  const ch = h1 && h1.querySelector('.ch');
  return {
    title: document.title,
    h1_chars: h1 ? h1.querySelectorAll('.ch').length : 0,
    first_char_opacity: ch ? getComputedStyle(ch).opacity : 'no-char',
    grad_chars: document.querySelectorAll('.ch-grad').length,
  };
})()`);

console.log('  title        :', hero.title);
console.log('  h1 chars     :', hero.h1_chars);
console.log('  first char   : opacity', hero.first_char_opacity);
console.log('  grad chars   :', hero.grad_chars);
console.log('');

// Scroll the whole page.
await evalJs(`(async () => {
  for (let y = 0; y <= document.body.scrollHeight; y += 400) {
    window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60));
  }
  window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 1200));
  return true;
})()`);

// The video: play it and confirm frames advance.
const video = await evalJs(`(async () => {
  const v = document.getElementById('promo');
  if (!v) return { found: false };
  v.muted = true;
  try { await v.play(); } catch (e) { return { found: true, play_error: String(e) }; }
  const t0 = v.currentTime;
  await new Promise(r => setTimeout(r, 2200));
  return {
    found: true,
    duration: Math.round(v.duration * 10) / 10,
    width: v.videoWidth, height: v.videoHeight,
    advanced: Math.round((v.currentTime - t0) * 100) / 100,
    readyState: v.readyState,
    error: v.error ? v.error.message : null,
  };
})()`);

console.log('  video');
if (video.found) {
  console.log('    size      :', video.width + 'x' + video.height);
  console.log('    duration  :', video.duration + 's');
  console.log('    advanced  :', video.advanced + 's in 2.2s');
  console.log('    readyState:', video.readyState);
  if (video.play_error) console.log('    play error:', video.play_error);
  if (video.error) console.log('    media err :', video.error);
} else {
  console.log('    NOT FOUND');
}
console.log('');

const after = await evalJs(`(() => {
  const hidden = [];
  document.querySelectorAll('.reveal').forEach(el => {
    if (parseFloat(getComputedStyle(el).opacity) < 0.05)
      hidden.push((el.className||'').toString().slice(0,36));
  });
  return {
    reveal: document.querySelectorAll('.reveal').length,
    revealed: document.querySelectorAll('.reveal.in').length,
    hidden,
    counters: document.querySelectorAll('[data-count]').length,
    counted: document.querySelectorAll('[data-count][data-counted="done"]').length,
    hero_stats: Array.from(document.querySelectorAll('.hero-stats b')).map(b => b.textContent.trim()),
    downloads: Array.from(document.querySelectorAll('a[download]')).map(a => a.getAttribute('href')),
  };
})()`);

console.log('  page state');
console.log('    revealed  :', after.revealed + '/' + after.reveal);
console.log('    counters  :', after.counted + '/' + after.counters);
console.log('    hero stats:', after.hero_stats.join('  |  '));
console.log('    downloads :', after.downloads.length);
if (after.hidden.length) console.log('    STILL HIDDEN:', after.hidden.join(', '));
console.log('');

const shot = await send('Page.captureScreenshot', { format: 'png' }, sessionId);
const outShot = resolve(here, '..', 'build', 'live-hero.png');
writeFileSync(outShot, Buffer.from(shot.data, 'base64'));
console.log('  screenshot:', outShot);

// Full-page shot of the video section.
await evalJs(`document.getElementById('video').scrollIntoView({block:'center'}); new Promise(r=>setTimeout(r,600))`);
const shot2 = await send('Page.captureScreenshot', { format: 'png' }, sessionId);
const outShot2 = resolve(here, '..', 'build', 'live-video.png');
writeFileSync(outShot2, Buffer.from(shot2.data, 'base64'));
console.log('  screenshot:', outShot2);
console.log('');

let pass = true;
const fail = (m) => { console.log('  FAIL ' + m); pass = false; };

if (hero.h1_chars < 10) fail('headline not split');
if (parseFloat(hero.first_char_opacity) < 0.9) fail('headline character invisible');
if (!hero.grad_chars) fail('no gradient characters');
if (!video.found) fail('video element missing');
else {
  if (video.width !== 1920 || video.height !== 1080) fail('video is not 1080p');
  if (Math.abs(video.duration - 52) > 1) fail('video duration is ' + video.duration + 's, expected 52s');
  if (!(video.advanced > 1)) fail('video did not advance while playing');
}
if (after.hidden.length) fail(after.hidden.length + ' element(s) never revealed');
if (after.counted < after.counters) fail('counters did not finish');
if (!after.downloads.length) fail('no download links');

console.log(pass ? '  PASS' : '  FAILED');

sock.close();
chrome.kill();
try { rmSync(profile, { recursive: true, force: true }); } catch { /* ignore */ }
process.exit(pass ? 0 : 1);
