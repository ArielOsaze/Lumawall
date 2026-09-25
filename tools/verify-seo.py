"""verify-seo.py — checks the page's metadata the way a crawler reads it.

A page can look correct and still produce a bare link with no thumbnail, because
every failure here is silent:

  · a relative og:image resolves against the crawler's base, not the page's
  · a missing og:url makes the canonical ambiguous
  · an image smaller than 1200x630 is rejected or cropped by most platforms
  · a description over ~160 characters is truncated mid-sentence in a result

This fetches the LIVE page, so it also catches a deploy that did not include the
metadata.

Run:  python tools/verify-seo.py [url]
"""

import re
import sys
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else 'https://lumawall.xinet.id/'

print('  fetching %s' % URL)
req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (compatible; LumaWallSEO/1.0)'})
with urllib.request.urlopen(req, timeout=60) as r:
    html = r.read().decode('utf-8', 'replace')

head = html[:html.find('</head>')] if '</head>' in html else html

problems = []


def meta(attr, name):
    m = re.search(r'<%s[^>]*%s=["\']([^"\']+)["\']' % (attr, name), head)
    return m.group(1) if m else None


def check(label, value, ok, detail=''):
    state = 'OK  ' if ok else 'FAIL'
    shown = (value or '(missing)')
    if len(shown) > 74:
        shown = shown[:71] + '...'
    print('    %s  %-26s %s' % (state, label, shown))
    if detail and not ok:
        print('           %s' % detail)
    if not ok:
        problems.append(label)


print()
print('  identity:')
title = re.search(r'<title>(.*?)</title>', head, re.S)
title = title.group(1).strip() if title else None
check('title', title, bool(title) and 15 <= len(title) <= 65,
      'a title outside 15-65 characters is truncated or looks thin in a result')

desc = meta('meta', 'name="description"')
check('description', desc, bool(desc) and 50 <= len(desc or '') <= 165,
      'a description over ~165 characters is cut mid-sentence')

canonical = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', head)
check('canonical', canonical.group(1) if canonical else None,
      bool(canonical) and (canonical.group(1) or '').startswith('https://'))

print()
print('  sharing:')
og_title = meta('meta', 'property="og:title"')
og_desc = meta('meta', 'property="og:description"')
og_url = meta('meta', 'property="og:url"')
og_img = meta('meta', 'property="og:image"')
og_type = meta('meta', 'property="og:type"')

check('og:title', og_title, bool(og_title))
check('og:description', og_desc, bool(og_desc) and len(og_desc or '') <= 200)
check('og:url', og_url, bool(og_url) and (og_url or '').startswith('https://'),
      'without an absolute og:url the canonical is ambiguous')
check('og:type', og_type, bool(og_type))

# The one that matters most, and the one that was broken: a relative og:image
# silently produces no thumbnail.
check('og:image is absolute', og_img,
      bool(og_img) and (og_img or '').startswith('https://'),
      'a relative og:image resolves against the crawler base, not the page')

check('og:image:width', meta('meta', 'property="og:image:width"'), True)
check('og:image:height', meta('meta', 'property="og:image:height"'), True)
check('og:image:alt', meta('meta', 'property="og:image:alt"'), True)

check('twitter:card', meta('meta', 'name="twitter:card"'),
      meta('meta', 'name="twitter:card"') in ('summary_large_image', 'summary'))
check('twitter:image', meta('meta', 'name="twitter:image"'),
      (meta('meta', 'name="twitter:image"') or '').startswith('https://'))

# ── the image itself ─────────────────────────────────────────────────────────
print()
print('  the share image:')
if og_img and og_img.startswith('https://'):
    try:
        req = urllib.request.Request(og_img, headers={'User-Agent': 'LumaWallSEO/1.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
            ctype = r.headers.get('content-type', '')

        # Read the dimensions out of the PNG header rather than decoding it.
        w = h = None
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            w = int.from_bytes(data[16:20], 'big')
            h = int.from_bytes(data[20:24], 'big')

        print('    %s  %-26s %s' % ('OK  ' if data else 'FAIL', 'reachable',
                                    '%d bytes, %s' % (len(data), ctype)))
        print('    %s  %-26s %s' % (
            'OK  ' if (w and h) else 'FAIL', 'dimensions',
            '%dx%d' % (w, h) if w else 'could not read'))

        if not w or w < 1200 or h < 630:
            problems.append('the share image is smaller than 1200x630')
        # Anything much wider than 1.91:1 is centre-cropped by the platforms.
        if w and h and w / h > 2.2:
            problems.append('the share image is wider than 1.91:1 and will be cropped')
    except Exception as e:
        problems.append('the share image could not be fetched: %s' % e)
        print('    FAIL  %-26s %s' % ('reachable', e))

print()
print('  structured data:')
blocks = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', head, re.S)
if blocks:
    import json
    for b in blocks:
        try:
            d = json.loads(b)
            print('    OK    %-26s %s' % ('valid JSON-LD', d.get('@type')))
            for field in ('name', 'applicationCategory', 'operatingSystem', 'offers'):
                if field not in d:
                    problems.append('structured data is missing %s' % field)
        except Exception as e:
            problems.append('structured data is not valid JSON: %s' % e)
            print('    FAIL  %-26s %s' % ('valid JSON-LD', e))
else:
    problems.append('no structured data')
    print('    FAIL  %-26s none' % 'structured data')

print()
if problems:
    print('  %d problem(s):' % len(problems))
    for p in problems:
        print('    ' + p)
    sys.exit(1)
print('  the metadata is complete and the share image is usable')
