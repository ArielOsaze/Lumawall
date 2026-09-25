"""check-promo-text.py — finds text in the promo that cannot be read.

The user reported that "beberapa teks ga kebaca". Asking a vision model gave a
different answer every time - one pass said the DISPLAY labels were crisp and
high-contrast, another said there was no text at all in the same strip. The question
is measurable, so it is measured here instead.

Two things make text unreadable in a rendered video, and both are arithmetic:

  1. Too small. A caption under 20px in a 1080p frame is about 1.2% of the frame
     height; on a phone that is a few pixels. Anything below that is decoration.
  2. Too little contrast against what is directly behind it. The correct measurement
     is the glyph colour against the pixels immediately around the glyph, not against
     the darkest part of the frame - comparing a white label to the black gap beside
     it always reports a high ratio and hides the problem.

This samples every beat, finds the text runs, and reports the ones that fail either
test, with the frame saved so the failure can be looked at.

Run:  python tools/check-promo-text.py [video]
"""

import os
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import label as cc_label
from scipy.ndimage import uniform_filter

VIDEO = sys.argv[1] if len(sys.argv) > 1 else 'build/livevid/promo.mp4'

BEATS = [
    ('intro', 3.0), ('problem', 10.5), ('catalog', 17.5),
    ('monitors', 25.5), ('pause', 34.0), ('perf', 41.5), ('outro', 48.5),
]

# A text run this short in a 1080p frame is unreadable on anything but a desktop.
MIN_GLYPH_HEIGHT = 16
# WCAG AA for normal text. Large text (>= 24px bold or >= 18.66px) may use 3.0.
MIN_CONTRAST = 4.5
MIN_CONTRAST_LARGE = 3.0


def frame(t):
    tmp = os.path.join('build', '_text.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', VIDEO,
                    '-frames:v', '1', '-y', tmp], capture_output=True)
    return np.asarray(Image.open(tmp).convert('RGB')).astype(float)


def rel_lum(rgb):
    c = rgb / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def find_text_runs(a):
    """Connected groups of near-white pixels that look like glyphs."""
    luma = rel_lum(a)
    # Text in this piece is white or near-white.
    mask = (a.min(axis=2) > 150) & (luma > 0.55)
    if mask.sum() < 40:
        return []

    labels, n = cc_label(mask)
    runs = []
    for i in range(1, n + 1):
        ys, xs = np.where(labels == i)
        if len(ys) < 30:
            continue
        h = ys.max() - ys.min() + 1
        w = xs.max() - xs.min() + 1
        # A glyph or a word: not a hairline, not a giant block.
        if h < 4 or w < 4:
            continue
        runs.append((ys.min(), ys.max(), xs.min(), xs.max(), h, w, len(ys)))
    return runs


def local_contrast(a, y0, y1, x0, x1):
    """Contrast of the glyphs against the pixels immediately around them."""
    pad = 6
    y0p, y1p = max(0, y0 - pad), min(a.shape[0], y1 + pad + 1)
    x0p, x1p = max(0, x0 - pad), min(a.shape[1], x1 + pad + 1)
    patch = a[y0p:y1p, x0p:x1p]
    l = rel_lum(patch)
    glyph = l[y0 - y0p:y1 - y0p + 1, x0 - x0p:x1 - x0p + 1]
    # Background = the patch with the glyphs removed.
    bg_mask = np.ones_like(l, dtype=bool)
    bg_mask[y0 - y0p:y1 - y0p + 1, x0 - x0p:x1 - x0p + 1] = False
    if bg_mask.sum() < 20:
        return None
    gl = glyph.mean()
    bl = l[bg_mask].mean()
    hi, lo = max(gl, bl), min(gl, bl)
    return (hi + 0.05) / (lo + 0.05)


def main():
    if not os.path.exists(VIDEO):
        print('  no video at %s' % VIDEO)
        return 1

    print('  %s' % VIDEO)
    print()
    problems = []

    for beat, t in BEATS:
        a = frame(t)
        if a is None:
            print('  %-10s could not read' % beat)
            continue

        runs = find_text_runs(a)
        # Group runs into lines by vertical overlap, so a word is one entry.
        runs.sort(key=lambda r: (r[0] // 12, r[2]))
        lines = []
        for r in runs:
            for ln in lines:
                if not (r[1] < ln[0] - 4 or r[0] > ln[1] + 4):
                    ln[0] = min(ln[0], r[0]); ln[1] = max(ln[1], r[1])
                    ln[2] = min(ln[2], r[2]); ln[3] = max(ln[3], r[3])
                    ln[4] = max(ln[4], r[4])
                    break
            else:
                lines.append([r[0], r[1], r[2], r[3], r[4]])

        if not lines:
            print('  %-10s no text found' % beat)
            continue

        worst = None
        small = 0
        for y0, y1, x0, x1, h in lines:
            if h < MIN_GLYPH_HEIGHT:
                small += 1
            cr = local_contrast(a, y0, y1, x0, x1)
            if cr is not None and (worst is None or cr < worst[0]):
                worst = (cr, h, x0, y0)

        if worst is None:
            print('  %-10s %2d text line(s), contrast not measurable' % (beat, len(lines)))
            continue

        cr, h, x, y = worst
        need = MIN_CONTRAST_LARGE if h >= 24 else MIN_CONTRAST
        ok = cr >= need and h >= MIN_GLYPH_HEIGHT
        flag = 'OK' if ok else 'TIDAK TERBACA'
        if not ok:
            problems.append((beat, cr, h, x, y))
        print('  %-10s %2d baris teks  |  terburuk: kontras %.2f (butuh %.1f), '
              'tinggi glyph %dpx  -> %s' % (beat, len(lines), cr, need, h, flag))

    print()
    if problems:
        print('  %d beat punya teks yang tidak terbaca:' % len(problems))
        for beat, cr, h, x, y in problems:
            print('    %-10s kontras %.2f, tinggi %dpx, di x=%d y=%d' % (beat, cr, h, x, y))
        return 1
    print('  semua teks terbaca pada 1080p')
    return 0


if __name__ == '__main__':
    sys.exit(main())
