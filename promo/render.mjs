// render.mjs — captures the promo page frame by frame and encodes it to MP4.
//
// Why not a screen recorder: a recorder samples the screen at whatever rate it
// manages, so the output drifts, drops frames under load, and cannot be
// reproduced. This drives the page's own clock instead - it sets frame N, waits
// for the browser to paint, grabs exactly that frame, and moves on. Every frame is
// the frame it claims to be, and a re-run produces the same video.
//
// Pipeline:
//   Chrome (headless) -> CDP Page.captureScreenshot -> PNG -> ffmpeg stdin
//
// The PNGs go to ffmpeg over a pipe, so no intermediate image files are written.

import { spawn } from 'node:child_process';
import { mkdirSync, existsSync, rmSync, writeFileSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'vite';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));   // promo/
const root = resolve(here, '..');                       // repo root

const args = process.argv.slice(2);
function arg(name, fallback) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
}

const OUT = arg('--out', join(root, 'site', 'assets', 'video', 'lumawall-promo.mp4'));
const FPS = Number(arg('--fps', '30'));
const WIDTH = 1920;
const HEIGHT = 1080;
const DURATION = Number(arg('--duration', '52'));
const SCALE = Number(arg('--scale', '1'));     // 1 = full quality, 0.5 = fast preview
const MAX_FRAMES = Number(arg('--max-frames', '0')) || Infinity;
const CRF = arg('--crf', '18');

const totalFrames = Math.min(Math.ceil(DURATION * FPS), MAX_FRAMES);
const outW = Math.round(WIDTH * SCALE);
const outH = Math.round(HEIGHT * SCALE);

console.log('LumaWall promo render');
console.log('  frames :', totalFrames, `(${DURATION}s @ ${FPS}fps)`);
console.log('  output :', `${outW}x${outH}`);
console.log('  file   :', OUT);
console.log('');

// ── Chrome ──────────────────────────────────────────────────────────────────
const CHROME = [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);

if (!CHROME) {
  console.error('Chrome or Edge not found.');
  process.exit(1);
}

// ── build the composition, then serve it statically ────────────────────────
await build({
  configFile: join(here, 'vite.config.js'),
  root: here,
  logLevel: 'warn',
});

const DIST = join(here, 'dist');
const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.mp4': 'video/mp4',
};

const staticServer = createServer(async (req, res) => {
  try {
    let rel = decodeURIComponent(req.url.split('?')[0]);
    if (rel === '/' || rel.endsWith('/')) rel += 'index.html';
    const file = join(DIST, rel);
    // Keep every request inside dist.
    if (!file.startsWith(DIST)) { res.writeHead(403).end(); return; }
    const body = await readFile(file);
    res.writeHead(200, { 'Content-Type': MIME[extname(file)] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404).end('not found');
  }
});

await new Promise((r) => staticServer.listen(5178, '127.0.0.1', r));
const URL = 'http://127.0.0.1:5178/';
console.log('  served :', URL);

// ── ffmpeg ──────────────────────────────────────────────────────────────────
mkdirSync(dirname(OUT), { recursive: true });

// Encode to a temporary file, then move it into place once ffmpeg has exited
// successfully. Writing straight to OUT meant that for the whole render the
// final path held a growing fragment: a deploy during that window published a
// 48-byte file that still returned 200 with Content-Type: video/mp4, so every
// automated check passed while the video was empty.
const TMP_OUT = OUT.replace(/\.mp4$/i, '') + '.part.mp4';

const ff = spawn('ffmpeg', [
  '-y',
  '-f', 'image2pipe',
  '-framerate', String(FPS),
  '-i', '-',
  '-vf', `scale=${outW}:${outH}:flags=lanczos`,
  '-c:v', 'libx264',
  '-preset', 'slow',
  '-crf', CRF,
  '-pix_fmt', 'yuv420p',
  '-movflags', '+faststart',
  '-r', String(FPS),
  TMP_OUT,
], { stdio: ['pipe', 'ignore', 'pipe'] });

let ffErr = '';
ff.stderr.on('data', (d) => { ffErr += d.toString(); });

// Without this, ffmpeg exiting mid-render raises an unhandled 'error' on the
// stdin pipe and the process dies with a stack trace, hiding ffmpeg's own
// message - which is the part that says what actually went wrong.
ff.stdin.on('error', () => {});

const ffDone = new Promise((res) => ff.on('close', (code) => res(code)));

// ── CDP ─────────────────────────────────────────────────────────────────────
// A tiny CDP client over the DevTools websocket. Node 26 has WebSocket built in,
// so no dependency is needed.
const { spawn: spawnProc } = await import('node:child_process');
const { mkdtempSync } = await import('node:fs');
const { tmpdir } = await import('node:os');

const profile = mkdtempSync(join(tmpdir(), 'lw-chrome-'));
const chrome = spawnProc(CHROME, [
  '--headless=new',
  '--remote-debugging-port=9333',
  `--user-data-dir=${profile}`,
  '--no-first-run',
  '--no-default-browser-check',
  '--disable-extensions',
  '--hide-scrollbars',
  '--force-device-scale-factor=1',
  '--window-size=1920,1080',
  '--enable-gpu-rasterization',
  '--disable-frame-rate-limit',
  '--disable-gpu-vsync',
  `--app=${URL}`,
], { stdio: 'ignore' });

// Wait for the debugging endpoint.
async function getWsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9333/json/version');
      const j = await r.json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error('Chrome DevTools endpoint never came up');
}

