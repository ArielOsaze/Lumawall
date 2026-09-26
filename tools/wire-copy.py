"""wire-copy.py — route every literal string in the scenes through copy.js.

Why a script, and not by hand:

There are 105 strings across 11 scenes, and they sit in three different shapes - JSX
children (`<Type>text</Type>`), string literals in props (`label="text"`), and array
members that get mapped over (`['Windows 10 / 11', ...]`). Editing 105 places by hand
means 105 chances to miss one, and a missed one does not fail: it renders in Indonesian
in the English video, which is exactly the kind of fault that ships.

So this rewrites the scenes mechanically and reports what it changed, and
check-copy-wired.py confirms afterwards that no literal text is left.

The transformation: a string that appears as a KEY in copy.js becomes `t('...')`. A
string that is NOT a key is left alone - that is how the numbers, the format names and
the identifiers stay untranslated without a special case for each one.

Run:  python tools/wire-copy.py --write
      python tools/wire-copy.py            (report only)
"""

import os
import re
import sys

SCENES = 'promo/src/scenes'
COPY = 'promo/src/copy.js'


def keys():
    """The keys in copy.js, which are the Indonesian strings."""
    src = open(COPY, encoding='utf-8').read()
    # Only the ID table: it is the one whose keys are the source strings.
    m = re.search(r'export const ID = \{(.*?)\n\};', src, re.S)
    if not m:
        return set()
    body = m.group(1)
    # 'key':\n  'value',  - the key is the first quoted string on the line.
    out = set()
    for line in body.split('\n'):
        mm = re.match(r"\s*'((?:[^'\\]|\\.)*)':", line)
        if mm:
            out.add(mm.group(1))
    return out


def js_escape(s):
    return s.replace('\\', '\\\\').replace("'", "\\'")


def wire(text, key_set):
    """Rewrite the literal strings that are keys into t('...') calls."""
    changed = []

    # ── 1. JSX children: <Tag>literal</Tag> ──────────────────────────────────
    #
    # Only when the child is a single plain string with no braces, which is how every
    # translatable headline in this piece is written. A child with a nested element or
    # an expression is left alone - those are the split-colour headlines, which are
    # handled by their own keys and need a human.
    def repl_child(m):
        tag_open, body, tag_close = m.group(1), m.group(2), m.group(3)
        s = body.strip()
        if not s or '{' in s or '<' in s:
            return m.group(0)
        if s in key_set:
            changed.append(s)
            return '%s{t(%s)}%s' % (tag_open, repr(s).replace('"', "'"), tag_close)
        return m.group(0)

    text = re.sub(r'(<[A-Za-z][\w.]*\b[^>]*>)([^<>{}]+)(</[A-Za-z][\w.]*>)',
                  repl_child, text)

    # ── 2. string literals inside arrays that are mapped over ────────────────
    #
    # `['Windows 10 / 11', '5.000+ wallpaper']` becomes `[t('...'), t('...')]`. The
    # whole array is rewritten in one pass so a partially-translated list cannot result.
    def repl_array(m):
        body = m.group(1)
        parts = re.findall(r"'((?:[^'\\]|\\.)*)'", body)
        if not parts or not any(p in key_set for p in parts):
            return m.group(0)
        out = body
        for p in parts:
            if p in key_set:
                changed.append(p)
                out = out.replace("'%s'" % p, "t('%s')" % js_escape(p), 1)
        return '[%s]' % out

    text = re.sub(r'\[((?:\s*\'[^\']*\'\s*,?)+)\]', repl_array, text)

    return text, changed


def main():
    write = '--write' in sys.argv
    key_set = keys()
    if not key_set:
        print('  no keys found in copy.js')
        return 1

    print('  %d keys in copy.js' % len(key_set))
    print()

    total = 0
    for f in sorted(os.listdir(SCENES)):
        if not f.endswith('.jsx'):
            continue
        path = os.path.join(SCENES, f)
        src = open(path, encoding='utf-8').read()

        # A scene that already imports t keeps it.
        new, changed = wire(src, key_set)
        if not changed:
            print('    %-20s nothing to wire' % f)
            continue

        # Add the import if the file now uses t() and does not import it.
        if 't(' in new and 'from \'../copy.js\'' not in new:
            m = re.search(r"^(import .*?;\n)", new, re.M)
            if m:
                new = new[:m.end()] + "import { t } from '../copy.js';\n" + new[m.end():]
            else:
                new = "import { t } from '../copy.js';\n" + new

        total += len(changed)
        print('    %-20s %d string(s) wired' % (f, len(changed)))
        for c in changed:
            print('        %s' % c[:72])

        if write:
            open(path, 'w', encoding='utf-8', newline='\n').write(new)

    print()
    print('  %d string(s) %s' % (total, 'rewritten' if write else 'would be rewritten'))
    if not write:
        print('  (run with --write to apply)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
