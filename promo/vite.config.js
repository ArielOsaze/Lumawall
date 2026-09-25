import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const site = resolve(here, '..', 'site');

// The promo shows the real product assets: the shipped app icon, the UI captures
// taken from the running application, and clean wallpaper renders. Those files
// live in the site folder, and serving that folder directly (instead of copying
// them in) means the video can never show a stale version of an asset.
//
// publicDir points at site/assets, so `./logo/app-logo.png` resolves to
// site/assets/logo/app-logo.png - the exact file the website and the MSIX use.
export default defineConfig({
  plugins: [react()],
  publicDir: resolve(site, 'assets'),
  server: {
    fs: { allow: [here, site] },
  },
  build: {
    outDir: resolve(here, 'dist'),
    emptyOutDir: true,
  },
});
