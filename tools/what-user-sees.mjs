// what-user-sees.mjs — loads the live site as a fresh visitor and reports what is
// actually on screen, including whether the video is playing and which file it is.
//
// This exists because "I refreshed and nothing changed" has two possible causes that
// look identical from the outside: the deploy did not land, or the browser served a
// cached copy. Reporting the URL and the byte count separates them.
import { spawn } from 'node:child_process';
import { mkdtempSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);

const port = 9800 + Math.floor(Math.random() * 150);
const profile = mkdtempSync(join(tmpdir(), 'lw-see-'));
const chrome = spawn(CHROME, [
  '--headless=new', `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900',
  'https://lumawall.xinet.id/',
], { stdio: 'ignore' });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
await sleep(7000);

const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = list.find((t) => t.type === 'page' && !t.url.startsWith('devtools'));
const ws = new WebSocket(page.webSocketDebuggerUrl);
let id = 0;
const pend = new Map();
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
};
await new Promise((r) => (ws.onopen = r));
const send = (method, params = {}) =>
  new Promise((res) => { const i = ++id; pend.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.result?.exceptionDetails) return 'EXC ' + r.result.exceptionDetails.text;
  return r.result?.result?.value;
};

// Scroll to the promo so it starts, like a visitor would.
await ev(`document.getElementById('video').scrollIntoView({block:'center'})`);
await sleep(6000);

console.log(await ev(`(() => {
  const v = document.getElementById('promo');
  const hero = document.querySelector('.hero-bg video') || document.querySelector('.hero-bg img');
  const out = {
    promoFile: v ? (v.currentSrc || '').split('/').pop() : null,
    promoDuration: v ? +v.duration.toFixed(2) : null,
    promoTime: v ? +v.currentTime.toFixed(2) : null,
    promoPaused: v ? v.paused : null,
    heroFile: hero ? (hero.currentSrc || hero.src || '').split('/').pop() : null,
    heroOpacity: hero ? getComputedStyle(hero).opacity : null,
    cssFile: [...document.querySelectorAll('link[rel=stylesheet]')].map(l => l.href.split('/').pop()).join(' '),
    jsFile: [...document.querySelectorAll('script[src]')].map(s => s.src.split('/').pop()).join(' '),
  };
  return JSON.stringify(out, null, 1);
})()`));

// And confirm the video has actually advanced, which is what "it plays" means.
const t1 = await ev(`+document.getElementById('promo').currentTime.toFixed(2)`);
await sleep(1500);
const t2 = await ev(`+document.getElementById('promo').currentTime.toFixed(2)`);
console.log('  clock: %s -> %s  %s', t1, t2, t2 > t1 ? '(playing)' : '(NOT PLAYING)');

ws.close();
chrome.kill();
process.exit(0);
