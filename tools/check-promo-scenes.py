"""check-promo-scenes.py — is a wallpaper visible in every beat of the promo?

The whole subject of the video is a moving wallpaper, so a beat that renders as a
plain black slide is a failure. This samples a band across the frame (not just one
corner, which is often legitimately dark) and reports the brightness of each beat.

Run:  python tools/check-promo-scenes.py site/assets/video/lumawall-promo.mp4
"""

import subprocess
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video
VIDEO = sys.argv[1] if len(sys.argv) > 1 else (promo_video() or 'site/assets/video/lumawall-promo.mp4')

# Beat windows, taken from Timeline.jsx.
BEATS = [
    ('intro',    0.0,   7.0),
    ('problem',  7.0,  14.0),
    ('catalog', 14.0,  21.0),
    ('monitors', 21.0, 29.0),
    ('pause',   29.0,  37.0),
    ('perf',    37.0,  44.0),
    ('outro',   44.0,  52.0),
]

# The upper two-thirds of the frame, sampled across its whole width. A single
# corner is often legitimately dark (vignettes, letterboxed art) and produced a
# false "this beat is black" reading before.
CROP = 'crop=1200:400:120:120,scale=80:27,format=gray'


def mean_brightness(t0, t1):
    r = subprocess.run(
        ['ffmpeg', '-v', 'error', '-ss', str(t0), '-t', str(t1 - t0),
         '-i', VIDEO, '-vf', 'fps=2,' + CROP, '-f', 'rawvideo', '-'],
        capture_output=True,
    )
    raw = r.stdout
    size = 80 * 27
    n = len(raw) // size
    if n == 0:
        return None, 0
    means = [sum(raw[i * size:(i + 1) * size]) / size for i in range(n)]
    return sum(means) / len(means), n


print('  beat        window      mean   frames   verdict')
fails = 0
for name, t0, t1 in BEATS:
    m, n = mean_brightness(t0, t1)
    if m is None:
        print('  %-10s  %4.0f-%4.0fs   no frames decoded' % (name, t0, t1))
        fails += 1
        continue
    if m >= 20:
        verdict = 'wallpaper visible'
    elif m >= 14:
        verdict = 'dim but present'
    else:
        verdict = 'TOO DARK - reads as a black slide'
        fails += 1
    print('  %-10s  %4.0f-%4.0fs  %5.1f  %6d   %s' % (name, t0, t1, m, n, verdict))

print()
if fails:
    print('  %d beat(s) need a brighter wallpaper layer.' % fails)
    sys.exit(1)
print('  every beat shows a wallpaper')
