"""check-app-text.py — checks the app's own user-visible text.

The website's copy was cleaned of the writing habits that read as machine-written
(em-dashes as pauses, "bukan sekadar", filler connectives). The Windows app has
its own user-visible strings — tray menu items, tooltips, the log's messages — and
they were never checked.

This extracts the string literals that are plausibly user-facing and reports any
that carry the same tells.

Run:  python tools/check-app-text.py
"""

import io
import re
import sys

FILES = ['LumaWall/MainWindow.cs', 'LumaWall/Program.cs', 'LumaWall/Icons.cs']

TELLS = [
    ('em-dash', '\u2014'),
    ('en-dash', '\u2013'),
    ('bukan sekadar', 'bukan sekadar'),
    ('yang memang', 'yang memang'),
    ('tanpa perlu', 'tanpa perlu'),
    ('perlu diketahui', 'perlu diketahui'),
    ('pada dasarnya', 'pada dasarnya'),
]

# A string is plausibly user-facing if it looks like prose: it has a space, and it
# is not a path, a flag, CSS, or an identifier.
def looks_like_prose(s):
    if ' ' not in s:
        return False
    if len(s) < 6:
        return False
    if any(c in s for c in ('\\', '/', '{', '}', '<', '>', '=', ';', '(', ')')):
        return False
    if s.startswith('--'):
        return False
    if re.match(r'^[a-z0-9_\-\.]+$', s):
        return False
    return True


print('  app text checks:')
problems = []
total = 0

for path in FILES:
    try:
        text = io.open(path, encoding='utf-8', errors='replace').read()
    except FileNotFoundError:
        print('    %s: not found' % path)
        continue

    strings = [s for s in re.findall(r'"([^"\\\n]{4,120})"', text) if looks_like_prose(s)]
    total += len(strings)

    hits = []
    for s in strings:
        for name, pat in TELLS:
            if pat in s:
                hits.append((name, s))

    print('    %-24s %3d prose strings, %d with a tell' % (
        path.split('/')[-1], len(strings), len(hits)))
    for name, s in hits:
        print('      [%s] %s' % (name, s[:80]))
        problems.append('%s: %s' % (path, name))

print()
print('  %d prose strings checked in total' % total)
if problems:
    print('  %d with a machine-writing tell:' % len(problems))
    for p in problems:
        print('    ' + p)
    sys.exit(1)
print('  the app text is clean')
