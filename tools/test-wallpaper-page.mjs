// test-wallpaper-page.mjs - runs the app's real wallpaper page and reports what it does.
//
// Why this exists:
//
// When a wallpaper fails to apply, every signal inside the app looks fine: the log says
// "Media prepared in permanent host", the file exists, and the video is a valid H.264
// file that plays in any player. What is missing is what the PAGE does - and the page
// is generated as a string inside Program.cs, so nothing has ever executed it in a
// browser outside the app.
//
// This takes that generated HTML, loads it in Chromium with a real video, and reports
// every message the page posts back. A page that never posts `media-ready` is a page
// whose video never became ready, and that is exactly the failure that leaves a
// wallpaper black while the log reports success.
//
// Usage:
//   node tools/test-wallpaper-page.mjs
//   node tools/test-wallpaper-page.mjs --video "C:/path/to/wallpaper.mp4"
//   node tools/test-wallpaper-page.mjs --scenario paused-then-prepare
//
// Scenarios, because the app drives the page differently depending on what is on
// screen, and the failure only happens in some of them:
//
//   fresh               prepare on a page that is playing          (the simple case)
//   paused-then-prepare setPlayback(true), then prepare            (a covered monitor)
//   rapid               five prepares in a row                    (the user changing
//                                                                  wallpaper quickly)
//   all                 every scenario above, one after another
//
// The page HTML is extracted from Program.cs rather than retyped, so this tests the
// page the app actually ships.

import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, existsSync, rmSync, statSync, createReadStream } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { createServer } from 'node:http';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');

// ── arguments ────────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
function argValue(name, fallback) {
  const at = argv.indexOf('--' + name);
  return at >= 0 && argv[at + 1] ? argv[at + 1] : fallback;
}
const VIDEO = argValue('video', join(process.env.LOCALAPPDATA || '', 'LumaWall', 'Wallpapers', 'Prana System Error.mp4'));
const SCENARIO = argValue('scenario', 'all');

// ── extract the page from Program.cs ─────────────────────────────────────────
//
// The page is a C# verbatim string literal: @"...". Finding it by its first line and
// reading to the closing `";` is enough, and it means this test cannot drift from the
// app: if the page changes, this reads the new one.
//
// --source <file> reads the page from a different C# file, which is how a previous
// revision is tested: `git show HEAD:LumaWall/Program.cs > build/old.cs` then
// `--source build/old.cs`. Comparing old and new on the same scenario is the only way
// to know a fix fixed anything.
const SOURCE = argValue('source', join(root, 'LumaWall', 'Program.cs'));
const programPath = resolve(root, SOURCE);
const program = readFileSync(programPath, 'utf8');

const start = program.indexOf('private string BuildMediaHtml()');
if (start < 0) {
  console.error('  could not find BuildMediaHtml() in Program.cs');
  process.exit(1);
}
const literalStart = program.indexOf('@"', start);
const literalEnd = program.indexOf('";', literalStart);
if (literalStart < 0 || literalEnd < 0) {
  console.error('  could not find the verbatim string literal');
  process.exit(1);
}
let html = program.slice(literalStart + 2, literalEnd);
// C# verbatim strings escape a quote by doubling it.
html = html.replace(/""/g, '"');

console.log('');
console.log('  the app\'s real wallpaper page, run in Chromium');
console.log('  ' + '-'.repeat(58));
console.log('  extracted  ' + html.length + ' bytes of HTML from Program.cs');
console.log('  video      ' + VIDEO);

if (!existsSync(VIDEO)) {
  console.error('');
  console.error('  no video at that path - pass --video <path>');
  process.exit(2);
}

