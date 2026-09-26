"""list-untranslated.py — the site text nodes that have no English entry.

The generator reports what it could not translate, but it reports the RAW node text -
which is wrapped across lines, so the same paragraph appears several times and the
list is hard to act on. This collapses the whitespace and de-duplicates, so the output
is the actual set of strings still needing a translation.

Usage:
    python tools/list-untranslated.py
"""

import json
import os
import re
import sys

SITE = 'site'
INDEX = os.path.join(SITE, 'index.html')
COPY = os.path.join(SITE, 'assets', 'js', 'site-copy.js')


def read(p):
    return open(p, encoding='utf-8').read()


def en_keys():
    src = read(COPY)
    m = re.search(r'export const EN = \{(.*?)\n\};', src, re.S)
    if not m:
        return set()
    out = set()
    for line in m.group(1).split('\n'):
        line = line.strip()
        if line.startswith("'"):
            e = line.find("':")
            if e > 0:
                out.add(line[1:e].replace("\\'", "'"))
    return out


def main():
    s = read(INDEX)
    s = re.sub(r'<script.*?</script>', '', s, flags=re.S)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)

    keys = en_keys()

    missing = []
    for m in re.finditer(r'(<[a-zA-Z][\w-]*\b[^>]*>)([^<>{}]+)(</[a-zA-Z][\w-]*>)', s):
        text = m.group(2).strip()
        if not text:
            continue
        if not re.search(r'[A-Za-z]{4,}', text) or len(text) <= 12:
            continue
        collapsed = re.sub(r'\s+', ' ', text)
        if collapsed not in keys and collapsed not in missing:
            missing.append(collapsed)

    print()
    print('  %d text node(s) in index.html have no English entry' % len(missing))
    print()
    for x in missing:
        print('  %s' % x)

    json.dump(missing, open('build/site-missing.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print()
    print('  build/site-missing.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
