"""check_promo_imports.py — verifies the promo sources are consistent.

Catches the two mistakes that actually happened while building the promo:

  1. A component used a helper it had not imported. React threw during render, the
     whole tree unmounted, and every frame from that moment was black — while the
     renderer still reported success.
  2. A scene used WallpaperStage without importing it.

Run: python tools/check_promo_imports.py
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'promo', 'src')

HELPERS = [
    'seg', 'lerp', 'range', 'easeOut', 'easeOutQuint', 'easeOutExpo',
    'easeOutBack', 'easeInOut', 'easeIn', 'pulse', 'spring', 'loop', 'rand',
    'parallax', 'camera', 'cameraTransform', 'clamp01', 'anim',
]


def main():
    problems = []

    for dirpath, _, files in os.walk(SRC):
        for name in sorted(files):
            if not name.endswith(('.js', '.jsx')):
                continue
            path = os.path.join(dirpath, name)
            text = open(path, encoding='utf-8').read()
            rel = os.path.relpath(path, SRC)

            # anim.js defines the helpers, so it does not import them.
            if rel == 'anim.js':
                continue

            # Helpers used but not imported.
            m = re.search(r"import \{([^}]+)\} from '[^']*anim\.js'", text)
            imported = set(n.strip() for n in m.group(1).split(',')) if m else set()

            # Only look at the component body, so the import line itself and
            # comments do not count as usage.
            body = text.split('export default', 1)[-1]
            body = re.sub(r'//.*', '', body)

            used = set(
                h for h in HELPERS
                if re.search(r'\b' + re.escape(h) + r'\s*\(', body)
            )
            missing = sorted(used - imported)
            if missing:
                problems.append('%s: uses %s without importing' % (rel, ', '.join(missing)))

            # Local components used but not imported.
            for comp in ('WallpaperStage', 'Aurora', 'Logo', 'SplitText', 'CountUp'):
                if re.search(r'<' + comp + r'\b', body) and comp not in text.split('export default', 1)[0]:
                    problems.append('%s: uses <%s> without importing' % (rel, comp))

    if problems:
        print('  promo source problems:')
        for p in problems:
            print('    ' + p)
        return 1

    print('  promo sources: all imports resolve')
    return 0


if __name__ == '__main__':
    sys.exit(main())
