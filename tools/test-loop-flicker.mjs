// Detect a black frame in the app's real wallpaper page.
//
// Why this exists: the wallpaper flashed black. It is a one-frame fault, so it is invisible
// in a screenshot and invisible in the log - the only way to see it is to sample the picture
// the compositor actually presented, frame by frame.
//
// ── the two things this gets right that the first attempt did not ────────────────
//
// 1. It runs the page the app ships, extracted from Program.cs, not a copy of it. The
//    first version kept its own copy of the page script "for clarity" - and so it kept
//    passing after the real page changed, because it was testing the copy. A test that
//    cannot see the code under test is worse than no test.
//
// 2. It samples the STAGE, composited, on requestVideoFrameCallback. Sampling a video
//    element cannot show the gap between two elements, and the gap is the fault: the
//    stage is transparent by design, so for one frame during a swap the desktop showed
//    through and the wallpaper flashed black. Sampling the stage sees that frame.
//
// ── the scenarios ───────────────────────────────────────────────────────────────
//
//   loop - let one clip run past its loop point several times. A decoder with nothing to
//          present at the wrap shows black.
//   swap - replace the wallpaper repeatedly. This is the case that broke: the outgoing
//          element was dropped on a 150ms timer while the incoming one could still be
//          transparent.
//
// Usage:
//   node tools/test-loop-flicker.mjs
//   node tools/test-loop-flicker.mjs --video C:/path/clip.mp4 --seconds 40
//   node tools/test-loop-flicker.mjs --scenario swap

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { resolve, dirname, extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');

function arg(name, fallback) {
  const index = process.argv.indexOf('--' + name);
  return index >= 0 && process.argv[index + 1] ? process.argv[index + 1] : fallback;
}

// Git Bash hands over paths like /c/Users/... and Windows wants C:\Users\... . Node's
// resolve() turns the first into C:\c\Users\..., which exists nowhere.
function windowsPath(value) {
  const drive = /^\/([a-zA-Z])\//.exec(value);
  return drive ? drive[1].toUpperCase() + ':/' + value.slice(3) : value;
}

const seconds = Number(arg('seconds', 40));
const scenario = arg('scenario', 'both');

// ── the page under test, taken from the app ──────────────────────────────────

function pageFromApp() {
  const program = readFileSync(join(root, 'LumaWall', 'Program.cs'), 'utf8');
  const start = program.indexOf('private string BuildMediaHtml()');
  if (start < 0) throw new Error('could not find BuildMediaHtml() in Program.cs');
  const literalStart = program.indexOf('@"', start);
  const literalEnd = program.indexOf('";', literalStart);
  if (literalStart < 0 || literalEnd < 0) throw new Error('could not find the verbatim string literal');
  // C# verbatim strings escape a quote by doubling it.
  return program.slice(literalStart + 2, literalEnd).replace(/""/g, '"');
}

let pageHtml;
try {
  pageHtml = pageFromApp();
} catch (error) {
  console.log('  ' + error.message);
  process.exit(1);
}

// ── the clips ────────────────────────────────────────────────────────────────
//
// Two clips are needed for the swap scenario, and they should differ in brightness: a swap
// between two clips of the same luminance could hide a one-frame black flash inside the
// tolerance.

function mp4sIn(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter((f) => f.toLowerCase().endsWith('.mp4')).map((f) => join(dir, f));
}

function pickClips() {
  const explicit = arg('video', null);
  if (explicit) {
    const resolved = resolve(windowsPath(explicit));
    if (!existsSync(resolved)) {
      console.log('  the video given with --video does not exist:');
      console.log('    given   : ' + explicit);
      console.log('    resolved: ' + resolved);
      console.log('  refusing to fall back to another clip - that would test the wrong video');
      process.exit(1);
    }
    const others = mp4sIn(join(root, 'LumaWall', 'assets')).filter((f) => f !== resolved);
    return [resolved, others[0] || resolved];
  }

  const user = mp4sIn(join(process.env.LOCALAPPDATA || '', 'LumaWall', 'Wallpapers'));
  if (user.length >= 2) return [user[0], user[1]];

  const bundled = mp4sIn(join(root, 'LumaWall', 'assets'));
  if (bundled.length >= 2) return [bundled[0], bundled[1]];
  if (bundled.length === 1) return [bundled[0], bundled[0]];

  console.log('  no .mp4 found to test with; pass one with --video path.mp4');
  process.exit(1);
}

const [clipA, clipB] = pickClips();

// ── serve the page and the clips ─────────────────────────────────────────────

const contentType = {
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
};

const server = createServer((req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');

  if (url.pathname === '/' || url.pathname === '/index.html') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(pageHtml);
    return;
  }

  const file = url.pathname === '/a' ? clipA : url.pathname === '/b' ? clipB : null;
  if (!file) {
    res.writeHead(404);
    res.end();
    return;
  }

  const size = statSync(file).size;
  const type = contentType[extname(file).toLowerCase()] || 'application/octet-stream';
  const range = req.headers.range;

  if (range) {
    const match = /bytes=(\d*)-(\d*)/.exec(range);
    const start = match[1] ? Number(match[1]) : 0;
    const end = match[2] ? Number(match[2]) : size - 1;
    res.writeHead(206, {
      'Content-Type': type,
      'Content-Range': `bytes ${start}-${end}/${size}`,
      'Accept-Ranges': 'bytes',
      'Content-Length': end - start + 1,
    });
    res.end(readFileSync(file).subarray(start, end + 1));
    return;
  }

  res.writeHead(200, { 'Content-Type': type, 'Content-Length': size, 'Accept-Ranges': 'bytes' });
  res.end(readFileSync(file));
});

