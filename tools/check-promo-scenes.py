"""check-promo-scenes.py — does every beat of the promo have something in it?

Why this was rewritten:

This check used to ask "is a wallpaper visible in every beat", and it failed a beat
whose mean brightness was under 14 - on the reasoning that a dark beat is a black
slide. That was the right question for a promo in which every scene WAS a wallpaper.
It is the wrong question now, and worse than wrong: it would fail the deliberate
design.

The piece now shows the app, not the wallpaper. Most scenes sit on a dark brand
surface with a lit app panel in the middle, so their mean brightness is legitimately
low - and the check would have reported a correctly-designed scene as broken while
passing a wallpaper that had nothing to say.

What actually matters is whether the beat has CONTENT: structure in the frame, which
is what a viewer reads. A blank slide has no structure - it is a flat field, whatever
its brightness. A scene with an app panel, a pipeline diagram or a measured figure has
a lot, even when it is dark.

So the measurement is the standard deviation of the frame across the whole width,
which is high wherever there are edges, panels, type or a photograph, and near zero
on a flat field. Measured on this material: scenes run 26-58, a flat field is under 8.

Usage:
    python tools/check-promo-scenes.py [video]
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video
from shotlist import windows as shot_windows

VIDEO = sys.argv[1] if len(sys.argv) > 1 else (promo_video() or 'site/assets/video/lumawall-promo.mp4')

# The shot windows come from Direction.jsx, so this can never describe a cut list
# that no longer exists. It used to carry its own copy, and a stale copy does not
# fail - it samples the wrong moments and reports about a piece that is not there.
BEATS = shot_windows()

# The whole frame, downsampled. Sampling a band rather than a corner: a corner is
# often legitimately dark (vignettes, letterboxed art) and produced false readings.
CROP = 'scale=160:90,format=gray'

# A frame with structure. Under this the beat is a flat field - a blank slide.
MIN_STRUCTURE = 8.0


def structure(t0, t1):
    """Mean frame-to-frame standard deviation across a beat, and the frame count."""
    r = subprocess.run(
        ['ffmpeg', '-v', 'error', '-ss', str(t0), '-t', str(t1 - t0),
         '-i', VIDEO, '-vf', 'fps=2,' + CROP, '-f', 'rawvideo', '-'],
        capture_output=True,
    )
    raw = r.stdout
    size = 160 * 90
    n = len(raw) // size
    if n == 0:
        return None, None, 0

    devs = []
    means = []
    for i in range(n):
        block = raw[i * size:(i + 1) * size]
        m = sum(block) / size
        var = sum((b - m) ** 2 for b in block) / size
        means.append(m)
        devs.append(var ** 0.5)
    return sum(devs) / len(devs), sum(means) / len(means), n


def main():
    if not VIDEO or not os.path.exists(VIDEO):
        print('  no video to check (looked for %s)' % VIDEO)
        return 1

    print('  beat        window        structure   mean   frames   verdict')
    fails = 0
    for name, t0, t1 in BEATS:
        sd, mean, n = structure(t0, t1)
        if sd is None:
            print('  %-10s  %4.1f-%4.1fs   no frames decoded' % (name, t0, t1))
            fails += 1
            continue

        if sd >= 22:
            verdict = 'has content'
        elif sd >= MIN_STRUCTURE:
            verdict = 'sparse but present'
        else:
            verdict = 'FLAT - reads as a blank slide'
            fails += 1

        print('  %-10s  %4.1f-%4.1fs  %8.1f  %5.1f  %6d   %s'
              % (name, t0, t1, sd, mean, n, verdict))

    print()
    if fails:
        print('  %d beat(s) render as a flat field - they have nothing in them.' % fails)
        return 1
    print('  every beat has content in it')
    return 0


if __name__ == '__main__':
    sys.exit(main())
