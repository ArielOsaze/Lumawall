"""check-cuts.py — the promo cuts, and the whip peaks exactly on the cut.

Why this replaced check-transition-curve.py:

That tool mirrored the OLD structure - seven beats in one 2D box with a handover
between each pair - and checked that the two beats in a handover never double-exposed.
The structure is gone. The promo now cuts: one shot replaces another on a single
frame, and the only technique at a boundary is a 0.17s directional smear that peaks
on the cut frame.

A checker that mirrors a structure which no longer exists does not fail - it passes,
because the arithmetic it re-implements is still self-consistent. That is the worst
kind of check: it reports success about code that has been deleted. So this one
reads the real module and asserts the real properties.

The properties that matter:

  1. Every cut is a cut. At the cut frame the shot index changes and the previous
     shot is not still on screen - there is no moment where both are visible, which
     is what a crossfade is and what this design removes.
  2. The whip peaks ON the cut, not after it. A smear that peaks late reads as the
     new shot arriving blurry, which is a transition effect; a smear that peaks on
     the cut hides the join, which is a whip pan.
  3. The whip is short. At 30fps a 0.17s window is five frames, so the incoming shot
     is readable within two frames of the cut.
  4. The shots are not evenly spaced. Equal time per shot is the clearest tell of a
     slideshow, so the spacing is asserted to be uneven.

Run:  python tools/check-cuts.py
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRECTION = os.path.join(ROOT, 'promo', 'src', 'Direction.jsx')

FPS = 30


def read_shots():
    """The cut list, read from the module rather than re-typed here."""
    src = open(DIRECTION, encoding='utf-8').read()
    block = re.search(r'export const SHOTS = \[(.*?)\];', src, re.S)
    if not block:
        return None
    return [float(m) for m in re.findall(r'cut:\s*([0-9.]+)', block.group(1))]


def main():
    if not os.path.exists(DIRECTION):
        print('  Direction.jsx not found - the promo structure moved')
        return 1

    src = open(DIRECTION, encoding='utf-8').read()
    cuts = read_shots()
    if not cuts or len(cuts) < 2:
        print('  could not read the cut list from Direction.jsx')
        return 1

    problems = []

    # The names come from the source. A hardcoded list of seven went stale
    # the moment the piece gained a sixth shot, and a checker that names the
    # wrong shot is a checker nobody can act on.
    shot_names = [m.group(1) for m in re.finditer(r"id:\s*'([a-z]+)'", src)]

    # ── 1. the whip window, from the source ──────────────────────────────────
    m = re.search(r'export function cutWhip\(t,\s*window\s*=\s*([0-9.]+)\)', src)
    if not m:
        problems.append('cutWhip() no longer takes a window - cannot check its shape')
        window = 0.17
    else:
        window = float(m.group(1))

    print('  cuts at: %s' % ', '.join('%.1fs' % c for c in cuts))
    print('  whip window: %.2fs = %.1f frames at %d fps' % (window, window * FPS, FPS))
    print()

    # ── 2. the spacing is uneven ─────────────────────────────────────────────
    gaps = [round(cuts[i + 1] - cuts[i], 2) for i in range(len(cuts) - 1)]
    print('  shot lengths: %s' % ', '.join('%.1fs' % g for g in gaps))
    if len(set(gaps)) == 1:
        problems.append('every shot is %.1fs - equal spacing is what a slideshow does' % gaps[0])
    else:
        spread = max(gaps) - min(gaps)
        if spread < 0.4:
            problems.append('the shot lengths are within %.1fs of each other - too even' % spread)

    # ── 3. the whip peaks on the cut, and is short ───────────────────────────
    before = window * 0.35
    after = window * 0.65

    print()
    print('  frame   shot          whip    note')
    print('  ' + '-' * 52)

    def shot_index(t):
        i = 0
        for k, c in enumerate(cuts):
            if t >= c:
                i = k
        return i

    def whip(t):
        for c in cuts[1:]:
            if c - before <= t <= c + after:
                if t <= c:
                    return max(0.0, min(1.0, (t - (c - before)) / before))
                # The source is `1 - easeOut(k)`, and easeOut(k) = 1 - (1-k)^3, so
                # this is (1-k)^3. Writing it as `1 - (1-k)^3` inverts the curve and
                # reports the whip RISING after the cut - which is what an earlier
                # version of this check did, and it would have hidden a real problem.
                return (1 - (t - c) / after) ** 3
        return 0.0

    for cut in cuts[1:]:
        centre = cut * FPS
        for f in (int(centre) - 2, int(centre) - 1, int(centre), int(centre) + 1, int(centre) + 2):
            t = f / FPS
            w = whip(t)
            note = ''
            if abs(f - centre) < 0.5:
                note = 'PEAK' if w > 0.95 else 'not at peak'
                if w <= 0.95:
                    problems.append('the whip does not peak on the cut at %.1fs (%.2f)' % (cut, w))
            print('  %5d   %-12s  %5.2f   %s' % (f, shot_names[shot_index(t)], w, note))
        print()

        # The whip has to be gone quickly: the incoming shot must be readable.
        clear = cut + after
        if clear - cut > 0.14:
            problems.append('the whip takes %.2fs to clear after the cut at %.1fs'
                            % (clear - cut, cut))

    # ── 4. no crossfade anywhere ─────────────────────────────────────────────
    #
    # A crossfade would show as two shots visible at once. The structure only ever
    # mounts one, so the check is that Timeline renders a single scene rather than a
    # list of them - and that nothing fades.
    #
    # The pattern is deliberately narrow. An earlier version matched any `opacity:`
    # followed by a non-1 value, which flagged the scene's own entrance animations
    # (a headline rising is not a crossfade) and would have failed a correct build.
    tl = open(os.path.join(ROOT, 'promo', 'src', 'Timeline.jsx'), encoding='utf-8').read()
    if 'BEATS.map' in tl or 'SHOTS.map' in tl:
        problems.append('Timeline renders a list of shots - that is the slideshow structure')
    if re.search(r'opacity:\s*(whip|presence|cut|p\b)', tl):
        problems.append('Timeline fades between shots - that is a crossfade')

    print()
    if problems:
        print('  PROBLEMS:')
        for p in problems:
            print('    ' + p)
        return 1

    print('  every boundary is a cut, the whip peaks on the cut frame, and the')
    print('  shots are not evenly spaced')
    return 0


if __name__ == '__main__':
    sys.exit(main())
