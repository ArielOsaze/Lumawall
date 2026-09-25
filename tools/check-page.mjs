// check-page.mjs — the checks that catch what a status code cannot.
//
// Each of these corresponds to a real defect that shipped:
//
//   · the video did not autoplay          -> the promo was a still frame
//   · a 1080p badge sat over the poster   -> a label nobody asked for
//   · the hero image was badly cropped    -> the subject's head was cut off
//   · the video cover never disappeared   -> `play` fires even when autoplay is
//                                            refused, so the cover hid while the
//                                            video sat at 0:00
//
// Run:  node tools/check-page.mjs

import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, mkdtempSync } from 'node:fs';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5192;

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.webp': 'image/webp', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
  '.mp4': 'video/mp4', '.woff2': 'font/woff2', '.json': 'application/json',
};

const srv = createServer(async (req, res) => {
  try {
    let rel = decodeURIComponent(req.url.split('?')[0]);
    if (rel === '/' || rel.endsWith('/')) rel += 'index.html';
    const b = await readFile(join(SITE, rel));
    const type = MIME[extname(rel)] || 'application/octet-stream';

    // Range support. Chrome asks for byte ranges when seeking a video, and a server
    // that ignores the header makes it buffer from the start every time - which is
    // what left the promo at t=0 in this check while the CDN served it fine.
    const range = req.headers.range;
    if (range) {
      const m = /bytes=(\d*)-(\d*)/.exec(range);
      if (m) {
        const start = m[1] ? parseInt(m[1], 10) : 0;
        const end = m[2] ? parseInt(m[2], 10) : b.length - 1;
        const chunk = b.subarray(start, end + 1);
        res.writeHead(206, {
          'Content-Type': type,
          'Content-Range': `bytes ${start}-${end}/${b.length}`,
          'Accept-Ranges': 'bytes',
          'Content-Length': chunk.length,
        });
        res.end(chunk);
        return;
      }
    }

    res.writeHead(200, {
      'Content-Type': type,
      'Accept-Ranges': 'bytes',
      'Content-Length': b.length,
    });
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

const profile = mkdtempSync(join(tmpdir(), 'lw-page-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=9456',
  `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--window-size=1440,900',
  `http://127.0.0.1:${PORT}/`,
], { stdio: 'ignore' });

async function wsUrl() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch('http://127.0.0.1:9456/json/version');
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
sock.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const { res, rej } = pending.get(m.id);
    pending.delete(m.id);
    m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
  }
};
const send = (method, params = {}, sessionId) => {
  const i = ++id; const p = { id: i, method, params };
  if (sessionId) p.sessionId = sessionId;
  return new Promise((res, rej) => { pending.set(i, { res, rej }); sock.send(JSON.stringify(p)); });
};

// Wait for a page target that has actually navigated to the site, not just any
// page target: Chrome opens about:blank first, and attaching to that produced an
// empty DOM and a screenful of false failures.
let target = null;
for (let i = 0; i < 90 && !target; i++) {
  const { targetInfos } = await send('Target.getTargets');
  target = targetInfos.find(
    (t) => t.type === 'page' && t.url.includes('127.0.0.1:' + PORT)
  );
  if (!target) await new Promise((r) => setTimeout(r, 400));
}
if (!target) {
  console.log('  the browser never navigated to the site');
  chrome.kill(); srv.close();
  process.exit(1);
}
const { sessionId } = await send('Target.attachToTarget', { targetId: target.targetId, flatten: true });
await send('Page.enable', {}, sessionId);
await send('Runtime.enable', {}, sessionId);

// And wait for the DOM to be there before measuring anything.
for (let i = 0; i < 40; i++) {
  const ready = await send('Runtime.evaluate', {
    expression: 'document.readyState === "complete" && document.querySelectorAll("section").length > 0',
    returnByValue: true,
  }, sessionId);
  if (ready.result.value) break;
  await new Promise((r) => setTimeout(r, 300));
}
await new Promise((r) => setTimeout(r, 1200));

const evalJs = async (expr) =>
  (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }, sessionId)).result.value;