// ── serve the page and the video ─────────────────────────────────────────────
//
// Served over http rather than opened as a file: the app navigates to a file:// URL,
// and Chromium treats media loaded from file:// differently in ways that matter here.
// An http origin is the stricter case, so a page that works here works there.
const server = createServer((req, res) => {
  const url = req.url.split('?')[0];

  if (url === '/' || url === '/page.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
    return;
  }

  if (url === '/video.mp4') {
    // Range support, because a video element asks for ranges and a server that
    // ignores them makes the element behave differently from the app's file:// case.
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
      res.writeHead(200, {
        'Content-Length': size,
        'Accept-Ranges': 'bytes',
        'Content-Type': 'video/mp4',
      });
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

// ── launch Chromium ──────────────────────────────────────────────────────────
const CANDIDATES = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
];
const chrome = CANDIDATES.find((c) => existsSync(c));
if (!chrome) {
  console.error('  no Chrome or Edge found');
  process.exit(1);
}

const profile = mkdtempSync(join(tmpdir(), 'lumawall-page-'));
const child = spawn(chrome, [
  '--headless=new',
  '--remote-debugging-port=0',
  '--user-data-dir=' + profile,
  '--no-first-run',
  '--no-default-browser-check',
  '--disable-extensions',
  '--autoplay-policy=no-user-gesture-required',
  '--enable-accelerated-video-decode',
  '--window-size=1920,1080',
  'about:blank',
], { stdio: ['ignore', 'pipe', 'pipe'] });

// The port is written to stderr as "DevTools listening on ws://...".
const wsUrl = await new Promise((resolvePromise, reject) => {
  let buffer = '';
  const timer = setTimeout(() => reject(new Error('Chromium did not report a DevTools port')), 30000);
  child.stderr.on('data', (chunk) => {
    buffer += chunk.toString();
    const m = /DevTools listening on (ws:\/\/\S+)/.exec(buffer);
    if (m) {
      clearTimeout(timer);
      resolvePromise(m[1]);
    }
  });
  child.on('exit', (code) => {
    clearTimeout(timer);
    reject(new Error('Chromium exited early with code ' + code));
  });
});

// ── a minimal CDP client ─────────────────────────────────────────────────────
class CDP {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.nextId = 1;
    this.pending = new Map();
    this.handlers = new Map();
    this.ready = new Promise((r) => { this.ws.onopen = r; });
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
        return;
      }
      if (msg.method && this.handlers.has(msg.method)) {
        for (const fn of this.handlers.get(msg.method)) fn(msg.params);
      }
    };
  }

  send(method, params = {}, sessionId) {
    const id = this.nextId++;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    this.ws.send(JSON.stringify(payload));
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }));
  }

  on(method, fn) {
    if (!this.handlers.has(method)) this.handlers.set(method, []);
    this.handlers.get(method).push(fn);
  }
}

const browser = new CDP(wsUrl);
await browser.ready;

// ── one fresh page per scenario ──────────────────────────────────────────────
async function openPage() {
  const { targetId } = await browser.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await browser.send('Target.attachToTarget', { targetId, flatten: true });

  await browser.send('Page.enable', {}, sessionId);
  await browser.send('Runtime.enable', {}, sessionId);
  await browser.send('Log.enable', {}, sessionId);

  // The page posts its state with window.chrome.webview.postMessage. Outside the app
  // that object does not exist, so it is stubbed BEFORE the page script runs, and every
  // message is recorded. That is the whole point of this test: those messages are what
  // the app listens for, and a missing `media-ready` is the bug being hunted.
  await browser.send('Page.addScriptToEvaluateOnNewDocument', {
    source: `
      window.__lumaMessages = [];
      window.chrome = window.chrome || {};
      window.chrome.webview = {
        postMessage: function (m) { window.__lumaMessages.push(String(m)); }
      };
    `,
  }, sessionId);

  await browser.send('Page.navigate', { url: pageUrl }, sessionId);
  await new Promise((r) => setTimeout(r, 900));
  return sessionId;
}

async function evaluate(sessionId, expression) {
  const r = await browser.send('Runtime.evaluate', { expression, returnByValue: true }, sessionId);
  if (r.exceptionDetails) {
    return { __error: r.exceptionDetails.text + ' ' + (r.exceptionDetails.exception?.description || '') };
  }
  return r.result.value;
}

async function waitFor(sessionId, predicate, ms) {
  const deadline = Date.now() + ms;
  let last = [];
  while (Date.now() < deadline) {
    const raw = await evaluate(sessionId, 'JSON.stringify(window.__lumaMessages || [])');
    try { last = JSON.parse(raw || '[]'); } catch { last = []; }
    if (predicate(last)) return last;
    await new Promise((r) => setTimeout(r, 250));
  }
  return last;
}

