"""make-promo-poster.py — the video's poster frame, taken from the video itself.

The old poster was a three-panel collage of wallpaper stills with no product in it.
A reviewer's verdict was blunt and correct: "too generic, no branding, no hint of
the product - it functions as a decorative background rather than a promotional
tool". The video block autoplays, so the poster is what a visitor sees before the
first frame decodes, and it is what they see for the whole time they are on the page
if autoplay is blocked. It has to say what the product is.

The right source is the video. Taking the frame from the finished render also means
the still and the video can never disagree about the product's appearance.

Run:  python tools/make-promo-poster.py            # Indonesian
      python tools/make-promo-poster.py --lang en  # English
"""

import os
import subprocess
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video, promo_video_en

# One poster per language, because the poster is the frame that carries the words.
# An English page whose poster shows an Indonesian call to action is a still the
# visitor cannot read - and it is the still they see for the whole time they are on
# the page if autoplay is blocked.
LANG = 'en' if '--lang' in sys.argv and sys.argv[sys.argv.index('--lang') + 1] == 'en' else 'id'

VIDEO = (promo_video_en() if LANG == 'en' else promo_video()) or \
    ('site/assets/video/lumawall-promo-en.mp4' if LANG == 'en'
     else 'site/assets/video/lumawall-promo.mp4')
OUT = ('site/assets/shots/poster-promo-en.png' if LANG == 'en'
       else 'site/assets/shots/poster-promo.png')

# The shots, read from the cut list so the times follow the piece. The previous
# version hardcoded seven windows, and after the piece was re-cut to eleven shots
# every one of those times landed in the wrong scene - including the poster time,
# which pointed past the end of a 47.5s render.
from shotlist import windows

_W = dict((n, (a, b)) for n, a, b in windows())


def _at(name, frac):
    """A time inside `name`, at `frac` of the way through it."""
    a, b = _W[name]
    return round(a + (b - a) * frac, 2)


# The close's call-to-action frame is the right poster. It carries the mark, the
# headline and the URL, so a visitor whose browser blocks autoplay sees what the
# product is and where to get it. A frame from the middle of the piece is prettier
# but has no branding at all - a review of exactly that choice scored it 5/10 and
# pointed out that nothing on it said "LumaWall".
CANDIDATES = [
    (_at('close', 0.80), 'close',   'the call-to-action frame: mark, headline, download button'),
    (_at('close', 0.60), 'close',   'a moment earlier, as the button arrives'),
    (_at('close', 0.35), 'close',   'the mark and the wordmark, before the button'),
    (_at('multi', 0.55), 'multi',   'three screens, three wallpapers - no branding'),
    (_at('browse', 0.55), 'browse', 'the app UI with its wallpaper grid'),
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

    # The close frame wins because it carries the branding, and branding is the one
    # thing a poster cannot do without. The rest are fallbacks.
    pick = next((f for f in frames if f[1] == 'close' and f[5] > 0.06), None)
    if pick is None:
        pick = next((f for f in frames if f[1] == 'multi' and 25 < f[4] < 140), None)
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
