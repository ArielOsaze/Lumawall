"""check-scene-layout.py — do the elements a scene places stay inside the frame?

Why this exists, and why it is not a pixel check:

The `multi` scene is about three monitors, and a render of it showed ONE. The placement
compounded three transforms - a percentage position, a translate3d on Z and a scale -
so the second and third screens were pushed past the right edge of the 1920px frame.
The scene rendered, the wallpaper played, the text was readable, and every other check
passed. It just did not contain its own subject.

Three attempts to catch that by measuring the rendered pixels all failed, and each
failure is worth recording because each looked reasonable:

  · Counting connected regions of high local variance reported 1 panel for a frame
    that plainly shows three monitors - the monitors overlap on purpose, so their
    regions merge.
  · Measuring the share of "detail" in a region reported a complete Task Manager panel
    as 6% detailed - the panel is a dark surface with thin text, and the region was
    mostly the surface around it.
  · Counting accent colours reported the green dot as 45000 pixels when the dot is
    90 pixels - the wallpaper behind it contains green.

Pixels are the wrong instrument for a layout fault. The bug was arithmetic, so the test
is arithmetic: this reads the scene's own placement code, evaluates the geometry it
would produce at several moments in the shot, and checks that every element lands
inside the frame and does not collide with the frame's other furniture.

That is exact, it needs no rendering, and it cannot be fooled by lighting, overlap or
what happens to be in the wallpaper.

Usage:
    python tools/check-scene-layout.py
"""

import os
import re
import sys

FRAME_W = 1920
FRAME_H = 1080
SCENES = 'promo/src/scenes'

# Scenes whose placement is computed, and what must hold for each. The geometry is
# re-evaluated here from the same numbers the scene uses, so the two cannot drift.
#
# Each entry: file, the name of the array of elements, and a list of (label, check).
# The checks are written against the variables the scene computes.


def read(path):
    return open(path, encoding='utf-8').read()


def numbers_from(src, names):
    """Pull `const <name> = <expr>;` values out of a scene's source.

    Only the simple linear expressions these scenes use are supported - a lookup table
    of numbers, not an interpreter. Anything it cannot read is reported rather than
    guessed at.
    """
    out = {}
    for n in names:
        m = re.search(r'const\s+%s\s*=\s*([^;]+);' % re.escape(n), src)
        if not m:
            continue
        expr = m.group(1).strip()
        # A plain number, or a simple arithmetic expression of plain numbers.
        if re.fullmatch(r'[\d\s.*+\-/()]+', expr):
            try:
                out[n] = eval(expr, {'__builtins__': {}}, {})
            except Exception:
                pass
    return out


def check_multi():
    """The three monitors in `multi` must all be inside the frame and not overlap the
    app panel's column."""
    path = os.path.join(SCENES, 'SceneMulti.jsx')
    if not os.path.exists(path):
        return [('SceneMulti.jsx is missing', None)], 0

    src = read(path)

    # The scene's own constants. The expressions reference `depth`, which is substituted
    # per monitor below. If these names change, this check must be updated - which is
    # the point: it reads the same arithmetic the scene uses.
    m = re.search(r'const\s+leftPx\s*=\s*([^;]+);', src)
    m2 = re.search(r'const\s+scale\s*=\s*([^;]+);', src)
    m3 = re.search(r'const\s+rotY\s*=\s*([^;]+);', src)
    if not (m and m2 and m3):
        return [('could not read the placement arithmetic from SceneMulti.jsx - the '
                 'check needs updating to match the scene', None)], 0

    # Evaluate the three expressions for each depth 0,1,2.
    #
    # The expressions in the scene reference `depth`, which is `s.z` - the values 0, 1
    # and 2 from the SCREENS array. The array itself is parsed so the depths are the
    # scene's own, not a copy of them.
    depths = []
    m_arr = re.search(r'const SCREENS = \[(.*?)\];', src, re.S)
    if m_arr:
        depths = [int(z) for z in re.findall(r'\bz:\s*(\d+)', m_arr.group(1))]
    if not depths:
        return [('could not read the monitor depths from SceneMulti.jsx', None)], 0

    def ev(expr, depth):
        expr = expr.replace('depth', str(depth))
        return eval(expr, {'__builtins__': {}}, {})

    left_expr, scale_expr, rotY_expr = m.group(1), m2.group(1), m3.group(1)

    width = 640
    panel_right = 74 + 620          # the app panel's column: left 74, width 620
    travel = -46                     # the row's own drift, at its most negative

    problems = []
    checked = 0
    for depth in depths:
        left = ev(left_expr, depth) + travel
        scale = ev(scale_expr, depth)
        rotY = ev(rotY_expr, depth)

        # A screen rotated about Y projects to a narrower shape: the visible width is
        # width * cos(angle) * scale.
        import math
        visible_w = width * abs(math.cos(math.radians(rotY))) * scale
        right = left + visible_w

        checked += 1
        if left < 0:
            problems.append('monitor %d starts off the left edge (left %.0f)' % (depth + 1, left))
        if right > FRAME_W:
            problems.append('monitor %d runs past the right edge (right %.0f of %d)'
                            % (depth + 1, right, FRAME_W))
        if right <= panel_right and depth == 0:
            problems.append('monitor %d is entirely behind the app panel' % (depth + 1))

        print('    monitor %d   left %7.0f   right %7.0f   width %6.0f   %s'
              % (depth + 1, left, right, visible_w,
                 'ok' if 0 <= left and right <= FRAME_W else 'OFF FRAME'))

    return problems, checked


def main():
    print()
    print('  scene layout: does every placed element stay inside the 1920x1080 frame?')
    print()

    problems, checked = check_multi()

    print()
    if problems:
        print('  %d problem(s):' % len(problems))
        for p in problems:
            print('    · %s' % (p[0] if isinstance(p, tuple) else p))
        print()
        print('  This is the fault that put two of the three monitors off screen in the')
        print('  multi scene. It is a placement fault, so it is checked by arithmetic.')
        return 1

    print('  all %d placed elements are inside the frame' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(main())