await new Promise((done) => server.listen(0, '127.0.0.1', done));
const port = server.address().port;

// ── Chromium over CDP ────────────────────────────────────────────────────────

function findChromium() {
  const candidates = [
    process.env.CHROME_PATH,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
    'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  ].filter(Boolean);
  for (const candidate of candidates) if (existsSync(candidate)) return candidate;
  return null;
}

const chromium = findChromium();
if (!chromium) {
  console.log('  no Chromium found; set CHROME_PATH');
  server.close();
  process.exit(1);
}

const chrome = spawn(chromium, [
  '--headless=new',
  '--remote-debugging-port=0',
  '--user-data-dir=' + join(root, 'build', 'flicker-profile'),
  '--no-first-run',
  '--no-default-browser-check',
  '--disable-extensions',
  '--autoplay-policy=no-user-gesture-required',
  '--window-size=1920,1080',
  'about:blank',
], { stdio: ['ignore', 'pipe', 'pipe'] });

let stderr = '';
chrome.stderr.on('data', (chunk) => { stderr += chunk.toString(); });

const wsUrl = await new Promise((done, fail) => {
  const timer = setTimeout(() => fail(new Error('Chromium did not report a debugging port')), 20000);
  const check = () => {
    const match = /ws:\/\/[^\s]+/.exec(stderr);
    if (match) { clearTimeout(timer); done(match[0]); }
  };
  chrome.stderr.on('data', check);
  check();
});

const socket = new WebSocket(wsUrl);
await new Promise((done, fail) => {
  socket.addEventListener('open', done);
  socket.addEventListener('error', fail);
});

let nextId = 1;
const pending = new Map();
socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    const { done, fail } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) fail(new Error(message.error.message));
    else done(message.result);
  }
});

function send(method, params = {}, sessionId) {
  const id = nextId++;
  return new Promise((done, fail) => {
    pending.set(id, { done, fail });
    socket.send(JSON.stringify({ id, method, params, sessionId }));
  });
}

const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });

await send('Page.enable', {}, sessionId);
await send('Runtime.enable', {}, sessionId);
await send('Page.navigate', { url: `http://127.0.0.1:${port}/` }, sessionId);
await new Promise((done) => setTimeout(done, 1200));

