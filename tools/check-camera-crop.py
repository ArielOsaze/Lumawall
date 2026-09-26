"""check-camera-crop.py — does the camera ever push the frame's own content off screen?

Why this exists:

The visitor's note was "efek zoom nya jadi ngecrop gambar teks juga" - the zoom crops
the picture, and the text too. It was exact. The camera pushed in twice over, a global
1 + 0.075t and a per-shot 1 + 0.10, compounding to 1.183. At that scale the visible
window into a 1920-wide composition is x = 167..1742, and every scene lays its text out
at x = 74 to 132. So the library headline (x = 104) reached screen x = -44 by the end
of its shot: not tight, gone.

Nothing caught it:

  · check-layout.py checks the SOURCE for a screenshot given a height - a different
    fault.
  · check-frame-margins.py checks the rendered frames for content touching the frame
    edge, but by the time the camera has cropped a headline the frame is perfectly
    valid - it just has less in it, and the check sees a comfortable margin because
    the missing thing is not there to measure.

── why this asks the real camera, and not a copy of it ──────────────────────

The first version of this check re-implemented the camera's arithmetic in Python. It
re-implemented it WRONG - it hardcoded z = 1 while Direction.jsx was still applying a
1.183 push-in - so it passed the exact bug it was written for. A check that restates
the thing it is checking cannot find a fault in it.

So this runs tools/camera-probe.mjs, which imports the real Direction.jsx through Vite
and prints what camera(t) actually returns for the whole piece. The check then asks
whether every scene's own layout margin falls inside the visible window at every
moment.

The margins are read from the scenes' source, so a scene that moves its text further
left makes this fail rather than silently cropping it.

Usage:
    python tools/check-camera-crop.py
"""

import json
import os
import re
import subprocess
import sys

SCENES = 'promo/src/scenes'
TIMELINE = 'promo/src/Timeline.jsx'
PROBE = 'promo/camera-probe.mjs'


def read(path):
    return open(path, encoding='utf-8').read()


def scene_margins():
    """The smallest x and y each scene places its own content at.

    Read from the scenes' source rather than assumed: the check exists because content
    at the left margin is what the camera cropped, so the margin has to come from the
    scene that sets it.
    """
    left, top, bottom = 1920, 1080, 0

    for f in sorted(os.listdir(SCENES)):
        if not f.endswith('.jsx'):
            continue
        src = read(os.path.join(SCENES, f))
        # `padding: '0 132px'` insets a scene's content; `left: 74` positions a column.
        for m in re.finditer(r"padding:\s*'(\d+)\s+(\d+)px'", src):
            left = min(left, int(m.group(2)))
        for m in re.finditer(r"\bleft:\s*(\d+)\b", src):
            v = int(m.group(1))
            if 40 <= v <= 400:
                left = min(left, v)
        for m in re.finditer(r"\btop:\s*(\d+)\b", src):
            v = int(m.group(1))
            if 20 <= v <= 400:
                top = min(top, v)
        for m in re.finditer(r"\bbottom:\s*(\d+)\b", src):
            v = int(m.group(1))
            if 20 <= v <= 400:
                bottom = max(bottom, v)

    return left, top, bottom


def origin():
    """The camera's transform origin, from Timeline.jsx."""
    m = re.search(r"transformOrigin:\s*'([\d.]+)%\s+([\d.]+)%'", read(TIMELINE))
    if not m:
        return 0.50, 0.48
    return float(m.group(1)) / 100.0, float(m.group(2)) / 100.0


def main():
    print()
    print('  camera crop: is every scene\'s own margin visible for the whole piece?')
    print()

    if not os.path.exists(PROBE):
        print('  %s is missing' % PROBE)
        return 1

    r = subprocess.run(['node', 'camera-probe.mjs'],
                       capture_output=True, text=True, timeout=180, cwd='promo')
    if r.returncode != 0 or not r.stdout.strip():
        print('  could not evaluate the camera:')
        print('    %s' % (r.stderr or r.stdout or '')[:400])
        return 1

    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        print('  the camera probe did not return JSON')
        print('    %s' % r.stdout[:400])
        return 1

    W, H = data['frameW'], data['frameH']
    frames = data['frames']
    if not frames:
        print('  the camera probe returned no frames')
        return 1

    oxf, oyf = origin()
    ox, oy = W * oxf, H * oyf

    # The rectangle of the composition visible at EVERY moment. A camera that zooms
    # has a different window each frame; the intersection is what everything on screen
    # has to fit inside.
    L, R, T, B = 0.0, float(W), 0.0, float(H)
    worst = None
    for f in frames:
        z, x, y = f['z'], f['x'], f['y']
        if z <= 0:
            continue
        # The inverse of `translate(x, y) scale(z)` about (ox, oy): the part of the
        # composition that lands on screen.
        l = ox - (ox + x) / z
        rr = ox + (W - ox - x) / z
        tt = oy - (oy + y) / z
        bb = oy + (H - oy - y) / z
        if l > L:
            L, worst = l, f
        if rr < R:
            R = rr
        if tt > T:
            T = tt
        if bb < B:
            B = bb

    zmax = max(f['z'] for f in frames)
    zmin = min(f['z'] for f in frames)

    left, top, bottom = scene_margins()

    print('    camera            z %.4f .. %.4f   (from Direction.jsx, via the real module)'
          % (zmin, zmax))
    print('    origin            %.0f%%, %.0f%%' % (oxf * 100, oyf * 100))
    print()
    print('    scene margins     left %4d   top %4d   bottom %4d' % (left, top, bottom))
    print('    visible window    left %4.0f   top %4.0f   right %4.0f   bottom %4.0f'
          % (L, T, R, B))
    print()

    problems = []

    if left < L:
        problems.append(
            'a scene places content at x=%d, but the camera crops everything left of '
            'x=%.0f at %.2fs - so that content is off screen (%.0fpx past the edge)'
            % (left, L, worst['t'] if worst else 0, L - left))
    if top < T:
        problems.append(
            'a scene places content at y=%d, but the camera crops everything above '
            'y=%.0f (%.0fpx)' % (top, T, T - top))
    if bottom and (H - bottom) > B:
        problems.append(
            'a scene places content at y=%d, below the visible bottom at y=%.0f '
            '(%.0fpx)' % (H - bottom, B, (H - bottom) - B))

    if problems:
        print('  %d problem(s):' % len(problems))
        for p in problems:
            print('    · %s' % p)
        print()
        print('  A zoom is not forbidden, but it must not crop what the scenes placed.')
        print('  Either reduce it until the window covers every margin, or move the')
        print('  camera so the subject stays in frame.')
        return 1

    print('  every scene\'s margin is inside the visible window for the whole piece')
    return 0


if __name__ == '__main__':
    sys.exit(main())
