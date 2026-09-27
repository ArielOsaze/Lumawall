"""Build the 71x71 tile assets from the 150x150 one.

Why this exists
---------------
The Square71x71Logo set was created while the app briefly carried a different mark, and
that mark is not the one the project ships: the shipped logo is the pink-to-cyan "L".
Restoring the other tile sizes from git therefore left these five files showing the wrong
mark - the website was correct while the Start menu tile was not, which is exactly the
kind of thing a build hides.

The 150x150 asset IS the shipped mark, so the small tile is derived from it rather than
redrawn. Scaling down a finished asset keeps the geometry and the gradient identical to
the sizes that already match.

Usage: python tools/make-71-tiles.py
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'LumaWall' / 'TileAssets' / 'Square150x150Logo.png'
OUT = ROOT / 'LumaWall' / 'TileAssets'

# The scale suffixes Windows looks for, and the pixel size each one means.
SCALES = {
    '': 71,
    '.scale-125': 89,   # 71 * 1.25
    '.scale-150': 107,  # 71 * 1.5
    '.scale-200': 142,  # 71 * 2
    '.scale-400': 284,  # 71 * 4
}


def main():
    if not SRC.exists():
        print('  missing %s' % SRC)
        return 1

    src = Image.open(SRC).convert('RGBA')
    print('  source: %s %dx%d' % (SRC.name, src.width, src.height))

    # The 150 tile has a little padding around the mark; keep it, so every tile in the
    # set has the same optical size in the Start menu.
    for suffix, size in SCALES.items():
        out = OUT / ('Square71x71Logo%s.png' % suffix)
        src.resize((size, size), Image.LANCZOS).save(out)
        print('  wrote %-34s %dx%d' % (out.name, size, size))

    # Verify: the shipped mark is the only one with cyan in it.
    import numpy as np
    for suffix in SCALES:
        p = OUT / ('Square71x71Logo%s.png' % suffix)
        a = np.asarray(Image.open(p).convert('RGBA'))
        vis = a[a[:, :, 3] > 128]
        if not len(vis):
            print('  %-34s EMPTY' % p.name)
            return 1
        lum = vis[:, :3].mean(axis=1)
        mark = vis[lum > (lum.mean() + 15)]
        cyan = ((np.abs(mark[:, 0].astype(int) - 121) < 55)
                & (np.abs(mark[:, 1].astype(int) - 232) < 45)
                & (np.abs(mark[:, 2].astype(int) - 252) < 45)).sum()
        ok = 'carries the shipped mark' if cyan > 0 else '*** WRONG MARK ***'
        print('  %-34s cyan %5d  %s' % (p.name, cyan, ok))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
