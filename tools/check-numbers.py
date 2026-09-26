"""check-numbers.py — every number rendered in the promo is a real number.

Why this exists:

The finished 52-second render showed "NaN%" where "60%" and "11%" belong, in the
CPU comparison - the piece's central claim. It survived every check that was
running, because none of them looked at whether the figures on screen were valid:
the frame was the right size, the text was legible, the scenes were all present,
and NaN is perfectly legible text.

The cause was one property read off the wrong object (`SHOTS[index].local`, when
only `shotAt()` returns `local`), which made the scene's time undefined and every
derived number NaN. A checker that reads the rendered pixels for "NaN" catches that
class of mistake - and any other that produces it - without having to know where
the mistake is.

Run:  python tools/check-numbers.py [video]
"""

import glob
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from promo_path import promo_video


def ocr(path):
    """Read the text in an image, if tesseract is available."""
    try:
        r = subprocess.run(
            ['tesseract', path, 'stdout', '--psm', '11'],
            capture_output=True, text=True, timeout=90,
        )
        return r.stdout if r.returncode == 0 else ''
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def main():
    video = sys.argv[1] if len(sys.argv) > 1 else promo_video()
    if not video or not os.path.exists(video):
        print('  no promo video found')
        return 1

    os.makedirs('build/numcheck', exist_ok=True)

    # Sample across the whole piece. The figures appear in the problem and perf
    # shots, but every shot is sampled: a NaN can appear anywhere a value is
    # computed, and looking only where numbers are expected would miss it.
    times = [t / 2 for t in range(2, 104, 2)]

    texts = []
    for t in times:
        fp = 'build/numcheck/f%05.1f.png' % t
        subprocess.run(
            ['ffmpeg', '-v', 'error', '-ss', str(t), '-i', video,
             '-frames:v', '1', '-y', fp],
            capture_output=True,
        )
        if not os.path.exists(fp):
            continue
        got = ocr(fp)
        if got is None:
            print('  tesseract is not installed - cannot read the numbers')
            print('  (install it, or check the figures by eye with:')
            print('   python tools/check-numbers.py --frames)')
            return 1
        texts.append((t, got))

    # ── look for the invalid-value tells ─────────────────────────────────────
    #
    # NaN, Infinity and undefined are all things a renderer will happily draw as
    # text when a computed value is not a number. They are never intentional.
    bad = re.compile(r'\b(NaN|Infinity|undefined|null)\b', re.IGNORECASE)

    problems = []
    for t, text in texts:
        flat = ' '.join(text.split())
        for m in bad.finditer(flat):
            problems.append((t, m.group(0), flat[max(0, m.start() - 40):m.end() + 40]))

    print()
    print('  %d frames read' % len(texts))
    print()

    if problems:
        print('  INVALID VALUES ON SCREEN - this is a rendering bug:')
        for t, word, ctx in problems[:12]:
            print('    t=%-6s %-10s  ...%s...' % (t, word, ctx))
        print()
        print('  A number that could not be computed was drawn as text. Find the')
        print('  value that is undefined at its source; it is usually one property')
        print('  read off the wrong object.')
        return 1

    # ── and confirm the figures that SHOULD be there are there ───────────────
    #
    # The measured claims in this piece are 60% (software decode, share of one
    # core) and 11% (LumaWall, same unit). If neither appears, the comparison did
    # not render even though nothing invalid did either.
    all_text = ' '.join(t for _, t in texts)
    found = [n for n in ('60', '11') if re.search(r'\b' + n + r'\b', all_text)]
    print('  no invalid values in any frame')
    print('  measured figures present: %s' % (', '.join(found) if found else 'NONE'))
    if len(found) < 2:
        print()
        print('  The comparison is missing a figure. Check that the problem shot')
        print('  renders both bars with their values.')
        return 1

    print()
    print('  every number on screen is a real number')
    return 0


if __name__ == '__main__':
    sys.exit(main())
