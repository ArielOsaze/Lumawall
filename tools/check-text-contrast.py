"""check-text-contrast.py — is every word on screen actually readable?

Why this exists:

"bbrp teks ga kebaca" - some text is unreadable - came back on a render, and the
existing text check did not catch it. That check measures the glyphs' own contrast
against their local background, which was fine; what it could not see was a scrim
that is measured at the wrong place. The scene's gradient ran .90 -> .58 -> .06, and
the paragraph happened to cross the wallpaper's own bright flare at the point where
the scrim was at 6%. Every glyph was crisp. The background under it was not dark.

So this check does the other half: it looks at the BACKGROUND, not the text. It
reconstructs what the frame would look like with the text removed - by blurring away
the high-frequency detail that glyphs are - and asks whether any large region of the
frame where text sits is too bright for white type.

The measurement is local background luminance under each text block. White text needs
its background under about 0.45 relative luminance to clear 4.5:1, and under about
0.30 to be comfortable. Anything above that is reported with its position, so the
scene that needs a heavier scrim is named.

Usage:
    python tools/check-text-contrast.py [video]
"""

import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video
from shotlist import windows

VIDEO = sys.argv[1] if len(sys.argv) > 1 else (promo_video() or 'site/assets/video/lumawall-promo.mp4')

# Where each scene puts its text, as (x0, y0, x1, y1) fractions of the frame. Only the
# columns that actually carry type are listed, because a scene is allowed to be bright
# where it has no text.
TEXT_BOXES = {
    'hook':    [(0.05, 0.22, 0.62, 0.55), (0.05, 0.86, 0.70, 0.95)],
    'problem': [(0.05, 0.16, 0.40, 0.60), (0.40, 0.10, 0.95, 0.92)],
    'browse':  [(0.20, 0.86, 0.80, 0.96)],
    'apply':   [(0.05, 0.20, 0.40, 0.72)],
    'multi':   [(0.05, 0.10, 0.55, 0.34)],
    'pause':   [(0.05, 0.18, 0.42, 0.74)],
    'gpu':     [(0.05, 0.12, 0.60, 0.34), (0.05, 0.78, 0.60, 0.96)],
    'perf':    [(0.05, 0.14, 0.60, 0.40), (0.05, 0.66, 0.95, 0.90)],
    'quality': [(0.05, 0.20, 0.42, 0.88)],
    'library': [(0.05, 0.18, 0.44, 0.90)],
    'close':   [(0.05, 0.24, 0.52, 0.90)],
}

# Relative luminance above which white type stops being comfortable. 0.30 is roughly
# 3.5:1 for white text; 0.45 is roughly 2:1 and is a failure.
MAX_BG_LUM = 0.30
HARD_FAIL = 0.45


def luminance(rgb):
    """sRGB relative luminance, 0..1, per pixel."""
    c = rgb / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def background_luminance(path, box):
    """The luminance of the frame with the glyphs blurred away.

    A median filter at a radius larger than a glyph's stroke removes the text and
    leaves the background it sits on. scipy is used when it is available; otherwise a
    block-wise median, which is coarser but has the same property.
    """
    im = Image.open(path).convert('RGB')
    W, H = im.size
    x0, y0, x1, y1 = box
    reg = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
    if reg.width < 8 or reg.height < 8:
        return None

    # Downsample first: a glyph stroke is 2-4px at 1080p, so at quarter scale the text
    # is sub-pixel and a median over a few pixels removes it entirely.
    small = reg.resize((max(8, reg.width // 4), max(8, reg.height // 4)), Image.BILINEAR)
    a = np.asarray(small).astype(float)
    lum = luminance(a)

    try:
        from scipy.ndimage import median_filter
        bg = median_filter(lum, size=7)
    except ImportError:
        # Block-wise median: each 7x7 block takes its own median.
        h, w = lum.shape
        bh, bw = max(1, h // 7), max(1, w // 7)
        bg = np.zeros_like(lum)
        for by in range(0, h, bh):
            for bx in range(0, w, bw):
                blk = lum[by:by + bh, bx:bx + bw]
                bg[by:by + bh, bx:bx + bw] = np.median(blk)

    return bg


def main():
    if not VIDEO or not os.path.exists(VIDEO):
        print('  no video to check (looked for %s)' % VIDEO)
        return 1

    shots = windows()
    if not shots:
        print('  could not read the cut list from Direction.jsx')
        return 1

    print()
    print('  text contrast: %s' % VIDEO)
    print('  (background luminance under each text block; white type needs < %.2f)'
          % MAX_BG_LUM)
    print()

    problems = []
    tmp = os.path.join('build', '_contrast.png')
    os.makedirs('build', exist_ok=True)

    for name, a, b in shots:
        if name not in TEXT_BOXES:
            continue

        # Sample a few moments through the shot: a scrim problem can appear only when
        # the wallpaper behind it reaches its brightest frame.
        worst = 0.0
        worst_t = 0.0
        worst_box = None
        for frac in (0.35, 0.55, 0.75):
            t = round(a + (b - a) * frac, 2)
            subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', VIDEO,
                            '-frames:v', '1', '-y', tmp], capture_output=True)
            if not os.path.exists(tmp):
                continue
            for box in TEXT_BOXES[name]:
                bg = background_luminance(tmp, box)
                if bg is None:
                    continue
                # The 90th percentile, not the mean: a text block is unreadable if PART
                # of it is over something bright, and a mean hides exactly that.
                v = float(np.percentile(bg, 90))
                if v > worst:
                    worst = v
                    worst_t = t
                    worst_box = box

        # Which text block, and where in the frame - a bare luminance figure does not
        # say what to move, and the fix is almost always to move one of the two.
        where = ''
        if worst_box:
            where = (' (the text at x %d-%d, y %d-%d)'
                     % (int(worst_box[0] * 1920), int(worst_box[2] * 1920),
                        int(worst_box[1] * 1080), int(worst_box[3] * 1080)))

        if worst >= HARD_FAIL:
            problems.append(
                '%s: the background under its text reaches %.2f luminance at %.1fs - '
                'white type there is unreadable%s' % (name, worst, worst_t, where))
            print('    %-9s  %.2f  at %.1fs   UNREADABLE%s' % (name, worst, worst_t, where))
        elif worst >= MAX_BG_LUM:
            problems.append(
                '%s: the background under its text reaches %.2f luminance at %.1fs - '
                'too bright for comfortable white type%s' % (name, worst, worst_t, where))
            print('    %-9s  %.2f  at %.1fs   too bright%s' % (name, worst, worst_t, where))
        else:
            print('    %-9s  %.2f  at %.1fs   readable' % (name, worst, worst_t))

    print()
    if problems:
        print('  %d problem(s):' % len(problems))
        for p in problems:
            print('    · %s' % p)
        return 1

    print('  every text block sits on a background dark enough for white type')
    return 0


if __name__ == '__main__':
    sys.exit(main())
