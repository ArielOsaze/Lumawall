"""check-copy.py — flags the writing habits that read as machine-written.

The tells are structural, not vocabulary. This checks for the ones that were
actually present in this project's copy:

  · an em-dash used as a dramatic pause in body text (correct in a table cell
    meaning "not applicable", so those are allowed)
  · "bukan sekadar X, tapi Y" and relatives, which inflate a plain point
  · the same sentence shape repeated in consecutive headings
  · a sentence starting lowercase after a full stop, which is what a careless
    em-dash rewrite leaves behind
  · "Tidak ada X, tidak ada Y, dan tidak ada Z" - the tricolon

Run:  python tools/check-copy.py
"""

import io
import re
import sys

PATH = 'site/index.html'
PROMO_GLOB = 'promo/src/scenes/*.jsx'


def visible_text(html):
    """The text a visitor reads, with tags and scripts removed."""
    t = re.sub(r'<script.*?</script>', ' ', html, flags=re.S)
    t = re.sub(r'<style.*?</style>', ' ', t, flags=re.S)
    t = re.sub(r'<!--.*?-->', ' ', t, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    return ' '.join(t.split())


def headings(html):
    out = []
    for tag in ('h1', 'h2', 'h3'):
        for m in re.finditer(r'<%s[^>]*>(.*?)</%s>' % (tag, tag), html, re.S):
            out.append((tag, ' '.join(re.sub(r'<[^>]+>', ' ', m.group(1)).split())))
    return out


html = io.open(PATH, encoding='utf-8').read()
text = visible_text(html)
problems = []

print('  copy checks:')

# ── em-dash ──────────────────────────────────────────────────────────────────
# Allowed only inside a table cell, where it means "not applicable".
body_without_cells = re.sub(r'<td[^>]*>[^<]*</td>', ' ', html)
body_text = visible_text(body_without_cells)
dashes = body_text.count('—')
print('    em-dash outside table cells : %d' % dashes)
if dashes:
    problems.append('em-dash used as punctuation (%d)' % dashes)
    for m in re.finditer(r'.{0,60}—.{0,60}', body_text):
        print('      %s' % m.group(0).strip()[:110])

# ── inflated contrast ────────────────────────────────────────────────────────
for phrase in ['bukan sekadar', 'bukan hanya', 'bukan cuma sekadar']:
    n = text.count(phrase)
    print('    "%-16s" : %d' % (phrase, n))
    if n:
        problems.append('"%s" (%d)' % (phrase, n))

# ── filler ───────────────────────────────────────────────────────────────────
for phrase in ['yang memang', 'tanpa perlu', 'dirancang supaya', 'perlu diketahui', 'pada dasarnya']:
    n = text.count(phrase)
    print('    "%-16s" : %d' % (phrase, n))
    if n:
        problems.append('"%s" (%d)' % (phrase, n))

# ── repeated construction across headings ───────────────────────────────────
#
# The failure that matters is one construction used for several headings, which
# makes them read as a template: "Decode di GPU, bukan CPU", "Berhenti per layar,
# bukan semua", "Reaksi dari event, bukan polling" - the same "X, bukan Y" shape
# three times.
#
# A generic shape comparison is useless here: reducing every word to a placeholder
# made unrelated headings look identical. Matching the constructions by name is
# both simpler and correct.
CONSTRUCTIONS = [
    ('X, bukan Y', r'^[^,]+,\s*bukan\s+\S+'),
    ('Dalam N ...', r'^dalam\s+\d'),
]

hs = [h for _, h in headings(html)]
found = {}
for h in hs:
    for name, pat in CONSTRUCTIONS:
        if re.match(pat, h, re.I):
            found.setdefault(name, []).append(h)

repeated = sum(1 for v in found.values() if len(v) > 1)
print('    repeated constructions      : %d' % repeated)
for name, items in found.items():
    if len(items) > 1:
        print('      %s used %d times:' % (name, len(items)))
        for it in items:
            print('        "%s"' % it[:52])
        problems.append('%s used for %d headings' % (name, len(items)))

# ── lowercase sentence start ─────────────────────────────────────────────────
lower = re.findall(r'\.\s+[a-z][a-z]+', text)
print('    sentences starting lowercase : %d' % len(lower))
for l in lower[:5]:
    print('      ...%s' % l)
if lower:
    problems.append('lowercase after a full stop (%d)' % len(lower))

# ── tricolon ─────────────────────────────────────────────────────────────────
tri = re.findall(r'Tidak ada \w+[^.]*, tidak ada \w+[^.]*, dan tidak ada \w+', text)
print('    "tidak ada X, Y, dan Z"      : %d' % len(tri))
if tri:
    problems.append('tricolon (%d)' % len(tri))

# ── the promo's on-screen copy ───────────────────────────────────────────────
print()
print('  promo copy:')
import glob
promo_issues = 0
for p in sorted(glob.glob(PROMO_GLOB)):
    src = io.open(p, encoding='utf-8').read()
    for m in re.finditer(r'(?:text="([^"]{6,})"|>([^<>{}\n]{8,})<)', src):
        line = ' '.join((m.group(1) or m.group(2) or '').split())
        for phrase in ['bukan sekadar', 'yang memang', 'tanpa perlu']:
            if phrase in line:
                print('    %s: "%s"' % (p.split('/')[-1], line[:60]))
                promo_issues += 1
        if '—' in line:
            print('    %s: em-dash in "%s"' % (p.split('/')[-1], line[:60]))
            promo_issues += 1
if not promo_issues:
    print('    clean')

print()
if problems:
    print('  %d issue(s):' % len(problems))
    for p in problems:
        print('    ' + p)
    sys.exit(1)
print('  copy is clean')
