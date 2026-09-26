import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync } from 'node:fs';

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
      // ── the app screenshots ──────────────────────────────────────────────
      //
      // These are served from site/assets/shots with a content hash in the filename
      // now, and Vite copies them into dist/shots under the ORIGINAL name. A dist
      // that already holds an older copy keeps it, so a render after a re-capture
      // would use the previous screenshot - which happened, and the four screenshots
      // still carried a hover highlight on the minimise button after it was fixed.
      //
      // The first attempt at a fix deleted dist/shots here. That was worse than the
      // bug: writeBundle runs AFTER Vite has copied the public directory, so deleting
      // the folder removed the screenshots from the output entirely. The catalogue
      // shot then rendered as an empty dark panel with a mouse cursor in it, for the
      // whole beat - and nothing failed, because a missing image is not an error.
      //
      // So the folder is REFILLED from site/assets/shots rather than emptied. The
      // source is the single truth: whatever the site serves is what the video shows.
      const shotsOut = resolve(here, 'dist', 'shots');
      const shotsSrc = resolve(assets, 'shots');
      if (!existsSync(shotsSrc)) {
        throw new Error('site/assets/shots is missing - the video has no product images');
      }
      rmSync(shotsOut, { recursive: true, force: true });
      mkdirSync(shotsOut, { recursive: true });

      // Only the files the promo actually references, and always under the plain
      // name it asks for: the page's hashed names are for browsers, not for us.
      //
      // The extension is taken from the source rather than assumed. hero-bg is a
      // JPEG on the site (it is a still from the video, and PNG of a photograph is
      // five times the size), and writing it as `hero-bg.png` gave the renderer a
      // JPEG named .png. It happens to decode, but a file whose name lies about its
      // format is a trap for whatever reads it next.
      const wanted = ['ui-discover', 'ui-library', 'ui-displays', 'ui-performance',
                      'poster-promo', 'hero-bg', 'og-card',
                      'wallpaper-acheron', 'wallpaper-i14', 'wallpaper-raiden'];
      let copied = 0;
      for (const stem of wanted) {
        const found = readdirSync(shotsSrc).filter(
          (f) => f.startsWith(`${stem}.`) && !f.endsWith('.bak'),
        );
        if (!found.length) continue;
        // Prefer the unhashed name when both exist, then keep its own extension.
        found.sort((a, b) => a.length - b.length);
        const ext = found[0].slice(found[0].lastIndexOf('.'));
        cpSync(resolve(shotsSrc, found[0]), resolve(shotsOut, `${stem}${ext}`));
        copied++;
      }
      if (copied === 0) {
        throw new Error('no product screenshots were staged into dist/shots');
      }

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