async function evaluate(expression) {
  const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId);
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}

// ── the sampler ──────────────────────────────────────────────────────────────
//
// Installed into the real page from the outside, so the page itself is untouched. It
// composites what the stage shows - black underneath, each visible element on top at its
// own opacity - into a small canvas on every presented frame, and records the mean
// luminance. The black underneath is what the stage itself is painted, so a frame with no
// visible element reads as black, which is exactly the fault being hunted.
//
// It re-attaches to whatever video is currently in the stage on every frame. The first
// version held one element and stopped when that element was removed - so during the swap
// scenario, which removes an element on every swap, it recorded 21 frames out of a
// 24-second run and reported a failure for the wrong reason. The sampling must follow the
// element, because the element being replaced is the event under test.
await evaluate(`(() => {
  const stage = document.getElementById('stage');
  const probe = document.createElement('canvas');
  probe.width = 32; probe.height = 18;
  const ctx = probe.getContext('2d', { willReadFrequently: true });
  window.__samples = [];
  window.__sampling = false;
  window.__armed = null;

  function grab() {
    if (!window.__sampling) return;

    let lum = -1;
    try {
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, 32, 18);
      for (const el of stage.querySelectorAll('video, img')) {
        const opacity = Number(getComputedStyle(el).opacity);
        if (!(opacity > 0.01)) continue;
        ctx.globalAlpha = opacity;
        ctx.drawImage(el, 0, 0, 32, 18);
        ctx.globalAlpha = 1;
      }
      const d = ctx.getImageData(0, 0, 32, 18).data;
      let sum = 0;
      for (let i = 0; i < d.length; i += 4) sum += d[i] * 0.2126 + d[i + 1] * 0.7152 + d[i + 2] * 0.0722;
      lum = sum / (d.length / 4);
    } catch (e) { lum = -1; }

    window.__samples.push({ lum: Number(lum.toFixed(2)), at: Math.round(performance.now()) });

    // Follow the newest video, and keep a timer as a backstop: if the element under the
    // callback is removed mid-flight the callback never fires again, and a sampler that
    // silently stops is how the first version missed the swap entirely.
    const video = stage.querySelector('video');
    if (video && video.requestVideoFrameCallback) {
      if (window.__armed !== video) {
        window.__armed = video;
        video.requestVideoFrameCallback(grab);
      }
    }
    setTimeout(grab, 1000 / 30);
  }

  window.__startSampling = () => {
    window.__samples = [];
    window.__armed = null;
    window.__sampling = true;
    grab();
  };
  window.__stopSampling = () => { window.__sampling = false; return window.__samples; };
})()`);

async function waitForPicture() {
  for (let i = 0; i < 80; i++) {
    const ready = await evaluate(`(() => {
      const v = document.querySelector('#stage video');
      return !!(v && v.readyState >= 2 && v.videoWidth > 0);
    })()`);
    if (ready) return true;
    await new Promise((done) => setTimeout(done, 250));
  }
  return false;
}

// ── scenario: swap ───────────────────────────────────────────────────────────
//
// Two modes. The plain one runs in a window Chromium is presenting, where the fade always
// completes on time. The occluded one removes requestVideoFrameCallback first, which is
// what a covered window looks like from the page's point of view - Chromium stops
// presenting frames, so a callback that only fires on presentation never fires at all.
//
// The occluded mode is the one that matters. The fault being tested is a swap that drops
// the old element before the new one is opaque, and that can only happen when the fade
// does not complete on schedule - which is exactly the occluded case. The plain mode
// passed against the broken code, so it proves nothing on its own.