async function videoState(sessionId) {
  const raw = await evaluate(sessionId, `(function(){
    var v = document.querySelector('video');
    if (!v) return JSON.stringify({ found: false });
    return JSON.stringify({
      found: true,
      readyState: v.readyState,
      paused: v.paused,
      currentTime: Number(v.currentTime.toFixed(2)),
      videoWidth: v.videoWidth,
      error: v.error ? (v.error.code + ' ' + v.error.message) : null,
      videos: document.querySelectorAll('video').length,
      opacity: getComputedStyle(v).opacity,
      display: getComputedStyle(v).display,
      zIndex: getComputedStyle(v).zIndex,
    });
  })()`);
  try { return JSON.parse(raw || '{}'); } catch { return {}; }
}

// ── the scenarios ────────────────────────────────────────────────────────────
const SCENARIOS = {
  // The simple case: the page is playing and the host sends a wallpaper.
  'fresh': async (sessionId) => {
    await evaluate(sessionId, `window.luma.prepare(${JSON.stringify(videoUrl)}, false, true, 1, 24)`);
    return waitFor(sessionId, (m) => m.some((x) => x.startsWith('media-ready') || x.startsWith('media-error')), 15000);
  },

  // A covered monitor. The host pauses playback as soon as it decides the screen is
  // hidden, and a wallpaper change can arrive while it is paused - so the page is asked
  // to prepare a video it has been told not to play. This is the case the machine was
  // in when the wallpaper failed to apply.
  'paused-then-prepare': async (sessionId) => {
    await evaluate(sessionId, 'window.luma.setPlayback(true, true)');
    await new Promise((r) => setTimeout(r, 300));
    await evaluate(sessionId, `window.luma.prepare(${JSON.stringify(videoUrl)}, false, true, 2, 24)`);
    return waitFor(sessionId, (m) => m.some((x) => x.startsWith('media-ready') || x.startsWith('media-error')), 15000);
  },

  // Changing wallpaper several times quickly, which is what a person browsing a
  // library does. Each prepare bumps the page's generation counter and discards the
  // previous element, so only the last one should report.
  'rapid': async (sessionId) => {
    for (let i = 1; i <= 5; i++) {
      await evaluate(sessionId, `window.luma.prepare(${JSON.stringify(videoUrl)}, false, true, ${100 + i}, 24)`);
      await new Promise((r) => setTimeout(r, 400));
    }
    return waitFor(sessionId, (m) => m.some((x) => x.startsWith('media-ready') || x.startsWith('media-error')), 20000);
  },

  // The occluded case, reproduced exactly. When a window is fully covered Chromium
  // stops presenting frames, and requestVideoFrameCallback - which only fires when a
  // frame is actually presented - never fires at all. The wallpapers on this machine
  // sit behind other windows, so this is the state the app is in when a wallpaper
  // change arrives. Reproduced by removing the callback entirely, which is
  // indistinguishable from the page's point of view.
  'occluded': async (sessionId) => {
    await evaluate(sessionId, `(function(){
      HTMLVideoElement.prototype.requestVideoFrameCallback = function(){ return 0; };
      return true;
    })()`);
    await evaluate(sessionId, `window.luma.prepare(${JSON.stringify(videoUrl)}, false, true, 7, 24)`);
    return waitFor(sessionId, (m) => m.some((x) => x.startsWith('media-ready') || x.startsWith('media-error')), 15000);
  },

  // Both at once: the wallpaper is covered (no frames presented) AND the host has
  // paused it, which is what a monitor hidden behind a fullscreen game looks like.
  'occluded-paused': async (sessionId) => {
    await evaluate(sessionId, `(function(){
      HTMLVideoElement.prototype.requestVideoFrameCallback = function(){ return 0; };
      return true;
    })()`);
    await evaluate(sessionId, 'window.luma.setPlayback(true, true)');
    await new Promise((r) => setTimeout(r, 300));
    await evaluate(sessionId, `window.luma.prepare(${JSON.stringify(videoUrl)}, false, true, 8, 24)`);
    return waitFor(sessionId, (m) => m.some((x) => x.startsWith('media-ready') || x.startsWith('media-error')), 15000);
  },
  // The memory pressure the app sends. When a monitor is covered, the app pauses the
  // wallpaper and calls Memory.simulatePressureNotification with level "critical" to
  // make Chromium release what it can. This scenario asks whether the page can still
  // do anything afterwards - which is the question that matters, because the host
  // waits for a message the page may no longer be able to send.
  'after-critical-pressure': async (sessionId) => {
    const control = await evaluate(sessionId, '1+1');
    console.log('    control before   ' + JSON.stringify(control));

    await browser.send('Memory.simulatePressureNotification', { level: 'critical' }, sessionId);
    await new Promise((r) => setTimeout(r, 2000));

    const after = await evaluate(sessionId, '1+1');
    console.log('    control after    ' + JSON.stringify(after));

    await evaluate(sessionId, `window.luma.prepare(${JSON.stringify(videoUrl)}, false, true, 9, 24)`);
    return waitFor(sessionId, (m) => m.some((x) => x.startsWith('media-ready') || x.startsWith('media-error')), 15000);
  },

  // The full sequence the app performs on a covered monitor: pause, then pressure.
  'paused-then-pressure-then-prepare': async (sessionId) => {
    await evaluate(sessionId, 'window.luma.setPlayback(true, true)');
    await new Promise((r) => setTimeout(r, 300));
    await browser.send('Memory.simulatePressureNotification', { level: 'critical' }, sessionId);
    await new Promise((r) => setTimeout(r, 1500));
    await evaluate(sessionId, `window.luma.prepare(${JSON.stringify(videoUrl)}, false, true, 10, 24)`);
    return waitFor(sessionId, (m) => m.some((x) => x.startsWith('media-ready') || x.startsWith('media-error')), 15000);
  },
};

