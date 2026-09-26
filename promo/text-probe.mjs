// text-probe.mjs — every string of text the promo actually draws, per scene.
//
// Why this exists:
//
// The promo is being given an English version, so every piece of text in it has to be
// found. Reading it out of the scene sources by hand misses the strings that are
// assembled at render time (a template literal, a value inside an array that is mapped
// over) and the ones that differ between a scene's variants.
//
// So this renders every scene, at several moments, in every variant, and reads back
// every text node in the DOM - which is exactly what the renderer will draw, with
// nothing missed and nothing invented.
//
// It also returns the text grouped by scene, so the translation table can be built
// per scene rather than as one flat list with no context.

import { createServer } from 'vite';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const here = dirname(fileURLToPath(import.meta.url));

// Which language to read the text in. The scenes read `window.__lang` at render time,
// and this probe runs in node with no window - so the global is set before the modules
// are loaded, which is what the renderer does with a page script.
const LANG = process.env.PROMO_LANG || 'id';
globalThis.window = { __lang: LANG };

const SCENE_FILES = {
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

const server = await createServer({
  root: here,
  logLevel: 'error',
  server: { middlewareMode: true },
  appType: 'custom',
});

try {
  const dir = await server.ssrLoadModule('/src/Direction.jsx');
  const total = dir.TOTAL_SECONDS;
  const shots = dir.SHOTS;

  const out = {};

  for (let i = 0; i < shots.length; i++) {
    const id = shots[i].id;
    const cut = shots[i].cut;
    const end = i + 1 < shots.length ? shots[i + 1].cut : total;

    const mod = await server.ssrLoadModule(`/src/scenes/${SCENE_FILES[id]}.jsx`);
    const C = mod.default;

    const strings = new Set();

    // Both variants, and several moments: a scene's text arrives over its shot, and
    // variant 1 changes the names in some of them.
    for (const variant of [0, 1]) {
      for (const frac of [0.15, 0.5, 0.9]) {
        const local = (end - cut) * frac;
        const t = cut + local;

        let html;
        try {
          html = renderToStaticMarkup(
            React.createElement(C, { t: local, global: t, start: cut, end: total, variant }),
          );
        } catch (e) {
          strings.add('!! ERROR: ' + (e && e.message ? e.message : String(e)));
          continue;
        }

        const text = html
          .replace(/<[^>]*>/g, '\u0001')
          .split('\u0001')
          .map((x) => x.trim())
          .filter((x) => x.length > 0);

        for (const s of text) strings.add(s);
      }
    }

    out[id] = Array.from(strings).sort();
  }

  process.stdout.write(JSON.stringify(out, null, 1));
} finally {
  await server.close();
}
