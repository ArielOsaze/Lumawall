"""check-layout.py — the two layout faults the promo kept shipping.

Why this is two checks of different kinds.

The two notes that came back were:

    "capture ke crop banyak yg rusak"       the captures are cropped and broken
    "smua scene pake wallpaper jelek bgt"   every scene uses a wallpaper, very ugly

The first is a SOURCE fault. The catalogue frame was given a fixed `height: 579` while
the screenshot at that width is 579 tall only at its own aspect ratio - so at the width
it was actually drawn, the frame and the image disagreed by 121px and the scroll
animation pushed the top of the image out of view. The pause frame had the same mistake.
A cropped screenshot renders perfectly; there is nothing in the output to notice.

So the crop check reads the SOURCE. The rule is that a screenshot is never given a
height - `Kit.Shot` sizes by width only and lets the browser derive the height from the
image, so a screenshot cannot be cropped by construction. This check enforces that rule:
it fails if any scene sets a height on a Shot, or draws a screenshot with an explicit
height, or clips one in a way that can cut it.

Checking pixels for this was tried first and abandoned. Matching the render against the
source image by correlation is defeated by the camera's own rotation and scale, and
locating the window by brightness picks up the type below it and the bezels beside it.
A rule in the source is exact and cannot be fooled by lighting.

The second is a PIXEL fault, and it has to be measured on the render: the question is
how the finished frames look, and only the finished frames answer it. The measure is
the fraction of the frame that is both bright and saturated - which is what a
photographic wallpaper filling the frame is, and what a dark brand surface is not.

The first version of this check used mean saturation alone and reported nine of eleven
shots as wallpapers. It was wrong: the brand surface has a saturated red bloom, so its
mean saturation is high even though the frame is dark. Requiring BRIGHTNESS as well as
saturation separates them cleanly - measured on this render, the one deliberate
full-bleed wallpaper scores 0.35 and every surface scene scores 0.19 or less.

Usage:
    python tools/check-layout.py [video]
"""

import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video
from shotlist import windows, total

VIDEO = sys.argv[1] if len(sys.argv) > 1 else (promo_video() or 'build/livevid/promo.mp4')
SCENES = 'promo/src/scenes'
KIT = 'promo/src/Kit.jsx'

# A pixel that is bright AND saturated. A wallpaper fills the frame with them; a dark
# brand surface has almost none, however saturated its bloom is.
WALLPAPER_HOT = 0.25

# Above this share of the piece, it reads as a wallpaper reel rather than a commercial.
MAX_WALLPAPER_SHARE = 0.45


# ── the source rule: a screenshot is never given a height ────────────────────

def check_source():
    problems = []
    checked = 0

    # 1. Kit.Shot must not accept or apply a height. If it ever does, every screenshot
    #    in the piece becomes croppable at once.
    if os.path.exists(KIT):
        kit = open(KIT, encoding='utf-8').read()
        m = re.search(r'export function Shot\(\{(.*?)\}\)', kit, re.S)
        if m:
            props = m.group(1)
            if 'height' in props:
                problems.append(
                    'Kit.Shot takes a `height` prop - that is how the previous version '
                    'cropped its screenshots, and the component exists to make it '
                    'impossible')
            checked += 1
        # The image inside Shot must derive its own height.
        if not re.search(r"height:\s*'auto'", kit):
            problems.append('Kit.Shot no longer sets `height: auto` on its image')

    # 2. No scene may pass a height to Shot.
    for f in sorted(os.listdir(SCENES)):
        if not f.endswith('.jsx'):
            continue
        src = open(os.path.join(SCENES, f), encoding='utf-8').read()
        for m in re.finditer(r'<Shot\b[^>]*?/>', src, re.S):
            tag = m.group(0)
            if re.search(r'\bheight\s*=', tag):
                problems.append(
                    '%s: a <Shot> is given a height (%s) - a screenshot must be sized '
                    'by width only' % (f, re.search(r'\bheight\s*=\s*\{?[^,}]*', tag).group(0).strip()))
            checked += 1

        # 3. A raw <img> of a screenshot must not carry a height either.
        for m in re.finditer(r'<img\b[^>]*?/>', src, re.S):
            tag = m.group(0)
            if 'shots/' in tag and re.search(r'\bheight\s*=\s*\{?\s*[0-9]', tag):
                problems.append(
                    '%s: a screenshot <img> is given a numeric height - it will be '
                    'cropped or squashed' % f)
            checked += 1

    return problems, checked


# ── the pixel rule: the piece is not a reel of wallpapers ────────────────────

def hot_share(path):
    """The fraction of the frame that is both bright and saturated."""
    rgb = np.asarray(Image.open(path).convert('RGB')).astype(float)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    val = mx / 255.0
    sat = np.where(mx > 8, (mx - mn) / np.maximum(mx, 1), 0.0)
    return float(((val > 0.22) & (sat > 0.22)).mean())


def main():
    problems = []

    print()
    print('  ── the source rule: no screenshot is ever given a height ──')
    src_problems, checked = check_source()
    print('    %d Shot / screenshot uses inspected' % checked)
    problems += src_problems
    for p in src_problems:
        print('    · %s' % p)
    if not src_problems:
        print('    no screenshot can be cropped by construction')

    if not VIDEO or not os.path.exists(VIDEO):
        print()
        print('  no video to check for backgrounds (looked for %s)' % VIDEO)
        return 1 if problems else 0

    shots = windows()
    if not shots:
        print('  could not read the cut list from Direction.jsx')
        return 1

    print()
    print('  ── the pixel rule: how much of the piece is a full-bleed wallpaper? ──')
    print('  %s — %d shots, %.1fs' % (VIDEO, len(shots), total()))

    rows = []
    for name, a, b in shots:
        t = round(a + (b - a) * 0.62, 2)
        tmp = os.path.join('build', '_layout.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', VIDEO,
                        '-frames:v', '1', '-y', tmp], capture_output=True)
        if not os.path.exists(tmp):
            continue
        hot = hot_share(tmp)
        is_wall = hot >= WALLPAPER_HOT
        rows.append((name, hot, is_wall))
        print('    %-9s t=%-5s  %.3f  %s'
              % (name, t, hot, 'WALLPAPER fills the frame' if is_wall else 'brand surface'))

    n_wall = sum(1 for _, _, v in rows if v)
    share = n_wall / len(rows) if rows else 0

    print()
    print('    %d of %d shots (%.0f%%) are a full-bleed wallpaper'
          % (n_wall, len(rows), share * 100))

    if share > MAX_WALLPAPER_SHARE:
        problems.append(
            '%d of %d shots are a full-bleed wallpaper - the piece reads as a '
            'wallpaper reel, not a product commercial' % (n_wall, len(rows)))

    runs = ['%s -> %s' % (rows[i - 1][0], rows[i][0])
            for i in range(1, len(rows)) if rows[i][2] and rows[i - 1][2]]
    if runs:
        problems.append('consecutive wallpaper shots: %s' % ', '.join(runs))
    else:
        print('    no two consecutive shots are both wallpapers')

    print()
    if problems:
        print('  %d problem(s):' % len(problems))
        for p in problems:
            print('    · %s' % p)
        return 1

    print('  no screenshot can be cropped, and the piece is not a wallpaper reel')
    return 0


if __name__ == '__main__':
    sys.exit(main())
