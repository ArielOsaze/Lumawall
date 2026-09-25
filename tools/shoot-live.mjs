// shoot-live.mjs — screenshots the LIVE site at a given viewport.
//
// The local copy and the deployed site can disagree, and when a user reports a
// layout problem the deployed one is what matters. This points the existing capture
// machinery at the public URL instead of the local files.

import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';
import { mkdtempSync, existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

const URL_ = process.argv[2] || 'https://lumawall.xinet.id/';
const W = parseInt(process.argv[3] || '1908', 10);
const H = parseInt(process.argv[4] || '844', 10);
const OUT = process.argv[5] || 'build/live-shot.png';
const SCROLL = parseInt(process.argv[6] || '0', 10);

const CHROME = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  join(process.env.LOCALAPPDATA || '', 'Google\\Chrome\\Application\\chrome.exe'),
  join(process.env.LOCALAPPDATA || '', 'Microsoft\\Edge\\Application\\msedge.exe'),
].find((p) => p && existsSync(p));

if (!CHROME) {
  console.error('  no Chrome or Edge found');
  process.exit(1);
}

const profile = mkdtempSync(join(tmpdir(), 'lw-shot-'));
const chrome = spawn(CHROME, [
  '--headless=new',
  '--remote-debugging-port=9444',
  `--user-data-dir=${profile}`,
  '--no-first-run',
  '--no-default-browser-check',
  '--disable-extensions',
  '--hide-scrollbars',
  '--force-device-scale-factor=1',
  `--window-size=${W},${H}`,
  URL_,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9444/json/version');
      const j = await r.json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch { /* not up */ }
    await sleep(400);
  }
  throw new Error('devtools endpoint never came up');
}

const ws = new WebSocket(await wsUrl());
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

let id = 0;
const pending = new Map();
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) {
    const { resolve, reject } = pending.get(m.id);
    pending.delete(m.id);
    m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result);
  }
};
const send = (method, params = {}, sessionId) => {
  const i = ++id;
  const p = { id: i, method, params };
  if (sessionId) p.sessionId = sessionId;
  return new Promise((resolve, reject) => {
    pending.set(i, { resolve, reject });
    ws.send(JSON.stringify(p));
  });
};

let target = null;
for (let i = 0; i < 60 && !target; i++) {
  const { targetInfos } = await send('Target.getTargets');
  target = targetInfos.find((t) => t.type === 'page' && !t.url.startsWith('devtools'));
  if (!target) await sleep(400);
}
const { sessionId } = await send('Target.attachToTarget', { targetId: target.targetId, flatten: true });
await send('Page.enable', {}, sessionId);
await send('Runtime.enable', {}, sessionId);
await send('Emulation.setDeviceMetricsOverride',
           { width: W, height: H, deviceScaleFactor: 1, mobile: false }, sessionId);

// Let the page settle: fonts, the hero video's first frame, the reveal animations.
await sleep(6000);

if (SCROLL > 0) {
  await send('Runtime.evaluate', {
    expression: `window.scrollTo({top:${SCROLL}, behavior:'instant'})`,
    returnByValue: true,
  }, sessionId);
  await sleep(2500);
}

const { data } = await send('Page.captureScreenshot', { format: 'png' }, sessionId);
writeFileSync(OUT, Buffer.from(data, 'base64'));
console.log(`  ${W}x${H} scroll=${SCROLL}  ->  ${OUT}`);

// Also report what the page thinks its own layout is, which is what a crop question
// actually needs: the width of the hero background versus the viewport.
const probe = await send('Runtime.evaluate', {
  expression: `(() => {
    const out = { viewport: [innerWidth, innerHeight], doc: [document.documentElement.scrollWidth, document.documentElement.scrollHeight] };
    const hero = document.querySelector('.hero-bg');
    if (hero) {
      const r = hero.getBoundingClientRect();
      out.heroBg = [Math.round(r.left), Math.round(r.width), Math.round(r.height)];
    }
    const v = document.querySelector('.hero-bg video');
    if (v) {
      const r = v.getBoundingClientRect();
      out.heroVideo = [Math.round(r.left), Math.round(r.width), Math.round(r.height)];
      out.videoIntrinsic = [v.videoWidth, v.videoHeight];
      out.videoReadyState = v.readyState;
      out.videoCurrentSrc = v.currentSrc;
    }
    const img = document.querySelector('.hero-bg img');
    if (img) {
      const r = img.getBoundingClientRect();
      out.heroImg = [Math.round(r.left), Math.round(r.width), Math.round(r.height)];
      out.imgNatural = [img.naturalWidth, img.naturalHeight];
      out.imgSrc = img.currentSrc;
    }
    const promo = document.getElementById('promo');
    if (promo) out.promoCurrentSrc = promo.currentSrc;
    return JSON.stringify(out);
  })()`,
  returnByValue: true,
}, sessionId);

console.log('  ' + probe.result.value);
ws.close();
chrome.kill();
process.exit(0);
