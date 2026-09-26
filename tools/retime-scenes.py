"""retime-scenes.py — scales every scene's animation to fit its new, shorter shot.

Why this is needed:

The shots are now 3-4 seconds instead of 6-8. Every scene's animation was authored
for the old length, so its delays (1.35, 2.05, 3.0 ...) now land outside its own shot -
the animation never finishes, or worse, never starts.

The retime is a scale of the animation clock, not a rewrite of each scene: a scene is
handed `t` measured in its shot, and multiplying that by a factor makes its whole
internal timeline faster by the same amount. It is one number per scene, and it is
derived from the ratio of the old shot length to the new one, so it stays correct if
the cut list changes again.

Run:  python tools/retime-scenes.py          (report only)
      python tools/retime-scenes.py --write  (apply)
"""

import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES = os.path.join(ROOT, 'promo', 'src', 'scenes')

# The old shot lengths, from the seven-shot version.
OLD = {
    'Intro': 7.2, 'Problem': 7.6, 'Catalog': 7.6, 'Monitors': 8.2,
    'Pause': 8.0, 'Perf': 8.0, 'Outro': 7.6,
}

# The new lengths, from Direction.jsx.
NEW = {
    'Intro': 3.4, 'Problem': 4.0, 'Catalog': 4.0, 'Monitors': 4.2,
    'Pause': 4.0, 'Perf': 4.2, 'Outro': 4.2,
}

# A scene may be reused at a different length; the tightest case sets the factor.
def factor_for(name):
    old = OLD.get(name)
    new = NEW.get(name)
    if not old or not new:
        return None
    return new / old


def main():
    write = '--write' in sys.argv
    print()
    print('  %-14s %8s %8s %8s' % ('scene', 'lama', 'baru', 'faktor'))
    print('  ' + '-'*44)

    changed = 0
    for path in sorted(glob.glob(os.path.join(SCENES, '*.jsx'))):
        name = os.path.basename(path).replace('Scene', '').replace('.jsx', '')
        f = factor_for(name)
        if f is None:
            print('  %-14s %8s %8s %8s' % (name, '-', '-', 'lewati'))
            continue

        src = io.open(path, encoding='utf-8').read()

        # The scene receives `t` as a prop. Retiming is applied where it is used, so
        # the component's own signature stays the same and the renderer does not need
        # to know about it.
        marker = 'export default function Scene'
        m = re.search(marker + r'\w+\(\{\s*t\s*[,}]', src)
        if not m:
            print('  %-14s %8.1f %8.1f %8.3f  (tidak menemukan signature)' % (name, OLD[name], NEW[name], f))
            continue

        # Insert a scaled alias right after the opening brace of the component.
        open_brace = src.index('{', m.start())
        # Find the end of the destructuring pattern.
        close = src.index('}', open_brace)
        params = src[open_brace + 1:close]

        if 'rt' in params.split(','):
            print('  %-14s sudah di-retime' % name)
            continue

        new_params = params.rstrip() + ', rt'
        head = src[:open_brace + 1] + new_params + src[close:]

        # And define rt from t at the top of the body.
        body_start = head.index('{', head.index(')', close)) + 1
        inject = (
            '\n  // Animation clock, scaled to this shot\'s new length. The delays in\n'
            '  // this scene were authored for a %.1fs shot; it is now %.1fs, so the whole\n'
            '  // internal timeline runs %.2fx faster. Without this the animation either\n'
            '  // never finishes inside the shot or never starts.\n'
            '  t = t * %.4f;\n' % (OLD[name], NEW[name], f, f)
        )
        out = head[:body_start] + inject + head[body_start:]

        print('  %-14s %8.1f %8.1f %8.3f' % (name, OLD[name], NEW[name], f))
        if write:
            io.open(path, 'w', encoding='utf-8').write(out)
            changed += 1

    print()
    if write:
        print('  %d scene dipercepat' % changed)
    else:
        print('  (laporan saja - jalankan dengan --write untuk menerapkan)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
