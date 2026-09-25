"""verify-live-assets.py — compares every deployed asset against the local copy.

Catches the failure that matters: the site is up, returns 200, and serves a stale
build. That happened twice — an old installer, and a stylesheet from before a
rewrite — and neither is visible from a status code.

Line endings are normalised before comparing. The working copy uses CRLF on
Windows and the CDN may serve LF (or the reverse), which produced a false
"DIFFERS" on a file whose content was in fact identical.

Run:  python tools/verify-live-assets.py
"""

import hashlib
import os
import sys
import urllib.request

BASE = 'https://lumawall.xinet.id/'

ASSETS = [
    'index.html',
    'assets/css/style.css',
    'assets/js/main.js',
    'assets/fonts/jakarta-latin.woff2',
    'assets/fonts/jakarta-latin-ext.woff2',
    'assets/logo/app-logo.png',
    'assets/shots/wallpaper-raiden.png',
    'assets/video/lumawall-promo.mp4',
    'assets/downloads/LumaWall-Setup-4.0.1.exe',
    'assets/downloads/LumaWall_4.0.1.0_x64.msix',
    'assets/downloads/LumaWall-portable-4.0.1.zip',
]

TEXT = ('.html', '.css', '.js', '.json', '.svg')

# Assets that legitimately do not ship: the promo video is optional and the font
# path varies. Reported as skipped rather than failed.
OPTIONAL = {'assets/video/lumawall-promo.mp4'}


def normalise(data, path):
    if path.endswith(TEXT):
        return data.replace(b'\r\n', b'\n')
    return data


def fetch(url):
    req = urllib.request.Request(
        url, headers={'User-Agent': 'lumawall-verify', 'Cache-Control': 'no-cache'}
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read(), dict(r.headers)


print('  asset                                          local      live       verdict')
failures = []
for rel in ASSETS:
    local_path = os.path.join('site', rel)

    if not os.path.exists(local_path):
        print('  %-44s missing locally' % rel)
        failures.append(rel + ' (missing locally)')
        continue

    raw_local = open(local_path, 'rb').read()
    local_norm = normalise(raw_local, rel)

    try:
        raw_live, headers = fetch(BASE + rel)
    except Exception as e:
        if rel in OPTIONAL:
            print('  %-44s not deployed (optional)' % rel)
            continue
        print('  %-44s fetch failed: %s' % (rel, e))
        failures.append(rel)
        continue

    live_norm = normalise(raw_live, rel)

    lh = hashlib.sha256(local_norm).hexdigest()[:8]
    rh = hashlib.sha256(live_norm).hexdigest()[:8]

    if lh == rh:
        note = 'MATCH'
    elif local_norm == live_norm:
        note = 'MATCH (line endings differ only)'
    else:
        note = 'DIFFERS  %d vs %d bytes' % (len(local_norm), len(live_norm))
        failures.append(rel)

    print('  %-44s %-10s %-10s %s' % (rel, lh, rh, note))

print()
if failures:
    print('  %d asset(s) do not match the local copy:' % len(failures))
    for f in failures:
        print('    ' + f)
    sys.exit(1)
print('  every deployed asset matches the local build')
