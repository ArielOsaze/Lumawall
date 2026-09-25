// verify-video-journey.mjs — the visitor's journey, with the scroll confirmed.
//
// An earlier version scrolled and then sampled after a fixed delay. When the scroll
// had not taken effect the sample described a page nobody had scrolled, which read
// as a failure of the page. Every step now waits until the scroll actually happened.
import { spawn } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

const URL = process.argv[2] || 'http://127.0.0.1:5199/';
const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find(p => { try { return require('node:fs').existsSync(p); } catch { return false; } });

const { existsSync } = await import('node:fs');
const exe = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);

const port = 9500 + Math.floor(Math.random() * 400);
const profile = mkdtempSync(join(tmpdir(), 'lw-journey-'));
const chrome = spawn(exe, [
  '--headless=new', `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900',
  URL,
], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));
await sleep(5000);
const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = list.find(t => t.type === 'page' && !t.url.startsWith('devtools'));
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0; const pending = new Map();
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
await new Promise(r => ws.onopen = r);
const send = (method, params = {}) => new Promise(res => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const evalJs = async expr => {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.result?.exceptionDetails) return null;
  return r.result?.result?.value;
};

const state = async () => evalJs(`(() => {
  const v = document.getElementById('promo');
  const r = v.getBoundingClientRect();
  return { paused: v.paused, t: +v.currentTime.toFixed(2), scrollY: Math.round(scrollY),
           onScreen: r.bottom > 0 && r.top < innerHeight && r.height > 0 };
})()`);

// Scroll and wait until the page really is where we asked it to be.
const scrollTo = async (target, label) => {
  for (let i = 0; i < 25; i++) {
    await evalJs(target);
    await sleep(300);
    const s = await state();
    if (s && (label === 'video' ? s.onScreen : s.scrollY < 100)) return s;
  }
  return (await state()) || { paused: null, t: null, scrollY: null, onScreen: null };
};

const results = [];
const step = async (label, target, settleMs) => {
  await scrollTo(target, label);
  await sleep(settleMs);
  const s = (await state()) || { paused: null, t: null, scrollY: null, onScreen: null };
  results.push({ label, ...s });
  console.log('  ' + label.padEnd(26) + ' paused=' + String(s.paused).padEnd(5) +
              ' t=' + String(s.t).padEnd(6) + ' onScreen=' + s.onScreen);
  return s;
};

console.log('  === perjalanan pengunjung ===');
await step('1. di atas halaman', 'window.scrollTo(0,0)', 1200);
await step('2. scroll ke video', `document.getElementById('video').scrollIntoView({block:'center'})`, 5000);
await step('3. scroll menjauh', 'window.scrollTo(0,0)', 2500);
const back = await step('4. scroll kembali', `document.getElementById('video').scrollIntoView({block:'center'})`, 5000);
// Confirm the clock is moving, not just that paused reads false.
const t1 = (await state())?.t ?? null;
await sleep(1300);
const t2 = (await state())?.t ?? null;
const advancing = t1 !== null && t2 !== null && t2 > t1;
console.log('  jam video maju setelah kembali   : ' + (advancing ? ('ya (' + t1 + ' -> ' + t2 + ')') : 'TIDAK'));

console.log();
const played = results[1].paused === false;
const stopped = results[2].paused === true;
const resumed = back.paused === false && advancing;
console.log('  video main saat terlihat       : %s', played ? 'ya' : 'TIDAK');
console.log('  berhenti saat keluar layar     : %s', stopped ? 'ya' : 'TIDAK');
console.log('  main lagi saat kembali         : %s', resumed ? 'ya' : 'TIDAK');
const ok = played && stopped && resumed;
console.log();
console.log(ok ? '  LULUS - video mengikuti layar dengan benar'
              : '  GAGAL - perilaku video tidak sesuai');
ws.close(); chrome.kill();
process.exit(ok ? 0 : 1);
