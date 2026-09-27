// check-scrollbar-site.mjs — does the site actually ship a dark scrollbar?
//
// The complaint was "the scrollbar on the right is white". The page is near-black and
// Chromium's default bar is light, so the fix is CSS: `color-scheme: dark` plus the
// ::-webkit-scrollbar rules (Chromium needs both; color-scheme alone is not enough).
//
// This loads the real page from disk, forces it to overflow, and asks the browser what it
// resolved — the computed `color-scheme` and `scrollbar-color` on the root element, and
// whether the ::-webkit-scrollbar rule reached the stylesheet at all. It fails when the
// page does not overflow, because a scrollbar that is never drawn cannot be checked.
//
// Run:  node tools/check-scrollbar-site.mjs

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, mkdtempSync, writeFileSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');
const SITE = join(ROOT, 'site');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.mp4': 'video/mp4',
  '.ico': 'image/x-icon',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
  '.xml': 'application/xml',
  '.txt': 'text/plain',
};

function findChrome() {
  const candidates = [
    process.env.CHROME,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    join(process.env.LOCALAPPDATA || '', 'Google/Chrome/Application/chrome.exe'),
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  ].filter(Boolean);
  for (const c of candidates) if (existsSync(c)) return c;
  return null;
}

async function main() {
  const chrome = findChrome();
  if (!chrome) {
    console.log('  no Chrome or Edge found, so the page cannot be rendered.');
    return 1;
  }

  const server = createServer(async (req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0]);
    if (p === '/') p = '/index.html';
    const f = join(SITE, p);
    try {
      const body = await readFile(f);
      res.writeHead(200, { 'Content-Type': TYPES[extname(f)] || 'application/octet-stream' });
      res.end(body);
    } catch {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('not found');
    }
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;

  const profile = mkdtempSync(join(tmpdir(), 'sb-site-'));
  const child = spawn(chrome, [
    '--headless=new',
    '--remote-debugging-port=9457',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-extensions',
    '--user-data-dir=' + profile,
    '--window-size=1280,700',
    'about:blank',
  ], { stdio: 'ignore' });

  // Wait for the DevTools endpoint. The port must be passed to the browser: without
  // --remote-debugging-port it never opens the endpoint, and the wait below times out
  // with "the browser did not start" while the browser is running fine.
  const endpoint = 'http://127.0.0.1:9457';
  let up = false;
  for (let i = 0; i < 90; i++) {
    await new Promise((r) => setTimeout(r, 400));
    try {
      const res = await fetch(endpoint + '/json/version');
      if (res.ok) { up = true; break; }
    } catch { /* not yet */ }
  }
  if (!up) {
    console.log('  the browser did not start.');
    child.kill();
    server.close();
    return 1;
  }

  // Drive it over the DevTools protocol with no extra dependencies.
  const { webSocketDebuggerUrl } = await (await fetch(endpoint + '/json/version')).json();
  const ws = new WebSocket(webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener('open', r, { once: true }));

  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  });
  const send = (method, params = {}, sessionId) => new Promise((res) => {
    const n = ++id;
    pending.set(n, res);
    ws.send(JSON.stringify({ id: n, method, params, sessionId }));
  });

  const { result: target } = await send('Target.createTarget', { url: 'about:blank' });
  const { result: attached } = await send('Target.attachToTarget',
    { targetId: target.targetId, flatten: true });
  const sid = attached.sessionId;

  await send('Page.enable', {}, sid);
  await send('Runtime.enable', {}, sid);
  await send('Emulation.setDeviceMetricsOverride',
    { width: 1280, height: 700, deviceScaleFactor: 1, mobile: false }, sid);
  await send('Page.navigate', { url: 'http://127.0.0.1:' + port + '/' }, sid);
  await new Promise((r) => setTimeout(r, 2500));

  const evaluate = async (expr) => {
    const r = await send('Runtime.evaluate',
      { expression: expr, returnByValue: true, awaitPromise: true }, sid);
    if (r.result?.exceptionDetails) {
      throw new Error(r.result.exceptionDetails.text || 'evaluate failed');
    }
    return r.result?.result?.value;
  };

  const info = await evaluate(`(() => {
    const de = document.documentElement;
    const cs = getComputedStyle(de);
    // Does a ::-webkit-scrollbar rule exist anywhere in the loaded stylesheets?
    let webkit = 0;
    for (const sheet of document.styleSheets) {
      let rules;
      try { rules = sheet.cssRules; } catch { continue; }
      for (const rule of rules) {
        if (rule.selectorText && rule.selectorText.includes('-webkit-scrollbar')) webkit++;
      }
    }
    return {
      colorScheme: cs.colorScheme,
      scrollbarWidth: cs.scrollbarWidth,
      scrollbarColor: cs.scrollbarColor,
      webkitRules: webkit,
      overflows: de.scrollHeight > de.clientHeight + 10,
      scrollHeight: de.scrollHeight,
      clientHeight: de.clientHeight,
      barWidth: window.innerWidth - de.clientWidth,
      stylesheets: document.styleSheets.length,
    };
  })()`);

  console.log('  what the browser resolved:');
  for (const [k, v] of Object.entries(info)) console.log('    %s %s'.replace('%s', k.padEnd(16)).replace('%s', v));
  console.log();

  const problems = [];
  if (!info.stylesheets) problems.push('no stylesheet loaded at all');
  if (info.colorScheme !== 'dark') {
    problems.push(`color-scheme is ${JSON.stringify(info.colorScheme)}, not "dark" - ` +
                  'the browser will draw its light scrollbar');
  }
  if (!info.webkitRules) {
    problems.push('no ::-webkit-scrollbar rule reached the page, so Chromium keeps its ' +
                  'default light bar');
  }
  if (!info.overflows) {
    problems.push('the page does not overflow at 1280x700, so no scrollbar is drawn and ' +
                  'nothing was actually checked');
  }

  if (problems.length) {
    for (const p of problems) console.log('  FAIL  ' + p);
    ws.close(); child.kill(); server.close();
    return 1;
  }

  console.log('  OK    the page ships a dark scrollbar: color-scheme dark, ' +
              `${info.webkitRules} ::-webkit-scrollbar rule(s), thumb ${info.scrollbarColor}`);
  console.log(`        (scrollbar is drawn: content ${info.scrollHeight}px in ${info.clientHeight}px, ` +
              `bar ${info.barWidth}px wide)`);

  ws.close(); child.kill(); server.close();
  return 0;
}

process.exit(await main());
