"""strip-ai-text.py — removes the writing habits that read as machine-written.

The tell is not any single word, it is a set of habits:

  · em-dashes used as a dramatic pause (— ) in body copy
  · "bukan sekadar X, tapi Y" and its relatives, which inflate a plain point
  · "dirancang supaya", "yang memang", "tanpa perlu" as filler connectives
  · a tricolon in every paragraph, and a summary sentence that repeats the
    paragraph it just ended

Indonesian copy written by a person uses a comma, a full stop, or a new
sentence. This rewrites those constructions rather than swapping one word for
another, because the rhythm is what gives it away.

Run:  python tools/strip-ai-text.py
"""

import io
import re
import sys

PATH = 'site/index.html'

# Each entry: (pattern, replacement, why).
RULES = [
    # Em-dash as a dramatic pause. A full stop or a comma does the same job and
    # is what a person writes.
    (r'\s+—\s+', '. ', 'em-dash pause'),
    (r'\s+—', '.', 'em-dash pause'),

    # "bukan sekadar X, tapi Y" is the most recognisable construction.
    (r'bukan sekadar ([^,.]{3,60}), (?:tapi|melainkan) ',
     r'bukan cuma \1. ', 'inflated contrast'),

    # Filler connectives that add nothing.
    (r'dirancang supaya kamu lupa kalau ini sedang berjalan',
     'kamu akan lupa kalau ini sedang berjalan', 'filler'),
    (r'yang memang tidak dirancang untuk video',
     'yang tidak dirancang untuk video', 'filler'),
    (r'tanpa perlu klik atau menyentuh apa pun',
     'tanpa klik atau sentuhan', 'filler'),
    (r'tanpa perlu ', 'tanpa ', 'filler'),

    # "Tidak ada X, tidak ada Y, dan tidak ada Z" - the tricolon.
    (r'Tidak ada iklan, tidak ada akun, dan tidak ada telemetri\.',
     'Tidak ada iklan, akun, maupun telemetri.', 'tricolon'),

    # Summary sentences that restate the paragraph.
    (r'Setiap keputusan teknis di LumaWall diambil untuk satu alasan: supaya\n\s+wallpaper hidup bisa dibiarkan menyala tanpa kamu harus memikirkannya\.',
     'Semuanya diarahkan ke satu hal: wallpaper hidup yang bisa dibiarkan\n        menyala tanpa kamu pikirkan lagi.', 'restating summary'),
]

text = io.open(PATH, encoding='utf-8').read()
original = text

print('  rewrites:')
for pattern, replacement, why in RULES:
    matches = re.findall(pattern, text)
    if matches:
        text = re.sub(pattern, replacement, text)
        print('    %-22s %d occurrence(s)' % (why, len(matches)))

# After the rules, report what is left so nothing is missed silently.
body = re.sub(r'<script.*?</script>', '', text, flags=re.S)
body = re.sub(r'<[^>]+>', ' ', body)
body = ' '.join(body.split())

print()
print('  remaining:')
for label, pat in [
    ('em-dash', '—'),
    ('en-dash', '–'),
    ('bukan sekadar', 'bukan sekadar'),
    ('yang memang', 'yang memang'),
    ('tanpa perlu', 'tanpa perlu'),
]:
    n = body.count(pat)
    print('    %-16s %d' % (label, n))

if text != original:
    io.open(PATH, 'w', encoding='utf-8').write(text)
    print()
    print('  written')
else:
    print()
    print('  no changes')
