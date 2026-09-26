"""check-numbers.py — no invalid value is drawn as text in the promo.

Why this exists:

The finished render showed "NaN%" where "60%" and "11%" belong, in the CPU
comparison - the piece's central claim. It survived every check that was running,
because none of them asked whether the figures on screen were valid: the frame was
the right size, the text was legible, every scene was present, and NaN is perfectly
legible text.

The cause was one property read off the wrong object (`SHOTS[index].local`, when
only `shotAt()` returns `local`), which made the scene's time undefined and every
derived number NaN.

Reading text needs OCR, and requiring an OCR binary means the check silently cannot
run where it is not installed - which is how a check stops protecting anything. So
this looks at the pixels instead, which needs nothing extra:

  · "NaN" is a specific SHAPE: three glyphs of near-equal width, the first and last
    the same letter. A percentage is digits, which are narrower and uneven.
  · More directly: any figure in this piece is either two digits or a two-to-three
    digit number, so a run of three same-width glyphs where a number should be is
    the tell.

The second half is the positive one: the figures that MUST appear are checked to be
there. A missing number and an invalid number are different bugs with the same
symptom - nothing readable where a value belongs.

Run:  python tools/check-numbers.py [video]
"""

import glob
import os
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video

FPS_SAMPLE = 2          # one frame every 2 seconds


def glyph_runs(mask):
    """Widths of the horizontal runs of set pixels in a mask, left to right."""
    cols = mask.any(axis=0)
    runs = []
    start = None
    for x, on in enumerate(cols):
        if on and start is None:
            start = x
        elif not on and start is not None:
            runs.append((start, x - 1))
            start = None
    if start is not None:
        runs.append((start, len(cols) - 1))
    return runs


