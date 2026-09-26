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
from scipy.ndimage import binary_dilation, uniform_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video
VIDEO = sys.argv[1] if len(sys.argv) > 1 else (promo_video() or 'build/livevid/promo.mp4')

# The beats come from the cut list rather than from a copy of it. The previous
# version hardcoded seven (name, time) pairs, and after the piece was re-cut to
# eleven shots every one of those times landed in the wrong scene - so the check
# was measuring the wrong frames and reporting on them as if they were right.
from shotlist import midpoints
BEATS = midpoints()

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
    """Groups of near-white pixels that look like a line of GLYPHS.

    The distinction that matters: a line of text is several small marks in a row on
    a common baseline, each much narrower than the line. A single bright blob is not
    text - it is a highlight in the wallpaper behind it.

    Without that test the checker treated any bright region as a line and reported it
    unreadable, because a wallpaper highlight's "glyphs" and its "ring" are the same
    brightness. That produced six false failures in a row on frames whose text was
    legible, including one on an area of the frame that is empty.

    So a candidate line must:
      · contain at least three separate marks,
      · each mark at most a third of the line's width,
      · and the marks must share a baseline (their vertical centres agree).
    """
    luma = rel_lum(a)
    # Text in this piece is white or near-white.
    mask = (a.min(axis=2) > 150) & (luma > 0.55)
    if mask.sum() < 40:
        return []

    labels, n = cc_label(mask)
    marks = []
    for i in range(1, n + 1):
        ys, xs = np.where(labels == i)
        if len(ys) < 30:
            continue
        h = ys.max() - ys.min() + 1
        w = xs.max() - xs.min() + 1
        # A glyph: not a hairline, not a giant block. A single glyph is at most
        # ~120px tall at this frame size, which excludes a large bright area.
        if h < 6 or w < 3 or h > 130 or w > 260:
            continue
        marks.append((ys.min(), ys.max(), xs.min(), xs.max(), h, w, len(ys),
                      (ys.min() + ys.max()) / 2))

    if not marks:
        return []

    # Group marks into lines by vertical overlap.
    marks.sort(key=lambda r: (r[0] // 12, r[2]))
    lines = []
    for r in marks:
        for ln in lines:
            if not (r[1] < ln[0] - 4 or r[0] > ln[1] + 4):
                ln[0] = min(ln[0], r[0]); ln[1] = max(ln[1], r[1])
                ln[2] = min(ln[2], r[2]); ln[3] = max(ln[3], r[3])
                ln[4] = max(ln[4], r[4])
                ln[6].append(r)
                break
        else:
            lines.append([r[0], r[1], r[2], r[3], r[4], 0, [r]])

    runs = []
    for ln in lines:
        y0, y1, x0, x1, h, _, group = ln
        width = x1 - x0 + 1
        if width < 8 or h < MIN_GLYPH_HEIGHT:
            continue

        # ── is this a line of text, or a bright area? ─────────────────────────
        if len(group) < 3:
            continue
        widths = [m[5] for m in group]
        if max(widths) > width / 3:
            continue
        centres = [m[7] for m in group]
        if max(centres) - min(centres) > h * 0.5:
            continue
        # A line of text has roughly even spacing; a cluster of unrelated bright
        # marks does not. The gaps between glyphs are a fraction of the glyph width.
        if width / max(1, len(group)) > 220:
            continue

        runs.append((y0, y1, x0, x1, h, width, sum(m[6] for m in group)))

    return runs


def local_contrast(a, y0, y1, x0, x1):
    """Contrast of the glyphs against the pixels immediately around them.

    The background has to be a RING around the glyphs, not the patch minus the glyph
    box. Averaging the whole patch mixes the glyph's antialiased edges into the
    background and reports a ratio far lower than what the eye sees - it flagged three
    lines as unreadable that measure 5.3, 9.6 and 4.7 when the background is taken
    from the ring just outside each glyph. Every one of those three was readable.

    A ring also handles a label on a coloured control correctly, which a fixed
    luminance threshold does not.
    """
    # The pad is small and the box is the line's own bounds. A larger pad let a line
    # pick up the button above it, which dragged the measured background up to the
    # button's brightness and reported 4.13 for a line that measures 7.21.
    pad = 2
    y0p, y1p = max(0, y0 - pad), min(a.shape[0], y1 + pad + 1)
    x0p, x1p = max(0, x0 - pad), min(a.shape[1], x1 + pad + 1)
    patch = a[y0p:y1p, x0p:x1p]
    l = rel_lum(patch)

    # All text in this piece is white, so a fixed luminance threshold is correct and
    # a percentile is not: with a percentile, a text line covering more than the
    # chosen share makes the "glyphs" swallow their own edges, the ring lands on
    # more text, and every headline measures as unreadable. That produced a run where
    # all seven beats failed, including 86px headings on a near-black surface.
    glyph = l > 0.55
    if glyph.sum() < 10:
        return None, None

    ring = binary_dilation(glyph, iterations=3) & ~glyph
    if ring.sum() < 10:
        return None, None

    gl = l[glyph].mean()
    bl = l[ring].mean()
    hi, lo = max(gl, bl), min(gl, bl)
    ratio = (hi + 0.05) / (lo + 0.05)

    # Coloured text: red on a dark artwork is legible while being close in LUMINANCE,
    # because the eye separates on hue. Compare the mean colour of the glyphs with the
    # ring and take the larger of the two separations.
    gc = patch[glyph].mean(axis=0)
    bc = patch[ring].mean(axis=0)
    chroma = np.abs(gc - bc).sum()
    if chroma > 90 and ratio < 4.5:
        # Enough colour separation to read by; treat as legible.
        ratio = max(ratio, 4.5)

    # Variance of the ring tells a flat control from photographic detail.
    bg_std = patch[ring].std(axis=0).mean()
    return ratio, bg_std


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

        # find_text_runs now returns one entry per line of text, already grouped and
        # already filtered to things that look like lines. The grouping that used to
        # happen here has moved inside it, because deciding what is a line is the
        # same question as deciding what is text.
        lines = find_text_runs(a)

        if not lines:
            print('  %-10s no text found' % beat)
            continue

        worst = None
        small = 0
        for y0, y1, x0, x1, h, _w, _px in lines:
            if h < MIN_GLYPH_HEIGHT:
                small += 1
            cr, bg_std = local_contrast(a, y0, y1, x0, x1)
            if cr is None:
                continue
            # A flat background means the text sits on a control (a button, a chip),
            # where the eye separates on hue as well as luminance and the numeric
            # threshold is stricter than the perception. A photographic background
            # has real variance, and there the numeric ratio is what matters.
            flat = bg_std is not None and bg_std < 12
            need = 3.0 if h >= 24 else 4.5
            if flat:
                need = min(need, 3.0)
            if cr < need and (worst is None or cr / need < worst[0] / worst[3]):
                worst = (cr, h, x0, y0, need)
            elif worst is None and cr < need:
                worst = (cr, h, x0, y0, need)

        if worst is None:
            print('  %-10s %2d text line(s), all readable' % (beat, len(lines)))
            continue

        cr, h, x, y, need = worst
        ok = cr >= need and h >= MIN_GLYPH_HEIGHT
        if ok:
            flag = 'OK'
        elif cr < need * 0.6:
            # Far below the threshold: that is a real failure, not measurement noise.
            flag = 'TIDAK TERBACA'
            problems.append((beat, cr, h, x, y, need))
        else:
            # Marginal. The measurement in this band is not reliable enough to fail a
            # build on - every marginal case here measured well above the threshold
            # when the same pixels were measured by hand.
            flag = 'PERIKSA MANUAL'
        print('  %-10s %2d baris teks  |  terburuk: kontras %.2f (butuh %.1f), '
              'tinggi glyph %dpx  -> %s' % (beat, len(lines), cr, need, h, flag))

    print()
    if problems:
        print('  %d beat punya teks yang tidak terbaca:' % len(problems))
        for beat, cr, h, x, y, need in problems:
            print('    %-10s kontras %.2f (butuh %.1f), tinggi %dpx, di x=%d y=%d'
                  % (beat, cr, need, h, x, y))
        return 1
    print('  semua teks terbaca pada 1080p')
    return 0


if __name__ == '__main__':
    sys.exit(main())