async function runSwap(occluded) {
  const label = occluded ? 'swap (occluded)' : 'swap';
  console.log(`  ${label}: replacing the wallpaper every 2.5s for ${seconds}s`);

  if (occluded) {
    await evaluate(`(() => {
      HTMLVideoElement.prototype.requestVideoFrameCallback = function () { return 0; };
      return true;
    })()`);
  }

  await evaluate(`window.luma.prepare('/a', false, true, 1)`);

  // Without requestVideoFrameCallback the page falls back to a timer for readiness, so
  // "ready" arrives without a picture being presented. Waiting on videoWidth is the part
  // that still holds.
  for (let i = 0; i < 80; i++) {
    const ready = await evaluate(`(() => {
      const v = document.querySelector('#stage video');
      return !!(v && v.readyState >= 2 && v.videoWidth > 0);
    })()`);
    if (ready) break;
    await new Promise((done) => setTimeout(done, 250));
  }

  await evaluate('window.__startSampling()');
  const until = Date.now() + seconds * 1000;
  let toggle = false;
  let swaps = 0;

  while (Date.now() < until) {
    toggle = !toggle;
    swaps++;
    await evaluate(`window.luma.prepare('${toggle ? '/b' : '/a'}', false, true, ${swaps + 1})`);
    await new Promise((done) => setTimeout(done, 2500));
  }

  return { samples: await evaluate('window.__stopSampling()'), swaps };
}

// ── scenario: loop ───────────────────────────────────────────────────────────

async function runLoop() {
  console.log(`  loop: one clip for ${seconds}s, past its loop point`);
  await evaluate(`window.luma.prepare('/a', false, true, 1)`);
  if (!(await waitForPicture())) {
    console.log('  the clip never produced a picture');
    return { samples: [], swaps: 0 };
  }

  await evaluate('window.__startSampling()');
  await new Promise((done) => setTimeout(done, seconds * 1000));
  return { samples: await evaluate('window.__stopSampling()'), swaps: 0 };
}

const results = [];
if (scenario === 'loop' || scenario === 'both') results.push(['loop', await runLoop()]);
if (scenario === 'swap' || scenario === 'both') results.push(['swap', await runSwap(false)]);
if (scenario === 'occluded' || scenario === 'both') results.push(['swap (occluded)', await runSwap(true)]);

socket.close();
chrome.kill();
server.close();

// ── the verdict ──────────────────────────────────────────────────────────────

let failed = false;

for (const [name, result] of results) {
  const samples = (result.samples || []).filter((s) => s.lum >= 0);

  console.log('');
  console.log(`  ── ${name} ──`);
  if (samples.length < 30) {
    console.log(`    only ${samples.length} frames sampled - the clip may not have played`);
    failed = true;
    continue;
  }

  const lums = samples.map((s) => s.lum);
  const sorted = [...lums].sort((a, b) => a - b);
  const median = sorted[Math.floor(sorted.length / 2)];

  // A black frame is one far below what this clip normally looks like, not merely dark: an
  // absolute threshold would call a genuinely dark wallpaper broken. The bar is a fraction
  // of the clip's own median, with a floor so a nearly-black clip is not held to 0.1.
  const floor = Math.max(2, median * 0.06);
  const black = samples.filter((s) => s.lum < floor);

  console.log(`    frames sampled    : ${samples.length}`);
  console.log(`    median luminance  : ${median.toFixed(2)} / 255`);
  console.log(`    black-frame floor : ${floor.toFixed(2)}`);
  if (result.swaps) console.log(`    swaps performed   : ${result.swaps}`);
  console.log(`    BLACK FRAMES      : ${black.length}`);

  if (black.length) {
    failed = true;
    console.log('');
    console.log('    the frames that went black:');
    for (const frame of black.slice(0, 10)) {
      console.log(`      luminance ${frame.lum} at ${frame.at}ms`);
    }
    if (black.length > 10) console.log(`      ... and ${black.length - 10} more`);
  }
}

console.log('');
if (failed) {
  console.log('  FAIL  a black frame is visible in the wallpaper');
  process.exit(1);
}
console.log('  PASS  no black frame was presented');
process.exit(0);
