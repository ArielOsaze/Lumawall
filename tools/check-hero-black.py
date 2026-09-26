"""check-hero-black.py — the hero's black side is flat, like the wallpaper's.

Why this exists:

The visitor said "kok masih ada bayangannya? ga full item kan di wallpaper asli full
hitam" - there is still a shadow, the original wallpaper is fully black. They were
right, and the cause was two gradients added on top of a wallpaper that did not need
them:

  1. make-hero-loop.py baked a per-pixel alpha ramp into the left 58% of the video,
     to darken it for white type. That was right for the previous hero (Acheron,
     left side 92/255) and wrong for this one (Girl Behind Curtains, 3/255).
  2. style.css laid a 90deg gradient over the same area for the same reason.

Darkening near-black is where banding appears. Eight-bit colour has only a handful of
distinct values between 0 and 8, so a ramp across 1100 px shows as visible steps -
which is what "bayangan" describes when you look at it closely.

The check is a comparison, not a threshold: the hero's black must match the
wallpaper's own black. A threshold would pass a hero that is black for a different
reason than the artwork, and the point is that the page shows the product as the app
shows it.

Run:  python tools/check-hero-black.py
"""

import glob
import os
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLPAPERS = os.path.join(os.path.expandvars(r'%LOCALAPPDATA%'), 'LumaWall', 'Wallpapers')

# The wallpaper the hero is composed from. Kept in sync with make-hero-loop.py.
SOURCE_NAME = 'Girl Behind Curtains.mp4'

# The left share of the frame the headline sits on. The hero is composed with the
# subject in the right third, so this is the region that must be flat.
LEFT_SHARE = 0.55

# How much the hero's black may differ from the wallpaper's own black. A couple of
# levels covers the video encode; anything more means something was added.
TOLERANCE = 4.0


def left_stats(a, share):
    """Mean and spread of the darkest 20% of the left region."""
    h, w, _ = a.shape
    region = a[:, :int(w * share)].reshape(-1, 3)
    lum = region.mean(axis=1)
    dark = region[lum <= np.percentile(lum, 20)]
    return dark.mean(axis=0), dark.std(axis=0).mean()


def main():
    problems = []

    # ── the wallpaper, as the app plays it ───────────────────────────────────
    src = os.path.join(WALLPAPERS, SOURCE_NAME)
    if not os.path.exists(src):
        print('  cannot find the hero wallpaper at %s' % src)
        print('  (set SOURCE_NAME in this file to match make-hero-loop.py)')
        return 1

    os.makedirs('build/heroblack', exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-ss', '4', '-i', src,
                    '-frames:v', '1', '-y', 'build/heroblack/source.png'],
                   capture_output=True)
    source = np.asarray(Image.open('build/heroblack/source.png').convert('RGB')).astype(float)
    s_mean, s_spread = left_stats(source, LEFT_SHARE)

    print('  wallpaper: %s' % SOURCE_NAME)
    print('    left %d%%: mean %s  spread %.2f'
          % (LEFT_SHARE * 100, s_mean.round(1), s_spread))

    # ── the hero the page actually serves ────────────────────────────────────
    posters = sorted(glob.glob(os.path.join(ROOT, 'site', 'assets', 'shots', 'hero-bg.*.jpg')))
    if not posters:
        print('  no hero poster found - run: python tools/make-hero-loop.py')
        return 1

    hero_path = posters[0]
    hero = np.asarray(Image.open(hero_path).convert('RGB')).astype(float)
    h_mean, h_spread = left_stats(hero, LEFT_SHARE)

    print('  hero: %s' % os.path.basename(hero_path))
    print('    left %d%%: mean %s  spread %.2f'
          % (LEFT_SHARE * 100, h_mean.round(1), h_spread))

    # ── the hero's black must BE the wallpaper's black ───────────────────────
    delta = float(np.abs(h_mean - s_mean).max())
    print()
    print('  difference from the wallpaper: %.2f levels (allowed %.1f)' % (delta, TOLERANCE))
    if delta > TOLERANCE:
        problems.append('the hero\'s black is %.1f levels away from the wallpaper\'s - '
                        'something was added to it' % delta)

    # ── and it must be FLAT, not a ramp ──────────────────────────────────────
    #
    # A gradient across a near-black region shows as visible steps. Measure how much
    # the value changes from the left edge to the middle of the black area: a flat
    # black changes by almost nothing, a ramp changes by several levels.
    h, w, _ = hero.shape
    strip_y = int(h * 0.25)
    edge = hero[strip_y, :int(w * 0.04)].mean(axis=0)
    mid = hero[strip_y, int(w * 0.45):int(w * 0.52)].mean(axis=0)
    ramp = float(np.abs(mid - edge).max())
    print('  ramp across the black: %.2f levels (a flat black is under 3)' % ramp)
    if ramp > 3.0:
        problems.append('the black side ramps by %.1f levels - that is a gradient, '
                        'and a gradient in near-black shows as banding' % ramp)

    print()
    if problems:
        for p in problems:
            print('  ' + p)
        print()
        print('  The hero must show the wallpaper as the app shows it. Do not darken')
        print('  a wallpaper that is already black: the type sits on it either way, and')
        print('  the gradient is what the visitor sees as a shadow.')
        return 1

    print('  the hero\'s black matches the wallpaper and is flat')
    return 0


if __name__ == '__main__':
    sys.exit(main())
