"""Build every tile asset the Store manifest asks for, at the size it asks for.

Why this exists
---------------
The manifest referenced two files that were the wrong size, and one that did not exist:

    Square71x71Logo="TileAssets\\Square44x44Logo.png"      a 44px file in a 71px slot
    Square310x310Logo="TileAssets\\Square150x150Logo.png"  a 150px file in a 310px slot

and `Square310x310Logo.png` itself was absent. A Store submission validates the manifest
against the package, so this is a rejection waiting to happen - and locally it shows as a
blurry or missing tile, which is easy to look past.

Every asset is derived from `Square150x150Logo.png`, which is the shipped mark: the pink
to cyan "L". Deriving from a finished asset keeps the geometry and the gradient identical
across sizes, which is what makes the Start menu, the taskbar and the Store listing look
like one product.

The scale variants are written too. Windows picks the file that matches the display's
scale factor, so a package that ships only the 100% files looks soft on every modern
laptop. Each base size gets 100/125/150/200/400, which is what the existing sets already
did - this script just does all of them, from one source, so they cannot drift apart.

Usage: python tools/make-tile-assets.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'LumaWall' / 'TileAssets'
SOURCE = ASSETS / 'Square150x150Logo.png'

# base name -> (nominal width, nominal height). These are the sizes the manifest names,
# and the sizes the Store validates against.
BASES = {
    'Square44x44Logo': (44, 44),
    'Square71x71Logo': (71, 71),
    'Square150x150Logo': (150, 150),
    'Square310x310Logo': (310, 310),
    'Wide310x150Logo': (310, 150),
    'StoreLogo': (50, 50),
    'SplashScreen': (620, 300),
    'BadgeLogo': (24, 24),
}

# The scale factors Windows looks for. 400 is for the very high-DPI panels and for the
# Store listing, which renders the tile larger than the Start menu does.
SCALES = {'': 1.0, '.scale-125': 1.25, '.scale-150': 1.5,
          '.scale-200': 2.0, '.scale-400': 4.0}

# The two assets that are not the app mark:
#   SplashScreen is the mark centred on the app's background colour;
#   BadgeLogo is a monochrome glyph shown on the lock screen, and it must be white-on-
#   transparent (Windows tints it), so it is built from the mark's alpha alone.
SPLASH_BG = (7, 8, 11, 255)     # #07080B, the same colour the manifest declares


def load_mark():
    if not SOURCE.exists():
        return None
    return Image.open(SOURCE).convert('RGBA')


def resize_contained(mark, width, height):
    """Scale the mark to fit inside width x height, centred on transparency."""
    if width == height:
        return mark.resize((width, height), Image.LANCZOS)

    # A wide tile: the mark is scaled to the height and centred horizontally, so it is
    # not stretched. Stretching a square mark into a 310x150 tile is what makes a wide
    # tile look wrong, and it is the usual mistake.
    side = height
    scaled = mark.resize((side, side), Image.LANCZOS)
    out = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    out.paste(scaled, ((width - side) // 2, 0), scaled)
    return out


def make_badge(mark, width, height):
    """A white-on-transparent badge, from the mark's shape."""
    a = np.asarray(mark.resize((width, height), Image.LANCZOS).convert('RGBA')).copy()
    # Keep the silhouette, drop the colour: Windows tints the badge itself.
    a[:, :, 0] = 255
    a[:, :, 1] = 255
    a[:, :, 2] = 255
    return Image.fromarray(a, 'RGBA')


def make_splash(mark, width, height):
    """The mark centred on the app's background colour."""
    out = Image.new('RGBA', (width, height), SPLASH_BG)
    side = int(height * 0.62)
    scaled = mark.resize((side, side), Image.LANCZOS)
    out.paste(scaled, ((width - side) // 2, (height - side) // 2), scaled)
    return out


def main():
    mark = load_mark()
    if mark is None:
        print('  missing %s - it is the source for every tile' % SOURCE)
        return 1
    print('  source: %s %dx%d' % (SOURCE.name, mark.width, mark.height))
    print()

    written = 0
    for base, (width, height) in BASES.items():
        for suffix, factor in SCALES.items():
            w = int(round(width * factor))
            h = int(round(height * factor))

            if base == 'BadgeLogo':
                img = make_badge(mark, w, h)
            elif base == 'SplashScreen':
                img = make_splash(mark, w, h)
            else:
                img = resize_contained(mark, w, h)

            out = ASSETS / ('%s%s.png' % (base, suffix))
            img.save(out)
            written += 1

        print('  %-20s %d files, %dx%d at 100%%' % (base, len(SCALES), width, height))

    print()
    print('  wrote %d files' % written)

    # Verify by reading the files back: a generator that reports success without checking
    # is how the missing 310 tile survived this long.
    print()
    print('  verifying every manifest asset exists at the size the manifest implies:')
    bad = []
    for base, (width, height) in BASES.items():
        p = ASSETS / ('%s.png' % base)
        if not p.exists():
            print('    %-22s MISSING' % base)
            bad.append(base)
            continue
        got = Image.open(p).size
        ok = got == (width, height)
        if not ok:
            bad.append(base)
        print('    %-22s %-9s want %dx%d  %s'
              % (base, '%dx%d' % got, width, height, 'ok' if ok else '<<< WRONG SIZE'))

    # Every asset must actually have visible pixels. An all-transparent tile passes a size
    # check and shows as a blank square in the Start menu.
    print()
    print('  checking each asset has visible pixels:')
    for base, (width, height) in BASES.items():
        p = ASSETS / ('%s.png' % base)
        if not p.exists():
            continue
        a = np.asarray(Image.open(p).convert('RGBA'))
        visible = (a[:, :, 3] > 32).mean()
        if visible < 0.02:
            print('    %-22s %.1f%% visible  <<< BLANK' % (base, visible * 100))
            bad.append(base)
        else:
            print('    %-22s %.1f%% visible' % (base, visible * 100))

    print()
    if bad:
        print('  FAIL %s' % ', '.join(sorted(set(bad))))
        return 1
    print('  PASS every tile the manifest names exists, at the right size, with pixels in it')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
