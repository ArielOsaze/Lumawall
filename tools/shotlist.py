"""shotlist.py — reads the promo's cut list from Direction.jsx.

Why this exists:

Four tools carried their own copy of the shot boundaries - check-promo-scenes,
check-frame-margins, measure-promo-backgrounds, make-promo-poster. Every time the cut
list changed, those copies went stale, and a stale copy does not fail: it samples the
wrong moments and reports about a piece that no longer exists. That happened twice,
and the second time it meant a checker passed while sampling two shots that had been
merged.

The cut list lives in one place. This reads it.

Run:  python tools/shotlist.py          (print the current list)
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRECTION = os.path.join(ROOT, 'promo', 'src', 'Direction.jsx')


def shots():
    """[(id, cut), ...] in order, read from Direction.jsx."""
    src = open(DIRECTION, encoding='utf-8').read()
    block = re.search(r'export const SHOTS = \[(.*?)\];', src, re.S)
    if not block:
        return []
    out = []
    for m in re.finditer(r"\{\s*id:\s*'([a-z]+)'(.*?)\}", block.group(1), re.S):
        cut = re.search(r'cut:\s*([0-9.]+)', m.group(2))
        if cut:
            out.append((m.group(1), float(cut.group(1))))
    return out


def windows():
    """[(id, start, end), ...] - each shot's span, derived from the cut list."""
    s = shots()
    out = []
    for i, (name, cut) in enumerate(s):
        end = s[i + 1][1] if i + 1 < len(s) else total()
        out.append((name, cut, end))
    return out


def total():
    src = open(DIRECTION, encoding='utf-8').read()
    m = re.search(r'export const TOTAL_SECONDS = ([0-9.]+)', src)
    return float(m.group(1)) if m else 52.0


def midpoints():
    """[(id, t), ...] - one sample in the middle of each shot, away from its cuts."""
    return [(n, (a + b) / 2) for n, a, b in windows()]


if __name__ == '__main__':
    print()
    print('  cut list, from Direction.jsx (%d shots, %.1fs):' % (len(shots()), total()))
    print()
    prev = None
    for name, cut in shots():
        length = '' if prev is None else '  (%.1fs)' % (cut - prev)
        print('    %-12s %6.1fs%s' % (name, cut, length))
        prev = cut
    if prev is not None:
        print('    %-12s %6.1fs  (%.1fs)' % ('end', total(), total() - prev))
    sys.exit(0)
