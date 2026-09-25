// verify-live-behaviour.mjs — checks the deployed site, not the local copy.
//
// Everything else in tools/ runs against site/ on disk. That is not the same
// thing as the site a visitor loads: the deploy can serve a stale asset, the CDN
// can hold a cached one, and the video can be a fragment that still returns 200.
// This runs the page checks against the real domain.

import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

const URL_TO_CHECK = process.argv[2] || 'https://lumawall.xinet.id/';

const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);

const profile = mkdtempSync(join(tmpdir(), 'lw-live-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9459',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900',
  '--autoplay-policy=no-user-gesture-required',
  URL_TO_CHECK,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9459/json/version');
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
const consoleErrors = [];

sock.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const { res, rej } = pending.get(m.id);
    pending.delete(m.id);
    m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
    return;
  }
  if (m.method === 'Runtime.exceptionThrown') {
    const d = m.params.exceptionDetails;
    consoleErrors.push((d.exception && d.exception.description) || d.text);
  }
  if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') {
    consoleErrors.push(m.params.entry.text);
  }
};

const send = (method, params = {}, sessionId) => {
  const i = ++id; const p = { id: i, method, params };
  if (sessionId) p.sessionId = sessionId;
  return new Promise((res, rej) => { pending.set(i, { res, rej }); sock.send(JSON.stringify(p)); });
};

// Wait for the real page, not about:blank.
let target = null;
for (let i = 0; i < 90 && !target; i++) {
  const { targetInfos } = await send('Target.getTargets');
  target = targetInfos.find((t) => t.type === 'page' && t.url.startsWith('http'));
  if (!target) await new Promise((r) => setTimeout(r, 400));
}
const { sessionId } = await send('Target.attachToTarget', { targetId: target.targetId, flatten: true });
await send('Page.enable', {}, sessionId);
await send('Runtime.enable', {}, sessionId);
await send('Log.enable', {}, sessionId);

for (let i = 0; i < 50; i++) {
  const r = await send('Runtime.evaluate', {
    expression: 'document.readyState === "complete" && document.querySelectorAll("section").length > 0',
    returnByValue: true,
  }, sessionId);
  if (r.result.value) break;
  await new Promise((r) => setTimeout(r, 300));
}
await new Promise((r) => setTimeout(r, 1500));

const evalJs = async (expr) =>
  (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;

let failures = 0;
const check = (name, ok, detail) => {
  console.log('    ' + (ok ? 'PASS' : 'FAIL') + '  ' + name + (detail ? '  (' + detail + ')' : ''));
  if (!ok) failures++;
};

console.log('  ' + URL_TO_CHECK);

const state = await evalJs(`(async () => {
  const v = document.getElementById('promo');
  if (v) {
    v.scrollIntoView({ block: 'center' });
    await new Promise(r => setTimeout(r, 4000));
  }
  const hero = document.querySelector('.hero-bg img');
  return {
    title: document.title,
    sections: document.querySelectorAll('section').length,
    font: getComputedStyle(document.body).fontFamily,
    video_exists: !!v,
    video_paused: v ? v.paused : null,
    video_time: v ? Math.round(v.currentTime * 100) / 100 : null,
    video_src: v ? (v.currentSrc || v.src) : null,
    video_error: v && v.error ? v.error.code : null,
    hero_src: hero ? hero.getAttribute('src') : null,
    hero_visible: hero ? parseFloat(getComputedStyle(hero).opacity) > 0.3 : false,
    badge: !!document.querySelector('.video-badge'),
    cover: !!document.querySelector('.video-cover'),
  };
})()`);

console.log('');
console.log('  checks:');
check('the page loaded', state.sections > 0, state.sections + ' sections');
check('the font is Plus Jakarta Sans', /Plus Jakarta Sans/.test(state.font));
check('the video is present', state.video_exists);
check('the video plays on arrival', state.video_exists && state.video_paused === false,
  't=' + state.video_time);
check('the video advanced', state.video_exists && state.video_time > 0.3, 't=' + state.video_time);
check('the video has no media error', state.video_exists && !state.video_error);
check('the video URL is the promo', /lumawall-promo\.mp4/.test(state.video_src || ''));
check('the hero image is the composed one', /hero-bg/.test(state.hero_src || ''), state.hero_src);
check('the hero image is visible', state.hero_visible);
check('no 1080p badge over the video', !state.badge);
check('no play cover over the video', !state.cover);

// The video has to be a real file, not a fragment that returns 200.
const videoSize = await evalJs(`(async () => {
  const v = document.getElementById('promo');
  if (!v) return null;
  const src = v.currentSrc || v.src;
  const r = await fetch(src, { method: 'HEAD' });
  return parseInt(r.headers.get('content-length') || '0', 10);
})()`);
check('the deployed video is a whole file', videoSize > 5_000_000,
  (videoSize / 1048576).toFixed(1) + ' MB');

console.log('');
if (consoleErrors.length) {
  console.log('  console errors on the live site:');
  for (const e of consoleErrors.slice(0, 6)) console.log('    ' + String(e).slice(0, 140));
  failures++;
} else {
  console.log('  no console errors');
}

console.log('');
if (failures) {
  console.log('  ' + failures + ' check(s) failed');
  sock.close(); chrome.kill();
  process.exit(1);
}
console.log('  the live site behaves correctly');

sock.close();
chrome.kill();
process.exit(0);
