import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { cpSync, existsSync, rmSync, readdirSync } from 'node:fs';

const here = dirname(fileURLToPath(import.meta.url));
const site = resolve(here, '..', 'site');
const frames = resolve(here, 'frames');
const assets = resolve(site, 'assets');

// The promo shows the real product assets: the shipped app icon, the UI captures
// taken from the running application, and the wallpaper clips. Serving the site's
// asset folder directly (instead of copying it in) means the video can never show
// a stale version of an asset.
//
// The wallpaper frame sequences are the exception: they live in promo/frames
// because they are 13 MB of intermediate render data that has no business on the
// public site. A build hook copies them into the output so the renderer can load
// them, and they never touch site/.
function stageFrames() {
  return {
    name: 'stage-wallpaper-frames',
    apply: 'build',
    // `writeBundle` runs AFTER Vite has written the output. `buildStart` runs
    // before it, and `emptyOutDir` then deletes whatever was copied there — the
    // frames silently vanished and the renderer found 0/240 of them.
    writeBundle() {
      // The app screenshots are served from site/assets/shots with a content hash in
      // the filename now. Vite copies them into dist/shots under the ORIGINAL name,
      // and a dist that already holds an older copy keeps it - so a render after a
      // re-capture would use the previous screenshot. That happened: the four
      // screenshots carried a hover highlight on the minimise button, and the copy in
      // dist still had it after the fix. Clearing the folder makes the render always
      // take what is in site/ right now.
      const shots = resolve(here, 'dist', 'shots');
      rmSync(shots, { recursive: true, force: true });

      const out = resolve(here, 'dist', 'frames');
      if (!existsSync(frames)) {
        throw new Error('promo/frames is missing. Run: python tools/extract-clips.py');
      }
      rmSync(out, { recursive: true, force: true });
      cpSync(frames, out, { recursive: true });
      const n = existsSync(out) ? readdirSync(out).length : 0;
      if (n === 0) throw new Error('staging wallpaper frames produced nothing');
    },
  };
}

export default defineConfig({
  plugins: [react(), stageFrames()],
  publicDir: assets,
  server: {
    fs: { allow: [here, site] },
  },
  build: {
    outDir: resolve(here, 'dist'),
    emptyOutDir: true,
  },
});
