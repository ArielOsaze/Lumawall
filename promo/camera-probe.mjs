// camera-probe.mjs — evaluate the promo's real camera function and print it.
//
// Why this exists:
//
// The check that is supposed to catch the camera cropping the frame has to know the
// camera's actual transform. The first version of that check re-implemented the
// camera's arithmetic in Python - and it re-implemented it WRONG: it hardcoded z = 1
// while Direction.jsx was still applying a 1.183 push-in, so it passed the very bug it
// was written for. A check that restates the thing it is checking cannot find a fault
// in it.
//
// So this imports the real module and prints what it actually returns. The Python check
// runs this and reads the numbers, so the two cannot disagree.
//
// It imports Direction.jsx through Vite's SSR transform, because the file is JSX and
// node cannot read it directly.

import { createServer } from 'vite';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const promo = here;

const server = await createServer({
  root: promo,
  logLevel: 'error',
  server: { middlewareMode: true },
  appType: 'custom',
});

try {
  const dir = await server.ssrLoadModule('/src/Direction.jsx');

  const total = dir.TOTAL_SECONDS;
  const frames = [];

  // Every 0.05s, the same sampling the Python check uses.
  for (let t = 0; t < total; t += 0.05) {
    const c = dir.camera(Number(t.toFixed(3)));
    frames.push({ t: Number(t.toFixed(3)), z: c.z, x: c.x, y: c.y, roll: c.roll });
  }

  // The shots, so the Python side can report per scene.
  const shots = dir.SHOTS.map((s) => ({ id: s.id, cut: s.cut }));

  process.stdout.write(JSON.stringify({
    total,
    frameW: dir.FRAME_W,
    frameH: dir.FRAME_H,
    shots,
    frames,
  }));
} finally {
  await server.close();
}