const wsUrl = await getWsUrl();
const ws = new WebSocket(wsUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

let msgId = 0;
const pending = new Map();
const events = [];

ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const { resolve: res, reject: rej } = pending.get(msg.id);
    pending.delete(msg.id);
    msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
  } else if (msg.method) {
    events.push(msg);
  }
};

function send(method, params = {}, sessionId) {
  const id = ++msgId;
  const payload = { id, method, params };
  if (sessionId) payload.sessionId = sessionId;
  return new Promise((res, rej) => {
    pending.set(id, { resolve: res, reject: rej });
    ws.send(JSON.stringify(payload));
  });
}

// Attach to the page target.
let target = null;
for (let i = 0; i < 60 && !target; i++) {
  const { targetInfos } = await send('Target.getTargets');
  target = targetInfos.find((t) => t.type === 'page' && t.url.includes('5178'));
  if (!target) await new Promise((r) => setTimeout(r, 400));
}
if (!target) throw new Error('promo page target not found');

const { sessionId } = await send('Target.attachToTarget', { targetId: target.targetId, flatten: true });

await send('Page.enable', {}, sessionId);
await send('Runtime.enable', {}, sessionId);
await send('Emulation.setDeviceMetricsOverride', {
  width: WIDTH, height: HEIGHT, deviceScaleFactor: 1, mobile: false,
}, sessionId);

// Wait for the navigation to finish before touching the page. Attaching to a
// target and evaluating straight away races the load: the first script can land
// in the old execution context, which is then destroyed, and the call fails with
// "Execution context was destroyed".
async function waitForEvent(method, timeoutMs) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (events.some((e) => e.method === method)) return true;
    await new Promise((r) => setTimeout(r, 100));
  }
  return false;
}

await waitForEvent('Page.loadEventFired', 20000);

// Then wait for the app itself. The probe is retried because a late redirect or a
// style/font load can still replace the context.
let ready = false;
for (let attempt = 0; attempt < 20 && !ready; attempt++) {
  try {
    const r = await send('Runtime.evaluate', {
      expression: `(async () => {
        await document.fonts.ready;
        if (window.__ready) return 'ready';
        return await new Promise(res => {
          const i = setInterval(() => {
            if (window.__ready) { clearInterval(i); res('ready'); }
          }, 50);
          setTimeout(() => { clearInterval(i); res('timeout'); }, 8000);
        });
      })()`,
      awaitPromise: true,
      returnByValue: true,
    }, sessionId);
    if (r?.result?.value === 'ready') ready = true;
  } catch {
    // Context replaced - re-attach and try again.
    await new Promise((r) => setTimeout(r, 500));
  }
}

if (!ready) throw new Error('the promo page never signalled readiness');

