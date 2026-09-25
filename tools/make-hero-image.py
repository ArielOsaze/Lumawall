"""make-hero-image.py — composes a hero background for the hero's own aspect ratio.

Why not crop a wallpaper with object-fit:

  The wallpapers are 16:9 stills of a character. The hero is a wide, short band.
  Covering one with the other crops the character at an arbitrary point, and
  `object-position` can only choose which arbitrary point - it cannot move the
  subject somewhere better, and it cannot darken one side for the type while
  leaving the other side bright.

  A hero image should be composed for the hero: the subject in the right third,
  clear of the headline, with the left side falling to near-black so white text
  sits on it without a heavy overlay on top of the artwork.

Run:  python tools/make-hero-image.py
"""

import os
import subprocess
import sys

OUT = 'site/assets/shots/hero-bg.jpg'

# 2400x1200 covers a 2x display at 1200 CSS pixels wide, and stays wide enough
# that a crop at 1440x900 or 2560x1080 both keep the subject.
W, H = 2400, 1200

SOURCE = 'site/assets/shots/wallpaper-raiden.png'
if not os.path.exists(SOURCE):
    sys.exit('missing %s' % SOURCE)

# The left-hand darkening has to be a gradient, not a box.
#
# A first attempt used drawbox, which is a hard-edged rectangle: it left a
# visible vertical seam down the middle of the artwork. A `geq` ramp on the
# alpha channel produces a smooth falloff instead, so there is no edge to see.
#
# `geq` is evaluated per pixel, so it is slow, but this runs once.
#   lum(lum(X)) gives a 0..1 ramp left-to-right; the power curve keeps the left
#   side dark for longer and clears quickly towards the right.
darken = (
    f"format=rgba,"
    f"geq="
    f"r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
    f"a='255*(0.30+0.70*pow(min(1,max(0,X/{int(W * 0.62)})),1.7))'"
)

filter_chain = (
    # 1. fit to the hero's aspect, anchored right so the character stays right
    f'scale={W}:{H}:force_original_aspect_ratio=increase,'
    f'crop={W}:{H}:(iw-{W})*0.74:0,'
    # 2. grade: slightly cooler, a touch more contrast
    'eq=brightness=-0.03:contrast=1.10:saturation=1.02,'
    # 3. the left-to-right darkening, as a smooth ramp
    + darken + ','
    # 4. vignette to close the corners
    'vignette=PI/4.5,format=rgb24'
)

cmd = [
    'ffmpeg', '-v', 'error', '-y',
    '-i', SOURCE,
    '-vf', filter_chain,
    '-q:v', '3',
    OUT,
]

print('  composing the hero image...')
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print('  ffmpeg failed:')
    print('   ', r.stderr.strip()[:700])
    sys.exit(1)

print('  %s  (%d bytes, %dx%d)' % (OUT, os.path.getsize(OUT), W, H))