// Confirm the page actually loaded before checking anything about it. Without
// this, a page that never navigated reports every check as a failure, which
// sends you looking for bugs in code that is fine.
const loaded = await evalJs(`(() => ({
  href: location.href,
  ready: document.readyState,
  sections: document.querySelectorAll('section').length,
  images: document.images.length,
  body_len: document.body ? document.body.innerHTML.length : 0,
}))()`);

console.log('  page:');
for (const [k, v] of Object.entries(loaded)) console.log('    ' + k.padEnd(10) + ': ' + v);
console.log('');

if (!loaded.body_len) {
  console.log('  the page did not load; nothing to check');
  sock.close(); chrome.kill(); srv.close();
  process.exit(1);
}
console.log('  checks:');

let failures = 0;
const check = (name, ok, detail) => {
  console.log('    ' + (ok ? 'PASS' : 'FAIL') + '  ' + name + (detail ? '  (' + detail + ')' : ''));
  if (!ok) failures++;
};

// ── 1. no 1080p badge ────────────────────────────────────────────────────────
const badge = await evalJs(`(() => {
  // The badge sat over the video's top-left corner. "1080p" as a resolution in
  // the body copy is a different thing and is fine.
  const overVideo = document.querySelector('.video-frame .video-badge, .video-badge');
  const inVideo = (() => {
    const v = document.getElementById('promo');
    if (!v) return false;
    const frame = v.closest('.video-frame') || v.parentElement;
    return /1080p/i.test(frame ? frame.innerText : '');
  })();
  return { badge_element: !!overVideo, text_over_video: inVideo };
})()`);
check('no 1080p badge over the video', !badge.badge_element && !badge.text_over_video,
  JSON.stringify(badge));

// ── 2. the video autoplays when scrolled to ──────────────────────────────────
//
// The wait has to be adaptive. This is a 16 MB file served by a plain Node static
// server, which is slower than the CDN, and a fixed 3.5s wait was not always enough
// for the browser to buffer the first frames - the check then failed with t=0 and
// the whole run took five minutes waiting on a retry. It now polls until the video
// actually advances, and reports what it saw if it never does.
const videoState = await evalJs(`(async () => {
  const v = document.getElementById('promo');
  if (!v) return { exists: false };
  v.scrollIntoView({ block: 'center' });

  const started = Date.now();
  let lastTime = -1;
  let stalledFor = 0;
  while (Date.now() - started < 45000) {
    await new Promise(r => setTimeout(r, 500));
    if (v.currentTime > lastTime) { lastTime = v.currentTime; stalledFor = 0; }
    else { stalledFor += 500; }
    // Enough to prove it plays, or clearly stuck.
    if (v.currentTime > 0.5) break;
    if (stalledFor > 20000) break;
  }

  return {
    exists: true,
    paused: v.paused,
    time: Math.round(v.currentTime * 100) / 100,
    muted: v.muted,
    autoplay_attr: v.hasAttribute('autoplay'),
    ready: v.readyState,
    network: v.networkState,
    error: v.error ? v.error.code : null,
    waited_ms: Date.now() - started,
    cover_present: !!document.querySelector('.video-cover'),
    badge_present: !!document.querySelector('.video-badge'),
  };
})()`);

check('the promo video element exists', videoState.exists);
check('the video is playing, not paused', videoState.exists && videoState.paused === false,
  'paused=' + videoState.paused + ' t=' + videoState.time);
check('the video has advanced past 0', videoState.exists && videoState.time > 0.2,
  't=' + videoState.time);
check('the video is muted (required for autoplay)', videoState.exists && videoState.muted === true);
check('no play cover is covering the video', videoState.exists && videoState.cover_present === false);
check('no badge is over the video', videoState.exists && videoState.badge_present === false);

// ── 2b. a deliberate pause is respected ──────────────────────────────────────
const pauseBehaviour = await evalJs(`(async () => {
  const v = document.getElementById('promo');
  if (!v) return { skipped: true };
  v.scrollIntoView({ block: 'center' });
  await new Promise(r => setTimeout(r, 1200));

  // The visitor presses pause.
  v.pause();
  await new Promise(r => setTimeout(r, 200));
  const pausedAfterClick = v.paused;

  // Then scrolls away and comes back.
  window.scrollTo({ top: 0, behavior: 'instant' });
  await new Promise(r => setTimeout(r, 900));
  v.scrollIntoView({ block: 'center' });
  await new Promise(r => setTimeout(r, 1500));

  return { skipped: false, pausedAfterClick, pausedAfterReturn: v.paused };
})()`);

