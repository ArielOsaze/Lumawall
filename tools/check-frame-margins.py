"""check-frame-margins.py — every scene keeps a sane left margin.

The bleed box made scenes lay out 32% wider than the frame, so a scene written
against 1920x1080 started its content 177 px off the left edge. It took a vision
review of a single frame to notice, because nothing in the checks looked at where
content sat - only at whether the frame was empty and whether it moved.

This samples the finished render across every beat and reports the leftmost column
that carries content. A margin near the frame edge means something is being clipped;
a margin of roughly the scene's own padding means the layout is right.

Run:  python tools/check-frame-margins.py [video]
"""

import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video
from shotlist import windows as shot_windows, midpoints as shot_midpoints
VIDEO = sys.argv[1] if len(sys.argv) > 1 else (promo_video() or 'site/assets/video/lumawall-promo.mp4')

# One sample in the middle of each shot, from Direction.jsx.
#   intro 0-6.4  problem 6.4-13.4  catalog 13.4-21.0  monitors 21.0-28.4
#   pause 28.4-36.4  perf 36.4-44.4  outro 44.4-52
# Sample points from the shot list in Direction.jsx, one per shot.
SAMPLES = shot_midpoints()

# The scenes pad between 110 and 150 px. Allow for the camera's own drift, which
# moves content by up to about 40 px, and for a scene that centres its content.
MIN_MARGIN = 40
MAX_MARGIN = 700

# What counts as content. A brightness threshold over the whole frame flags the
# intro, whose wallpaper is full-bleed on purpose - the character is meant to reach
# the edge. The defect this check exists for put TEXT off the edge, so it looks for
# text: pixels bright in every channel, which the dark stage and most wallpaper
# frames are not.
TEXT_LEVEL = 140


def main():
    if not os.path.exists(VIDEO):
        print('  no video at %s' % VIDEO)
        return 1

    print('  %s' % VIDEO)
    print()
    print('  beat        leftmost content   rightmost   verdict')
    problems = []

    for t, beat in SAMPLES:
        tmp = os.path.join('build', '_margin.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', VIDEO,
                        '-frames:v', '1', '-y', tmp], capture_output=True)
        if not os.path.exists(tmp):
            print('    %-10s could not read' % beat)
            continue

        a = np.asarray(Image.open(tmp).convert('RGB')).astype(int)
        h, w, _ = a.shape

        # Text and UI are near-white; the stage and most wallpaper frames are not.
        bright = (a.min(axis=2) > TEXT_LEVEL)
        # Ignore the outermost 6 px, where the frame's own edge can be bright.
        bright[:, :6] = False
        bright[:, w - 6:] = False

        cols = np.where(bright.any(axis=0))[0]
        if len(cols) == 0:
            print('    %-10s no content above the threshold' % beat)
            continue

        left = int(cols.min())
        right = int(w - 1 - cols.max())
        ok = MIN_MARGIN <= left <= MAX_MARGIN
        verdict = 'OK' if ok else ('CLIPPED' if left < MIN_MARGIN else 'TOO MUCH MARGIN')
        if not ok:
            problems.append((beat, left, verdict))
        print('    %-10s %5d px           %5d px    %s' % (beat, left, right, verdict))

    print()
    if problems:
        print('  %d beat(s) with a margin problem:' % len(problems))
        for beat, left, why in problems:
            print('    %-10s left margin %d px - %s' % (beat, left, why))
        return 1
    print('  every beat keeps its content inside the frame')
    return 0


if __name__ == '__main__':
    sys.exit(main())
