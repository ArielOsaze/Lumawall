"""check-promo-copy.py — is every string in the promo translated, and does it fit?

Two faults this catches, and both are silent:

  1. A STRING THAT WAS NEVER WIRED. It renders in Indonesian in the English video.
     Nothing fails - the video is the right size, the text is legible, every scene is
     present, and one line is in the wrong language. The only way to see it is to
     compare what the two languages actually draw.

  2. A TRANSLATION THAT OVERFLOWS ITS BOX. English is usually longer than Indonesian
     ("Wallpaper hidup" -> "Live wallpaper" is 1.3x), and a headline is set at a fixed
     size in a fixed-width column. Too long and it wraps to a second line, which pushes
     the layout - or it is clipped, which loses words.

The first is checked by rendering the promo in both languages and diffing the text: a
string that is IDENTICAL in both is either deliberately untranslated (a number, a format
name, a product name) or was missed. The allow-list below is that first set, and it is
short enough to read - which is the point.

The second is checked by the length ratio, which is a proxy for width: the scenes set
their type in a fixed-size box, so a translation that is much longer than the original
is the one that overflows.

Usage:
    python tools/check-promo-copy.py
"""

import json
import os
import re
import subprocess
import sys

COPY = 'promo/src/copy.js'

# Strings that are the same in both languages on purpose. Numbers, units, product and
# format names, and the app's own UI labels.
#
# Anything NOT in this list that renders identically in both languages is a string
# nobody wired to copy.js - so it is in Indonesian in the English video.
SAME_ON_PURPOSE = {
    'LumaWall', 'GPU', 'CPU', 'DXVA2', 'NVDEC / DXVA2', 'PLAYING', 'PAUSED',
    'Display 1', 'Display 2', 'Display 3', 'Windows 10 / 11',
    'Task Manager — CPU', 'Wallpaper engine', 'Browser', 'Explorer', 'Spotify',
    'LumaWall (GPU)', 'Multi-monitor', '1920×1080', '3840×2160', '24 Mbps',
    'HEVC 10-bit', '4K', 'fps', 'K', 'Pause', 'Gratis', 'Katalog',
    # Wallpaper titles are proper nouns - the name of an artwork, not copy.
    'Astra Yao', 'I-14 Thousand-Faced', 'Zankou',
    # Technical terms that are the same word in both languages. These have an entry in
    # copy.js anyway - so the day one needs a different English word, the entry is
    # already there and only the value changes.
    'FRAME RATE', 'BITRATE', 'CPU.',
}

# A string that is only digits, units and separators is a MEASUREMENT, and a
# measurement is not translated - it is the same number in both languages. The first
# version of this check reported 22 of them as "untranslated", which buried the twelve
# real misses in noise. A check whose output has to be filtered by hand is a check
# nobody reads.
_MEASUREMENT = re.compile(
    r'^[\s\d.,%×x·/\-+]*'                     # digits, separators, units' punctuation
    r'(?:GB|MB|KB|fps|K|px|Mbps|bit|ut|th)?'  # and an optional unit
    r'[\s\d.,%×x·/\-+]*$',
    re.I,
)


def is_measurement(s):
    """Is this a number rather than prose?

    True for '40.9%', '0.38 GB', '60 fps', '1920×1080', '1 proses · 12 utas' is NOT
    (it has words), and neither is '5.000+' - that one carries a localisation: the
    thousands separator differs between Indonesian (5.000) and English (5,000).
    """
    t = s.strip()
    if not t:
        return True
    if not re.search(r'\d', t):
        return False
    # Remove the digits and the units; if nothing that looks like a word is left, it is
    # a measurement.
    stripped = re.sub(r'[\d.,%×x·/\-+\s]', '', t)
    stripped = re.sub(r'(GB|MB|KB|fps|K|px|Mbps|bit)', '', stripped, flags=re.I)
    return len(stripped) == 0


# Strings that carry a NUMBER whose formatting is localised. Indonesian writes five
# thousand as 5.000, English as 5,000 - so these are the same string in both languages
# only if the separator was not localised, which is the fault.
LOCALISED_NUMBERS = {'5.000+': '5,000+'}

IGNORE_PREFIX = ('!! ERROR',)

# A translation this much longer than its source will not fit the box the source was
# laid out for. Measured against the actual scenes: the widest headline box is 760px at
# 54px type, which holds about 22 Indonesian characters per line - so a 1.75x English
# string needs a line the scene does not have.
MAX_RATIO = 1.75


def read(p):
    return open(p, encoding='utf-8').read()


def table(name):
    """One table out of copy.js, as a dict.

    Parsed by hand rather than with a regex over the whole object, because the values
    contain apostrophes, em dashes and newlines - and a regex that gets one of those
    wrong silently returns a short table, which reads as "everything is translated".
    """
    src = read(COPY)
    m = re.search(r'export const %s = \{(.*?)\n\};' % name, src, re.S)
    if not m:
        return {}

    out = {}
    body = m.group(1)
    # Each entry starts with a quoted key at the start of a line.
    for em in re.finditer(r"^\s*'((?:[^'\\]|\\.)*)':", body, re.M):
        key = em.group(1).replace("\\'", "'")
        # The value runs from the colon to the next entry or the end.
        start = em.end()
        nxt = re.search(r"^\s*'(?:[^'\\]|\\.)*':", body[start:], re.M)
        chunk = body[start:start + nxt.start()] if nxt else body[start:]
        vm = re.search(r"'((?:[^'\\]|\\.)*)'", chunk, re.S)
        if vm:
            out[key] = vm.group(1).replace("\\'", "'")
    return out