check('a deliberate pause survives scrolling away and back',
  pauseBehaviour.skipped || (pauseBehaviour.pausedAfterClick && pauseBehaviour.pausedAfterReturn),
  JSON.stringify(pauseBehaviour));

// Put it back for the remaining checks.
await evalJs(`(async () => {
  const v = document.getElementById('promo');
  if (v) { v.muted = true; try { await v.play(); } catch {} }
  return true;
})()`);

// ── 3. the hero image is not badly cropped ───────────────────────────────────
const hero = await evalJs(`(() => {
  const im = document.querySelector('.hero-bg img');
  if (!im) return { exists: false };
  const r = im.getBoundingClientRect();
  const nw = im.naturalWidth, nh = im.naturalHeight;
  const srcRatio = nw / nh, boxRatio = r.width / r.height;
  const kept = srcRatio > boxRatio ? boxRatio / srcRatio : srcRatio / boxRatio;
  return {
    exists: true,
    src: im.getAttribute('src'),
    natural: nw + 'x' + nh,
    box: Math.round(r.width) + 'x' + Math.round(r.height),
    kept: Math.round(kept * 100),
    position: getComputedStyle(im).objectPosition,
    opacity: getComputedStyle(im).opacity,
  };
})()`);

check('the hero has a background image', hero.exists);
check('the hero image keeps most of its frame', hero.exists && hero.kept >= 70,
  hero.kept + '% kept');
check('the hero image is visible, not near-invisible',
  hero.exists && parseFloat(hero.opacity) >= 0.4, 'opacity ' + hero.opacity);

// ── 4. nothing on the page is stuck invisible ────────────────────────────────
const reveals = await evalJs(`(async () => {
  for (let y = 0; y <= document.body.scrollHeight; y += 300) {
    window.scrollTo({ top: y, behavior: 'instant' });
    await new Promise(r => setTimeout(r, 110));
  }
  window.scrollTo({ top: 0, behavior: 'instant' });
  await new Promise(r => setTimeout(r, 2600));
  const hidden = [];
  document.querySelectorAll('.reveal').forEach(el => {
    if (parseFloat(getComputedStyle(el).opacity) < 0.05) {
      hidden.push((el.className || '').toString().slice(0, 30));
    }
  });
  return { total: document.querySelectorAll('.reveal').length, hidden };
})()`);
check('every reveal element became visible', reveals.hidden.length === 0,
  reveals.hidden.length + ' hidden of ' + reveals.total);

// ── 5. no removed effect has crept back ──────────────────────────────────────
const leftovers = await evalJs(`(() => {
  const out = [];
  if (document.querySelector('.ch')) out.push('split characters');
  if (document.querySelector('.shiny')) out.push('shiny sweep');
  if (document.querySelector('.grad')) out.push('gradient text');
  const mono = Array.from(document.querySelectorAll('body *')).some(el =>
    /monospace|Consolas|Cascadia|Courier/i.test(getComputedStyle(el).fontFamily || ''));
  if (mono) out.push('monospace font');
  return out;
})()`);
check('no removed effect has returned', leftovers.length === 0, leftovers.join(', '));

// ── 6. the copy has no machine-writing tells ─────────────────────────────────
const copy = await evalJs(`(() => {
  const t = document.body.innerText;
  return {
    emdash: (t.match(/\\u2014/g) || []).length,
    bukan_sekadar: (t.match(/bukan sekadar/gi) || []).length,
    yang_memang: (t.match(/yang memang/gi) || []).length,
  };
})()`);
check('no em-dash in the page copy', copy.emdash === 0, String(copy.emdash));
check('no "bukan sekadar"', copy.bukan_sekadar === 0);
check('no "yang memang"', copy.yang_memang === 0);

console.log('');
if (failures) {
  console.log('  ' + failures + ' check(s) failed');
  sock.close(); chrome.kill(); srv.close();
  process.exit(1);
}
console.log('  all checks passed');

sock.close();
chrome.kill();
srv.close();
process.exit(0);
