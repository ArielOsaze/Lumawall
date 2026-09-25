// probe-dom.mjs — what does the browser actually receive and parse?
//
// The source file contains the element but the DOM does not, which means the
// markup is being altered between disk and the parser. This compares the three
// stages: file on disk, bytes over HTTP, and the parsed DOM.

import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(here, '..', 'site');
const PORT = 5189;

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };

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

// Stage 1: the file on disk.
const disk = await readFile(join(SITE, 'index.html'), 'utf8');
console.log('  file on disk:');
console.log('    video-frame  : ' + (disk.match(/video-frame/g) || []).length);
console.log('    video-cover  : ' + (disk.match(/video-cover/g) || []).length);
console.log('    <button      : ' + (disk.match(/<button/g) || []).length);

// Stage 2: the bytes over HTTP.
const served = await (await fetch(`http://127.0.0.1:${PORT}/`)).text();
console.log('  served over http:');
console.log('    identical to disk : ' + (served === disk));
console.log('    video-cover       : ' + (served.match(/video-cover/g) || []).length);

// Stage 3: find the section and print it, so a structural problem is visible.
const i = served.indexOf('video-frame');
console.log('  markup around the video frame:');
const chunk = served.slice(i - 60, i + 1400);
for (const line of chunk.split('\n')) console.log('    ' + line);

srv.close();
