"""Measure the catalogue grid: are the tiles showing pictures?

Why this exists
---------------
The complaint was "kenapa di catalog ada bbrp wallpaper yg cuma item" - some tiles are
just black. Counting dark pixels over the whole window is useless, because the app is
dark-themed and the sidebar alone drags the number up. What matters is the content of
each TILE, so this finds the tile rectangles and measures the variation inside each one.

A tile with a picture has many distinct colours and a wide spread. An empty tile is flat.
A placeholder tile has the app's own surface colour plus one small glyph, so it is nearly
flat - which is why this reports it separately rather than as "has an image".

Usage: python tools/check-catalog-tiles.py <shot.png>
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def tiles_in(img):
    """Find the grid tiles by their borders, and return their boxes.

    The grid is the region right of the nav rail and left of the detail panel. Tiles are
    separated by the page background, so the columns of "not background" give the spans.
    """
    a = np.asarray(img.convert('RGB')).astype(np.int16)
    h, w, _ = a.shape

    # The content column: past the 76px nav rail, before the ~380px detail panel.
    x0, x1 = int(w * 0.055), int(w * 0.76)
    y0, y1 = int(h * 0.40), int(h * 0.96)
    band = a[y0:y1, x0:x1]

    # A tile is brighter than the page background, which is nearly black (#000-ish).
    lum = band.mean(axis=2)
    occupied = lum > 18

    cols = occupied.mean(axis=0)
    rows = occupied.mean(axis=1)

    def spans(profile, frac=0.35):
        on = profile > frac
        out, start = [], None
        for i, v in enumerate(on):
            if v and start is None:
                start = i
            elif not v and start is not None:
                if i - start > 30:
                    out.append((start, i))
                start = None
        if start is not None and len(on) - start > 30:
            out.append((start, len(on)))
        return out

    cs = spans(cols)
    rs = spans(rows)
    return [(x0 + c0, y0 + r0, x0 + c1, y0 + r1) for r0, r1 in rs for c0, c1 in cs]


def classify(img, box):
    """(has_picture, spread, colours) for one tile."""
    x0, y0, x1, y1 = box
    # Inset so the border and the badge do not count.
    pad_x = max(2, (x1 - x0) // 14)
    pad_y = max(2, (y1 - y0) // 14)
    a = np.asarray(img.convert('RGB').crop((x0 + pad_x, y0 + pad_y, x1 - pad_x, y1 - pad_y)))
    if a.size == 0:
        return False, 0.0, 0
    # Ignore the caption strip at the bottom of the card.
    a = a[: int(a.shape[0] * 0.72)]
    flat = a.reshape(-1, 3)
    lum = flat.mean(axis=1)
    spread = float(np.percentile(lum, 92) - np.percentile(lum, 8))
    # Distinct colours, coarsely quantised so a photograph scores high and a flat
    # surface with a single glyph does not.
    q = (flat // 24).astype(np.int32)
    colours = len(np.unique(q[:, 0] * 10000 + q[:, 1] * 100 + q[:, 2]))
    return (spread > 42 and colours > 60), spread, colours


def main():
    shot = Path(sys.argv[1] if len(sys.argv) > 1 else 'build/catalog-final.png')
    img = Image.open(shot)
    boxes = tiles_in(img)
    if not boxes:
        print('  no tiles found in %s' % shot)
        return 1

    pics = empty = 0
    for b in boxes:
        has, spread, colours = classify(img, b)
        if has:
            pics += 1
        else:
            empty += 1
            print('    FLAT  %-24s spread %5.1f  colours %4d' % (str(b), spread, colours))

    total = len(boxes)
    print()
    print('  tiles        : %d' % total)
    print('  with a picture: %d (%.0f%%)' % (pics, 100.0 * pics / total))
    print('  flat / empty : %d' % empty)
    return 0 if empty == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