let scenarios = Object.keys(SCENARIOS);
if (SCENARIO !== 'all') scenarios = [SCENARIO];
for (const s of scenarios) {
  if (!SCENARIOS[s]) {
    console.error('  unknown scenario: ' + s);
    console.error('  known: ' + Object.keys(SCENARIOS).join(', ') + ', all');
    process.exit(2);
  }
}

const results = [];

for (const name of scenarios) {
  console.log('');
  console.log('  scenario: ' + name);

  const sessionId = await openPage();

  let messages = [];
  let failure = null;
  try {
    messages = await SCENARIOS[name](sessionId);
  } catch (e) {
    failure = e.message;
  }

  const state = await videoState(sessionId);
  const gotReady = messages.some((m) => m.startsWith('media-ready'));
  const gotError = messages.some((m) => m.startsWith('media-error'));

  console.log('    messages   ' + (messages.length ? messages.join(' | ') : '(none)'));
  console.log('    video      ' + JSON.stringify(state));
  if (failure) console.log('    threw      ' + failure);

  const ok = gotReady;
  console.log('    ' + (ok ? 'PASS' : 'FAIL') + '       ' + (gotReady
    ? 'reached media-ready'
    : gotError
      ? 'reported media-error instead'
      : 'never reported anything - the host would wait forever'));

  results.push({ name, ok, messages, state, failure });

  try { await browser.send('Target.closeTarget', { targetId: (await browser.send('Target.getTargets')).targetInfos.find((t) => t.url.includes('page.html'))?.targetId || '' }); } catch {}
}

// ── verdict ──────────────────────────────────────────────────────────────────
console.log('');
console.log('  ' + '-'.repeat(58));
const failed = results.filter((r) => !r.ok);

for (const r of results) {
  console.log('  ' + (r.ok ? 'PASS' : 'FAIL') + '  ' + r.name);
}

console.log('');
if (failed.length === 0) {
  console.log('  every scenario reached media-ready.');
} else {
  console.log('  ' + failed.length + ' scenario(s) never reached media-ready:');
  for (const r of failed) {
    console.log('    · ' + r.name + '  -> ' + (r.messages.join(' | ') || '(no messages)'));
  }
  console.log('');
  console.log('  That is the bug: the host waits for media-ready and never gets it,');
  console.log('  so it never treats the wallpaper as applied.');
}

try { child.kill(); } catch {}
try { rmSync(profile, { recursive: true, force: true }); } catch {}
server.close();
process.exit(failed.length === 0 ? 0 : 1);