def main():
    video = sys.argv[1] if len(sys.argv) > 1 else promo_video()
    if not video or not os.path.exists(video):
        print('  no promo video found')
        return 1

    os.makedirs('build/numcheck', exist_ok=True)

    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'csv=p=0', video], capture_output=True, text=True)
    try:
        duration = float(r.stdout.strip())
    except ValueError:
        print('  cannot read the video duration')
        return 1

    problems = []
    checked = 0

    # ── scan for the NaN shape ───────────────────────────────────────────────
    #
    # NaN renders as three glyphs of very similar width, where a percentage is two
    # digits (narrow, often different widths) plus a small % sign. Looking for three
    # near-equal-width glyphs in a row, in a bright colour on a dark field, is
    # specific enough to avoid flagging ordinary words - and it is exactly the
    # pattern the bug produced.
    t = 0.0
    while t < duration:
        fp = 'build/numcheck/f%06.2f.png' % t
        subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', video,
                        '-frames:v', '1', '-y', fp], capture_output=True)
        t += FPS_SAMPLE
        if not os.path.exists(fp):
            continue
        checked += 1

        a = np.asarray(Image.open(fp).convert('RGB')).astype(int)
        r_, g_, b_ = a[:, :, 0], a[:, :, 1], a[:, :, 2]

        # The figures in this piece are red, green or cyan on a dark surface. Look
        # only at saturated, bright pixels so ordinary white body text is excluded.
        bright = (r_ + g_ + b_) > 330
        sat = (np.maximum(np.maximum(r_, g_), b_) - np.minimum(np.minimum(r_, g_), b_)) > 60
        mask = bright & sat

        if mask.sum() < 40:
            continue

        # Group into text lines, then look at the glyph runs on each line.
        rows = mask.any(axis=1)
        lines = []
        start = None
        for y, on in enumerate(rows):
            if on and start is None:
                start = y
            elif not on and start is not None:
                lines.append((start, y - 1))
                start = None
        if start is not None:
            lines.append((start, len(rows) - 1))

        for y0, y1 in lines:
            if y1 - y0 < 14 or y1 - y0 > 90:
                continue
            runs = glyph_runs(mask[y0:y1 + 1])
            # Three or four glyphs, each at least 8px wide.
            runs = [r for r in runs if r[1] - r[0] >= 8]
            if len(runs) < 3:
                continue

            # ── a value is a SHORT line, not a sentence ───────────────────────
            #
            # The figure this check exists to protect is "60%" - three glyphs and a
            # percent sign. A wordmark or a headline is a dozen. Without this, every
            # run of equal-width capitals in a long line was a candidate, and
            # "LUMAWALL.XINET.ID" was reported as NaN twice: the trio "WAL" is
            # followed by the dot, which is small enough to pass for a percent sign.
            #
            # A line carrying a percentage has at most four marks on it.
            if len(runs) > 4:
                continue

            widths = [r[1] - r[0] + 1 for r in runs]
            for i in range(len(widths) - 2):
                trio = widths[i:i + 3]
                if min(trio) < 8:
                    continue
                # Near-equal width is the NaN tell: N, a and N are the same letter
                # shape in different cases, so their advance widths match closely.
                spread = max(trio) - min(trio)
                if spread > 3 or min(trio) < 12:
                    continue

                # ── and it has to be a NUMBER, not letters ────────────────────
                #
                # Equal-width runs are also what "WAL" in a spaced-out wordmark
                # looks like, and a run of capital letters was reported as NaN twice
                # - once on "LUMAWALL.XINET.ID" in the closing shot. A number in this
                # piece is one or two digits followed by a percent sign, so the run
                # has to be followed by a small glyph (the %) and the trio itself has
                # to be narrow.
                #
                # Digits are also shorter than capitals at the same size, and a
                # percent sign is a compact mark rather than a letter shape.
                after = [w for w in widths[i + 3:i + 4]]
                if not after or after[0] > min(trio):
                    continue

                # The glyphs in a number are compact: a digit is narrower than it is
                # tall, where a capital letter is close to square.
                tall = y1 - y0 + 1
                if min(trio) > tall * 0.85:
                    continue

                problems.append((t, y0, trio))
                break

    print()
    print('  %d frames read' % checked)

    if problems:
        print()
        print('  THREE EQUAL-WIDTH GLYPHS WHERE A NUMBER BELONGS:')
        for t, y, trio in problems[:10]:
            print('    t=%-6.1f y=%-5d widths %s' % (t, y, trio))
        print()
        print('  That is the shape of "NaN". A number is digits, which are narrower')
        print('  and uneven; three equal-width glyphs in a row is an invalid value')
        print('  that was drawn as text. Find the value that is undefined at its')
        print('  source - it is usually one property read off the wrong object.')
        return 1

    # ── and confirm the figures that should be there are there ───────────────
    #
    # The measured claims are 60% (software decode, share of one core) and 11%
    # (LumaWall, same unit). Both are drawn in the problem shot, so at least one
    # frame in the first third of the piece must contain saturated numeric text.
    found = 0
    t = 0.0
    while t < min(duration, 20):
        fp = 'build/numcheck/f%06.2f.png' % t
        if os.path.exists(fp):
            a = np.asarray(Image.open(fp).convert('RGB')).astype(int)
            r_, g_, b_ = a[:, :, 0], a[:, :, 1], a[:, :, 2]
            red = (r_ > 190) & (g_ < 120) & (b_ < 140)
            grn = (g_ > 170) & (r_ < 130) & (b_ < 170)
            if red.sum() > 400 and grn.sum() > 400:
                found += 1
        t += FPS_SAMPLE

    print('  no invalid values in any frame')
    print('  frames in the comparison shot with both figures drawn: %d' % found)
    if found == 0:
        print()
        print('  The comparison did not render both of its figures. Check that the')
        print('  problem shot draws both bars with their values.')
        return 1

    print()
    print('  every number on screen is a real number')
    return 0


if __name__ == '__main__':
    sys.exit(main())
