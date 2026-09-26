// numbers-probe.mjs — render every scene and read back the text it actually draws.
//
// Why this exists, and why it replaces a pixel check:
//
// A scene once drew "NaN%" where a CPU figure belonged, and the render was accepted
// because nothing looked at what the numbers said. The check written to catch that
// tried to find the SHAPE of "NaN" in the video, and four attempts all failed on real
// frames:
//
//   · three equal-width glyphs matched the word "sama"
//   · requiring a narrower follower matched it again (the full stop)
//   · requiring the follower to be a percent sign by vertical position is fragile
//   · counting digits per value-shaped run reported body text, badge dots and link
//     text, and would have needed a size threshold tuned against each one
//
// All four were trying to read text from pixels. But the text is not in the pixels -
// it is in the scene, and the renderer computes it from JavaScript. So this asks the
// scene directly: it renders every scene at several moments and reads back every
// string of text in the DOM.
//
// That is exact. A "NaN" cannot hide from it, and a word cannot be mistaken for one.

import { createServer } from 'vite';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const here = dirname(fileURLToPath(import.meta.url));

const server = await createServer({
  root: here,
  logLevel: 'error',
  server: { middlewareMode: true },
  appType: 'custom',
});

try {
  const dir = await server.ssrLoadModule('/src/Direction.jsx');
  const timeline = await server.ssrLoadModule('/src/Timeline.jsx');

  const total = dir.TOTAL_SECONDS;
  const shots = dir.SHOTS;

  // Every scene, at several moments through its own shot. The moments are spread so a
  // value that is only wrong at the end - after an animation completes - is caught.
  const samples = [];
  for (let i = 0; i < shots.length; i++) {
    const cut = shots[i].cut;
    const end = i + 1 < shots.length ? shots[i + 1].cut : total;
    for (const frac of [0.05, 0.3, 0.55, 0.8, 0.98]) {
      samples.push({
        id: shots[i].id,
        t: cut + (end - cut) * frac,
        local: (end - cut) * frac,
      });
    }
  }

  // The scene components, by the same map Timeline uses.
  const SCENES = {};
  for (const id of shots.map((s) => s.id)) {
    const mod = await server.ssrLoadModule(`/src/scenes/${sceneFile(id)}.jsx`);
    SCENES[id] = mod.default;
  }

  const results = [];
  for (const s of samples) {
    const C = SCENES[s.id];
    if (!C) {
      results.push({ id: s.id, t: s.t, error: 'no scene component' });
      continue;
    }
    let html;
    try {
      html = renderToStaticMarkup(
        React.createElement(C, { t: s.local, global: s.t, start: 0, end: total, variant: 0 }),
      );
    } catch (e) {
      results.push({ id: s.id, t: s.t, error: String(e && e.message ? e.message : e) });
      continue;
    }

    // Every text node, with the tags stripped. This is what the renderer will draw.
    const text = html
      .replace(/<[^>]*>/g, '\u0001')
      .split('\u0001')
      .map((x) => x.trim())
      .filter((x) => x.length > 0);

    // And every attribute that carries a number into a style, since a NaN in a
    // transform silently produces an invalid value rather than visible text.
    const styleNums = [];
    for (const m of html.matchAll(/(translate3d|scale|translateX|translateY|rotateZ?)\(([^)]*)\)/g)) {
      styleNums.push(`${m[1]}(${m[2]})`);
    }

    results.push({ id: s.id, t: Number(s.t.toFixed(2)), text, styleNums });
  }

  process.stdout.write(JSON.stringify({ total, results }));
} finally {
  await server.close();
}

// The scene file for a shot id: `hook` -> `SceneHook`.
function sceneFile(id) {
  const map = {
    hook: 'SceneHook',
    problem: 'SceneProblem',
    browse: 'SceneBrowse',
    apply: 'SceneApply',
    multi: 'SceneMulti',
    pause: 'ScenePause',
    gpu: 'SceneGpu',
    perf: 'ScenePerf',
    quality: 'SceneQuality',
    library: 'SceneLibrary',
    close: 'SceneClose',
  };
  return map[id] || 'Scene' + id.charAt(0).toUpperCase() + id.slice(1);
}
