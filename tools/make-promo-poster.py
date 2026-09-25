"""make-promo-poster.py — the video's poster frame, taken from the video itself.

The old poster was a three-panel collage of wallpaper stills with no product in it.
A reviewer's verdict was blunt and correct: "too generic, no branding, no hint of
the product - it functions as a decorative background rather than a promotional
tool". The video block autoplays, so the poster is what a visitor sees before the
first frame decodes, and it is what they see for the whole time they are on the page
if autoplay is blocked. It has to say what the product is.

The right source is the video. Taking the frame from the finished render also means
the still and the video can never disagree about the product's appearance.

Run:  python tools/make-promo-poster.py
"""

import os
import subprocess
import sys

from PIL import Image

VIDEO = 'site/assets/video/lumawall-promo.mp4'
OUT = 'site/assets/shots/poster-promo.png'

# The beats, from Timeline.jsx:
#   intro 0.0-6.4   problem 6.4-13.6   catalog 13.6-21.4   monitors 21.4-29.4
#   pause 29.4-38.2   perf 38.2-45.4   outro 45.4-52
# A poster has to show the product working, so the app and monitor beats are the
# candidates. The monitor beat is the product's whole point: several screens, each
# with its own wallpaper.
CANDIDATES = [
    (25.0, 'monitors', 'three screens, three wallpapers'),
    (26.5, 'monitors', 'later in the beat, camera settled'),
    (27.5, 'monitors', 'near the end of the beat'),
    (17.0, 'catalog',  'the app UI with its wallpaper grid'),
    (33.0, 'pause',    'the app with the pause state visible'),
]


def grab(t):
    tmp = os.path.join('build', '_poster_frame.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', VIDEO,
                    '-frames:v', '1', '-y', tmp], capture_output=True)
    return Image.open(tmp).convert('RGB') if os.path.exists(tmp) else None


def main():
    if not os.path.exists(VIDEO):
        print('  no video at %s' % VIDEO)
        return 1

    print('  candidate frames from the finished render:')
    frames = []
    for t, beat, why in CANDIDATES:
        im = grab(t)
        if im is None:
            print('    t=%-5s could not read' % t)
            continue
        small = im.resize((160, 90))
        px = list(small.getdata())
        mean = sum(sum(c) for c in px) / (len(px) * 3)
        # How much of the frame is not near-black? A poster that is mostly black
        # reads as an empty box in a link preview.
        lit = sum(1 for c in px if sum(c) > 90) / len(px)
        frames.append((t, beat, why, im, mean, lit))
        print('    t=%-5s %-9s brightness %5.1f  lit %3.0f%%  %s'
              % (t, beat, mean, lit * 100, why))

    if not frames:
        print('  no frames could be read')
        return 1

    # Prefer the monitor beat: it shows the product doing the thing the page claims,
    # and it is bright enough to work as a thumbnail. Fall back to the brightest
    # frame if that beat is not readable.
    pick = next((f for f in frames if f[1] == 'monitors' and 25 < f[4] < 140), None)
    if pick is None:
        pick = max(frames, key=lambda f: f[5])
    t, beat, why, im, mean, lit = pick

    im.save(OUT)
    print()
    print('  poster written: %s' % OUT)
    print('    from t=%.1fs, the %s beat - %s' % (t, beat, why))
    print('    %dx%d, %d bytes' % (im.width, im.height, os.path.getsize(OUT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