def rendered_texts():
    """What each scene draws, per language, from the real components."""
    out = {}
    for lang in ('id', 'en'):
        env = dict(os.environ)
        env['PROMO_LANG'] = lang
        r = subprocess.run(['node', 'text-probe.mjs'], capture_output=True, text=True,
                           timeout=300, cwd='promo', env=env)
        if r.returncode != 0 or not r.stdout.strip():
            print('  could not render the %s text:' % lang)
            print('    %s' % ((r.stderr or r.stdout) or '')[:400])
            return None
        out[lang] = json.loads(r.stdout)
    return out


def main():
    print()
    print('  promo copy: is every string translated, and does the translation fit?')
    print()

    id_table = table('ID')
    en_table = table('EN')

    if not id_table:
        print('  could not read the ID table from copy.js')
        return 1

    problems = []

    # ── 1. the tables ────────────────────────────────────────────────────────
    missing = [k for k in id_table if k not in en_table]
    extra = [k for k in en_table if k not in id_table]

    print('    copy.js          %d keys, %d translated' % (len(id_table), len(en_table)))
    if missing:
        print('    MISSING %d English entr(ies):' % len(missing))
        for k in missing[:10]:
            print('      · %s' % k[:70])
        problems.append('%d key(s) have no English translation' % len(missing))
    if extra:
        print('    %d English entr(ies) match no source string:' % len(extra))
        for k in extra[:10]:
            print('      · %s' % k[:70])
        problems.append('%d English entr(ies) do not match any source string' % len(extra))

    # ── 2. what the scenes draw ──────────────────────────────────────────────
    print()
    texts = rendered_texts()
    if texts is None:
        return 1

    def flat(d):
        out = set()
        for items in d.values():
            for s in items:
                if not any(s.startswith(x) for x in IGNORE_PREFIX):
                    out.add(s)
        return out

    id_drawn = flat(texts['id'])
    en_drawn = flat(texts['en'])

    print('    scenes draw      %d strings (id), %d strings (en)'
          % (len(id_drawn), len(en_drawn)))

    # ── 3. identical strings ─────────────────────────────────────────────────
    #
    # A string that renders identically is one of three things: a measurement, which is
    # the same in both languages by nature; a proper noun; or a string nobody wired. The
    # first two are filtered out here so the third is the only thing reported - the
    # first version listed 22 measurements alongside the real misses, and a check whose
    # output has to be read past is a check that gets skipped.
    same = sorted(id_drawn & en_drawn)
    measurements = [s for s in same if is_measurement(s)]
    localised = [s for s in same if s in LOCALISED_NUMBERS]
    suspicious = [s for s in same
                  if s not in SAME_ON_PURPOSE
                  and s not in measurements
                  and s not in localised]

    print()
    print('    %d string(s) render identically in both languages' % len(same))
    print('      %d are measurements (same number, both languages)' % len(measurements))
    print('      %d are product names, formats or labels (the allow-list)'
          % len([s for s in same if s in SAME_ON_PURPOSE]))
    print('      %d are numbers whose formatting is localised' % len(localised))
    print('      %d are unexplained' % len(suspicious))

    if localised:
        print()
        print('    A NUMBER THAT SHOULD HAVE BEEN LOCALISED:')
        for s in localised:
            print('      · %s  should read %s in English' % (s, LOCALISED_NUMBERS[s]))
        problems.append('%d number(s) keep their Indonesian separator' % len(localised))

    if suspicious:
        print()
        print('    UNEXPLAINED — still Indonesian in the English video:')
        for s in suspicious:
            print('      · %s' % s[:78])
        problems.append('%d string(s) are not wired to copy.js' % len(suspicious))

    # ── 4. translations that overflow ────────────────────────────────────────
    print()
    print('    length ratio (English / Indonesian), longest first:')
    ratios = []
    for k, v in id_table.items():
        if k in en_table and len(k) > 8:
            ratios.append((len(en_table[k]) / max(1, len(k)), k, en_table[k]))
    ratios.sort(reverse=True)

    for ratio, k, v in ratios[:10]:
        flag = ''
        if ratio > MAX_RATIO:
            flag = '  TOO LONG'
            problems.append('the English for "%s" is %.2fx the Indonesian - it will '
                            'overflow a fixed-width headline' % (k[:40], ratio))
        print('      %.2fx  %-44s -> %s' % (ratio, k[:44], v[:42]))

    print()
    if problems:
        print('  %d problem(s):' % len(problems))
        for p in problems:
            print('    · %s' % p)
        return 1

    print('  every string is translated, and no translation overflows its box')
    return 0


if __name__ == '__main__':
    sys.exit(main())
