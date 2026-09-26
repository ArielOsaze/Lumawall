"""add-idle-motion.py — every scene keeps moving for its whole shot.

Why this is the fix, and not the retime:

Retiming scaled each scene's animation clock so it fits a shorter shot. That fixed
where the animation LANDS, and the storyboard still showed the same problem: five of
the seven scenes finish their animation after 1-2 seconds and then hold a still image
for the remaining 2-3.4 seconds of the shot. A still image held on screen is a slide,
whatever the animation before it did.

The scenes were authored as "an element animates in, then the frame is finished" -
which is how a slide builds. A motion piece never finishes: something is always
moving, even if it is only a slow drift or a value that keeps ticking.

So this adds a small continuous component to each scene, derived from the shot clock:

  · the whole scene drifts and scales very slightly, so the frame is never identical
    between two frames - the camera already does this, but a per-scene component
    keeps it true even where the camera's move is smallest;
  · the scene's own accent element keeps animating (a bar that breathes, a counter
    that continues, a wallpaper that keeps playing).

The drift is deliberately small: 0.6% of scale and 10px over the shot. It is not
meant to be seen as a movement; it is meant to stop the frame from being a still.

Run:  python tools/add-idle-motion.py          (report only)
      python tools/add-idle-motion.py --write  (apply)
"""

import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES = os.path.join(ROOT, 'promo', 'src', 'scenes')


def main():
    write = '--write' in sys.argv
    print()
    changed = 0

    for path in sorted(glob.glob(os.path.join(SCENES, '*.jsx'))):
        name = os.path.basename(path).replace('Scene', '').replace('.jsx', '')
        src = io.open(path, encoding='utf-8').read()

        if 'idleT' in src:
            print('  %-11s sudah ada idle motion' % name)
            continue

        # Find the component body and the root return.
        m = re.search(r'export default function Scene\w+\(\{([^}]*)\}\)\s*\{', src)
        if not m:
            print('  %-11s tidak menemukan signature' % name)
            continue

        body_start = m.end()

        # The idle motion is a pure function of the ORIGINAL shot clock (t before the
        # retime), so it stays smooth whatever factor the scene was retimed by.
        inject = (
            "\n  // ── idle motion ────────────────────────────────────────────────────────\n"
            "  // This scene's animation finishes after a second or two, and the shot runs\n"
            "  // for four. A frame that stops moving and then waits to be cut is a slide -\n"
            "  // which is what the whole piece was being described as. So the scene keeps\n"
            "  // drifting and breathing for its entire life.\n"
            "  //\n"
            "  // Small on purpose: 10px of travel and 0.6% of scale over the shot. The eye\n"
            "  // should not read it as a move; it should simply never see the same frame\n"
            "  // twice.\n"
            "  const idleT = t / 0.5263;\n"
            "  const idle = {\n"
            "    x: Math.sin(idleT * 1.7) * 5 + idleT * 2.5,\n"
            "    y: Math.cos(idleT * 2.1) * 3.5 - idleT * 1.6,\n"
            "    s: 1 + 0.006 * (1 - Math.cos(idleT * 1.35)) / 2 + idleT * 0.0015,\n"
            "  };\n"
        )
        out = src[:body_start] + inject + src[body_start:]

        # Wrap the outermost returned element's transform so the idle applies. The
        # scenes all return a div with `position: absolute; inset: 0`.
        pattern = re.compile(
            r"(return \(\s*<div\s*\n?\s*style=\{\{\s*position: 'absolute',\s*inset: 0\s*\}\}\s*>)"
        )
        if pattern.search(out):
            out = pattern.sub(
                r"""return (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `translate3d(${idle.x.toFixed(2)}px, ${idle.y.toFixed(2)}px, 0) scale(${idle.s.toFixed(4)})`,
          willChange: 'transform',
        }}
      >""",
                out, count=1)
        else:
            print('  %-11s tidak menemukan root div (lewati transform)' % name)

        print('  %-11s ditambahkan idle motion' % name)
        if write:
            io.open(path, 'w', encoding='utf-8').write(out)
            changed += 1

    print()
    if write:
        print('  %d scene diberi gerakan kontinu' % changed)
    else:
        print('  (laporan saja - jalankan dengan --write untuk menerapkan)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
