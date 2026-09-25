// probe-console.mjs — captures the page's console and any script error.
//
// The markup is correct on disk and over HTTP, but the DOM query returns nothing,
// which points at a script error. This attaches before navigation so nothing is
// missed, then reports every console entry and exception.

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, mkdtempSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5190;

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

const profile = mkdtempSync(join(tmpdir(), 'lw-con-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9454',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900',
  'about:blank',
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9454/json/version');
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
const events = [];
sock.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const { res, rej } = pending.get(m.id);
    pending.delete(m.id);
    m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
    return;
  }
  if (m.method === 'Runtime.consoleAPICalled') {
    events.push('console.' + m.params.type + ': ' +
      m.params.args.map((a) => a.value ?? a.description ?? a.type).join(' '));
  }
  if (m.method === 'Runtime.exceptionThrown') {
    const d = m.params.exceptionDetails;
    events.push('EXCEPTION: ' + (d.exception && d.exception.description ? d.exception.description.split('\n')[0] : d.text));
  }
  if (m.method === 'Log.entryAdded') {
    events.push('log.' + m.params.entry.level + ': ' + m.params.entry.text);
  }
};
const send = (method, params = {}, sessionId) => {
  const i = ++id; const p = { id: i, method, params };
  if (sessionId) p.sessionId = sessionId;
  return new Promise((res, rej) => { pending.set(i, { res, rej }); sock.send(JSON.stringify(p)); });
};

const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });

// Enable the domains BEFORE navigating, so nothing is missed.
await send('Runtime.enable', {}, sessionId);
await send('Log.enable', {}, sessionId);
await send('Page.enable', {}, sessionId);
await send('Page.navigate', { url: `http://127.0.0.1:${PORT}/` }, sessionId);
await new Promise((r) => setTimeout(r, 4000));

const state = (await send('Runtime.evaluate', {
  expression: `(() => ({
    ready_state: document.readyState,
    sections: document.querySelectorAll('section').length,
    video: !!document.getElementById('promo'),
    cover: !!document.querySelector('.video-cover'),
    buttons: document.querySelectorAll('button').length,
    scripts: document.querySelectorAll('script').length,
    body_len: document.body ? document.body.innerHTML.length : 0,
  }))()`,
  returnByValue: true,
}, sessionId)).result.value;

console.log('  DOM:');
for (const [k, v] of Object.entries(state)) console.log('    ' + k.padEnd(14) + ': ' + v);

console.log('');
console.log('  console / exceptions:');
if (!events.length) console.log('    (none)');
for (const e of events.slice(0, 20)) console.log('    ' + e.slice(0, 160));

sock.close();
chrome.kill();
srv.close();
process.exit(0);
