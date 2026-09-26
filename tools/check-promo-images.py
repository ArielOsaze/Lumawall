"""check-promo-images.py — every product image the promo loads actually exists.

Why this exists:

The catalogue shot rendered as an empty dark panel with a mouse cursor in it, for
the whole beat, in the finished 52-second video. Nothing failed. A missing <img>
is not an error in a browser - it draws nothing - so the render completed, every
frame check passed, and the piece went out with its main product shot blank.

The cause was a fix to a different problem: the build step cleared dist/shots to
stop a stale screenshot being reused, but the step runs AFTER Vite copies the public
directory, so it deleted the images from the output entirely.

That class of mistake is invisible from inside the render, so it has to be checked
from outside: the files the composition asks for must be on disk, and the panels in
the rendered video must contain something.

Two halves, because either alone is insufficient:

  1. STAGING - every image the scenes reference is present in the build output.
  2. RENDERED - the region of the frame where the product shot belongs is not a
     flat dark area. A panel that is genuinely empty measures as empty.

Run:  python tools/check-promo-images.py
"""

import glob
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES = os.path.join(ROOT, 'promo', 'src', 'scenes')
DIST_SHOTS = os.path.join(ROOT, 'promo', 'dist', 'shots')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video


def referenced_images():
    """Every ./shots/... path the scene sources ask for."""
    out = set()
    for path in glob.glob(os.path.join(SCENES, '*.jsx')):
        src = open(path, encoding='utf-8').read()
        for m in re.finditer(r'["\']\.?/?shots/([A-Za-z0-9._-]+\.(?:png|jpe?g))["\']', src):
            out.add(m.group(1))
    return sorted(out)


def main():
    problems = []

    # ── 1. staging ───────────────────────────────────────────────────────────
    wanted = referenced_images()
    print('  images the scenes reference: %d' % len(wanted))

    if not os.path.isdir(DIST_SHOTS):
        print()
        print('  promo/dist/shots does not exist - the build did not stage any')
        print('  product images, so every panel that shows one will be blank.')
        print('  Run: cd promo && npx vite build')
        return 1

    staged = set(os.listdir(DIST_SHOTS))
    missing = []
    for name in wanted:
        stem, ext = os.path.splitext(name)
        # The build stages under the plain name; the site may carry a hash.
        if name in staged:
            continue
        if any(s.startswith(stem + '.') for s in staged):
            continue
        missing.append(name)

    print('  staged in dist/shots: %d' % len(staged))
    for name in wanted:
        ok = name in staged or any(s.startswith(os.path.splitext(name)[0] + '.') for s in staged)
        print('    %-34s %s' % (name, 'present' if ok else 'MISSING'))
        if not ok:
            problems.append('the build did not stage %s' % name)

    # A staged file whose name lies about its format decodes anyway, but it is a
    # trap for whatever reads it next.
    for f in sorted(staged):
        p = os.path.join(DIST_SHOTS, f)
        try:
            im = Image.open(p)
            im.load()
        except Exception as e:
            problems.append('%s cannot be decoded (%s)' % (f, e))
            continue
        real = (im.format or '').lower()
        if real == 'jpeg' and f.endswith('.png'):
            problems.append('%s is a JPEG named .png' % f)

    # ── 2. the rendered panels are not blank ─────────────────────────────────
    video = promo_video()
    if not video or not os.path.exists(video):
        print()
        print('  no promo video found - cannot check the rendered panels')
        return 1 if problems else 0

    print()
    print('  checking the rendered frames:')

    os.makedirs('build/imgcheck', exist_ok=True)

    # The scenes where an app screenshot is the subject. If staging worked, that
    # region has the detail of a UI; if it did not, the region is a flat dark
    # rectangle - which is what happened once, and nothing failed, because a missing
    # image is not an error.
    #
    # The times come from the cut list. The previous version named the catalogue shot
    # at 17.0s and 19.0s, which were inside it when the piece had seven shots; after
    # the re-cut those times were in a different scene entirely.
    from shotlist import windows
    W = dict((n, (a, b)) for n, a, b in windows())

    def inside(name, frac=0.5):
        """A time inside `name`, away from either cut."""
        a, b = W[name]
        return round(a + (b - a) * frac, 1)

    # The region to sample, per scene: where the screenshot sits in that layout.
    checks = [
        ('browse',  inside('browse', 0.55),  (430, 250, 1500, 830), 8.0),
        ('apply',   inside('apply', 0.30),   (760, 300, 1780, 800), 8.0),
        ('pause',   inside('pause', 0.55),   (900, 260, 1700, 800), 8.0),
    ]

    for name, t, (x0, y0, x1, y1), min_std in checks:
        fp = 'build/imgcheck/f%05.1f.png' % t
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', video,
                        '-frames:v', '1', '-y', fp], capture_output=True)
        if not os.path.exists(fp):
            problems.append('could not read a frame at %.1fs' % t)
            continue

        a = np.asarray(Image.open(fp).convert('L')).astype(float)
        region = a[y0:y1, x0:x1]
        std = region.std()
        mean = region.mean()
        # A panel with a UI in it has structure: text edges, borders, thumbnails.
        # An empty panel is nearly uniform. 8 grey levels of deviation is a low bar
        # that a blank rectangle still fails.
        ok = std >= min_std
        print('    %-9s t=%-5s mean %5.1f  std %5.2f  %s'
              % (name, t, mean, std, 'has content' if ok else 'BLANK'))
        if not ok:
            problems.append('the %s shot is blank where the product image belongs '
                            '(t=%.1fs, std %.2f)' % (name, t, std))

    print()
    if problems:
        print('  PROBLEMS:')
        for p in problems:
            print('    ' + p)
        return 1

    print('  every referenced product image is staged and present on screen')
    return 0


if __name__ == '__main__':
    sys.exit(main())