// Pin the viewport to the composition size now that the page has loaded.
await send('Emulation.setDeviceMetricsOverride', {
  width: WIDTH, height: HEIGHT, deviceScaleFactor: 1, mobile: false,
}, sessionId);

// Preload every wallpaper frame before capturing anything.
//
// The wallpaper clips are image sequences, and a <img> that has not decoded yet
// renders as nothing. During a render, the frame index changes faster than the
// images load, so without this the wallpaper would be blank in most frames — and
// it would look like a bug in the video rather than in the renderer.
{
  const r = await send('Runtime.evaluate', {
    expression: `(async () => {
      const dirs = ['raiden','astra','albedo','i14'];
      const urls = [];
      for (const d of dirs) {
        for (let i = 0; i < 60; i++) {
          urls.push('./frames/' + d + '/f' + String(i).padStart(3, '0') + '.webp');
        }
      }
      const results = await Promise.all(urls.map(u => new Promise(res => {
        const img = new Image();
        img.onload = () => res(true);
        img.onerror = () => res(false);
        img.src = u;
      })));
      const failed = urls.filter((u, i) => !results[i]);
      return {
        ok: urls.length - failed.length,
        total: urls.length,
        missing: failed.slice(0, 4),
      };
    })()`,
    awaitPromise: true,
    returnByValue: true,
  }, sessionId);

  const pre = r?.result?.value;
  console.log('  frames :', pre.ok + '/' + pre.total, 'preloaded');

  // Every wallpaper frame must load. If one is missing the component shows
  // nothing, the wallpaper sits frozen, and the renderer still reports success —
  // which is exactly how a promo for a moving wallpaper ended up containing a
  // still one. Fail loudly instead.
  if (pre.ok !== pre.total) {
    console.error('');
    console.error('  MISSING WALLPAPER FRAMES:', pre.missing.join(', '));
    console.error('  The video would contain a frozen wallpaper. Run:');
    console.error('    python tools/extract-clips.py');
    process.exit(2);
  }
}

console.log('  page   : ready');
console.log('');

// ── capture loop ────────────────────────────────────────────────────────────
const t0 = Date.now();
let lastLog = 0;

for (let f = 0; f < totalFrames; f++) {
  await send('Runtime.evaluate', {
    expression: `window.__setFrame(${f})`,
    returnByValue: true,
  }, sessionId);

  // Wait for the browser to actually paint the new state. Two animation frames
  // plus a task turn is the reliable minimum; the screenshot then reflects the
  // committed frame rather than the previous one.
  await send('Runtime.evaluate', {
    expression: 'new Promise(r => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(r, 0))))',
    awaitPromise: true,
    returnByValue: true,
  }, sessionId);

  const shot = await send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: false,
    fromSurface: true,
  }, sessionId);

  ff.stdin.write(Buffer.from(shot.data, 'base64'));

  const now = Date.now();
  if (now - lastLog > 4000 || f === totalFrames - 1) {
    lastLog = now;
    const pct = (((f + 1) / totalFrames) * 100).toFixed(1);
    const rate = (f + 1) / ((now - t0) / 1000);
    const eta = Math.round((totalFrames - f - 1) / rate);
    console.log(`  ${String(f + 1).padStart(5)}/${totalFrames}  ${pct.padStart(5)}%  ${rate.toFixed(1)} fps  eta ${eta}s`);
  }
}

ff.stdin.end();
const code = await ffDone;

ws.close();
chrome.kill();
await new Promise((r) => staticServer.close(r));
try { rmSync(profile, { recursive: true, force: true }); } catch { /* ignore */ }

if (code !== 0) {
  console.error('\nffmpeg failed:\n' + ffErr.split('\n').slice(-18).join('\n'));
  try { rmSync(TMP_OUT, { force: true }); } catch { /* ignore */ }
  process.exit(code || 1);
}

// ffmpeg exited cleanly, so the temporary file is a complete video. Move it into
// place; until this moment OUT either holds the previous good render or nothing.
const { statSync, renameSync } = await import('node:fs');
renameSync(TMP_OUT, OUT);
const size = statSync(OUT).size;
console.log('');
console.log(`  done: ${OUT}`);
console.log(`  size: ${(size / 1048576).toFixed(2)} MB`);
