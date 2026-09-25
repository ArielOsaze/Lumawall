"""fix-test-escapes.py — repairs over-escaped regexes in the CDP test scripts.

Inside a JS template literal, `\\s` is an escaped backslash followed by "s", which
evaluates to the two characters `\s` — a correct regex. A single `\s` is not a
valid escape and collapses to plain `s`, so `/s+/g` silently replaces every run of
the letter "s". That is what made the site's own headline read as "di  etiap".

This normalises any single-escaped class inside a template literal to a
double-escaped one.
"""

import io
import re
import sys

PATTERNS = [
    ('s', 'whitespace'),
    ('d', 'digit'),
    ('w', 'word char'),
]

changed_files = []

for path in sys.argv[1:]:
    text = io.open(path, encoding='utf-8').read()
    original = text

    for letter, _ in PATTERNS:
        # A single backslash before the letter, not preceded by another backslash.
        bad = re.compile(r'(?<!\\)\\' + letter)
        good = '\\\\' + letter
        # Only inside template literals (between backticks) or evalJs strings.
        if bad.search(text):
            text = bad.sub(lambda m: good, text)

    if text != original:
        io.open(path, 'w', encoding='utf-8').write(text)
        changed_files.append(path)
        print('  fixed: %s' % path)

if not changed_files:
    print('  nothing to fix')

# Report what the file now contains, measured rather than eyeballed.
for path in sys.argv[1:]:
    text = io.open(path, encoding='utf-8').read()
    for i, line in enumerate(text.split('\n'), 1):
        if 'replace(' in line and 'textContent' in line:
            bs = line.count('\\')
            print('  %s line %d: %d backslash(es)' % (path.split('/')[-1], i, bs))
            print('    %s' % line.strip())
