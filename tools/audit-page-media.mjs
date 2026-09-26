// audit-page-media.mjs — every video and image the live page loads, and which are
// actually visible.
//
// Written because "the video still looks the same" has to be answered with evidence
// about WHICH FILE the page is playing, not with a claim that it was replaced.
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

const url = process.argv[2] || 'https://lumawall.xinet.id/';
const port = 9900 + Math.floor(Math.random() * 90);
const profile = mkdtempSync(join(tmpdir(), 'lw-audit-'));

const chrome = spawn(CHROME, [
  '--headless=new', `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900', url,
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

console.log('  page: ' + url);
console.log();
console.log(await ev(`(() => {
  const rows = [];
  document.querySelectorAll('video').forEach((v, i) => {
    const r = v.getBoundingClientRect();
    const s = getComputedStyle(v);
    rows.push('  VIDEO ' + (i+1) + ': ' + (v.currentSrc || v.src || '(none)').split('/').pop());
    rows.push('     id=' + (v.id || '-') + ' class=' + (v.className || '-'));
    rows.push('     ' + Math.round(r.width) + 'x' + Math.round(r.height) +
              '  display=' + s.display + ' opacity=' + s.opacity +
              ' paused=' + v.paused + ' t=' + v.currentTime.toFixed(2) +
              ' dur=' + (isNaN(v.duration) ? '?' : v.duration.toFixed(2)));
    rows.push('     poster=' + (v.poster || '').split('/').pop());
    const src = v.querySelector('source');
    if (src) rows.push('     <source>=' + (src.src || '').split('/').pop());
  });
  document.querySelectorAll('img').forEach((im, i) => {
    const r = im.getBoundingClientRect();
    if (r.width < 4) return;
    rows.push('  IMG ' + (i+1) + ': ' + (im.currentSrc || im.src || '').split('/').pop() +
              '  ' + Math.round(r.width) + 'x' + Math.round(r.height));
  });
  return rows.join('\\n');
})()`));

ws.close();
chrome.kill();
process.exit(0);
