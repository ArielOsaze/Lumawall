"""Give every motionbgs entry a thumbnail URL.

Why this exists
---------------
9697 entries in the catalogue - 42% of it - came from motionbgs and carried no
`thumbnailUrl` at all, because the scraper never recorded one. In the app's grid those
entries drew as black tiles, which is the complaint: "kenapa di catalog ada bbrp wallpaper
yg cuma item".

The site does serve a still for every video, and it is predictable from the video's own
URL. The video is

    https://motionbgs.com/media/5328/<slug>.3840x2160.mp4

and the still is the same path with the resolution suffix and the extension replaced:

    https://motionbgs.com/media/5328/<slug>.jpg

Verified against the live site: 200, content-type image/jpeg, real JPEG bytes.

This rewrites the catalogue in place, but only after checking a sample really serves an
image - a URL pattern that looks right and returns 404 for most entries would turn a black
grid into a broken grid, which is not an improvement.

Usage:
    python tools/add-motionbgs-thumbs.py --probe 40
    python tools/add-motionbgs-thumbs.py --apply
"""

import argparse
import concurrent.futures as cf
import json
import random
import re
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / 'LumaWall' / 'catalog.json'

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120 Safari/537.36',
    'Referer': 'https://motionbgs.com/',
}

# The video is .../media/<id>/<slug>.<W>x<H>.mp4 and the still is the same path with the
# resolution suffix REMOVED and the extension changed: .../media/<id>/<slug>.jpg.
#
# Verified against the live site. Keeping the resolution - <slug>.3840x2160.jpg - returns
# 404, which is the trap: the resolution looks like part of the name and it is not. An
# earlier attempt that kept it matched only 22% of entries; dropping it matches 78%.
VIDEO_RE = re.compile(r'^(https?://motionbgs\.com/media/\d+/[^/]+?)\.\d+x\d+\.mp4$')


def still_for(video_url):
    """The still image that belongs to a motionbgs video, or '' if the url is not one."""
    m = VIDEO_RE.match(video_url or '')
    return m.group(1) + '.jpg' if m else ''


def probe(url):
    """True when the url really serves an image."""
    try:
        req = urllib.request.Request(url, headers=UA, method='GET')
        with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
            head = r.read(4)
            ctype = (r.headers.get('Content-Type') or '').lower()
        return (head[:3] == b'\xff\xd8\xff' or head[:4] == b'\x89PNG'
                or head[:4] == b'RIFF' or 'image' in ctype)
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--probe', type=int, default=0, help='check this many before applying')
    ap.add_argument('--apply', action='store_true', help='write the catalogue')
    args = ap.parse_args()

    entries = json.loads(CATALOG.read_text(encoding='utf-8'))
    print('  catalogue: %d entries' % len(entries))

    missing = [e for e in entries if not (e.get('thumbnailUrl') or '').strip()]
    print('  without a thumbnail: %d' % len(missing))

    fixable = [e for e in missing if still_for(e.get('videoUrl'))]
    print('  of those, motionbgs with a derivable still: %d' % len(fixable))

    if not fixable:
        print()
        print('  nothing to do.')
        return 0

    if args.probe:
        random.seed(11)
        sample = random.sample(fixable, min(args.probe, len(fixable)))
        ok = 0
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for e, good in zip(sample, ex.map(lambda x: probe(still_for(x['videoUrl'])), sample)):
                if good:
                    ok += 1
                else:
                    print('    MISS  %s' % still_for(e['videoUrl']))
        print()
        print('  probed %d, served an image: %d (%.0f%%)'
              % (len(sample), ok, 100.0 * ok / len(sample)))
        if ok < len(sample):
            print()
            print('  Some stills are missing. The pattern is right but not universal, so')
            print('  applying it everywhere would leave broken images where there are')
            print('  black tiles now. Only apply if the miss rate is acceptable.')
        if not args.apply:
            return 0

    if not args.apply:
        print()
        print('  dry run - pass --apply to write the catalogue.')
        return 0

    # Verify every still before writing it.
    #
    # The pattern matches 78% of entries, so applying it blindly would leave 22% pointing
    # at a 404 - a black tile replaced by a broken image, which is not an improvement. The
    # ones that do not resolve are left with an empty thumbnailUrl, and the app draws its
    # own placeholder for those.
    print()
    print('  verifying %d stills (this is the slow part)' % len(fixable))
    verified = {}
    done = 0
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(probe, still_for(e['videoUrl'])): e for e in fixable}
        for future in cf.as_completed(futures):
            e = futures[future]
            done += 1
            try:
                good = future.result()
            except Exception:
                good = False
            if good:
                verified[id(e)] = still_for(e['videoUrl'])
            if done % 500 == 0:
                print('    %d/%d  verified %d' % (done, len(fixable), len(verified)))

    changed = 0
    for e in entries:
        if (e.get('thumbnailUrl') or '').strip():
            continue
        still = verified.get(id(e))
        if still:
            e['thumbnailUrl'] = still
            changed += 1

    CATALOG.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding='utf-8')
    print()
    print('  verified stills : %d of %d (%.0f%%)'
          % (len(verified), len(fixable), 100.0 * len(verified) / len(fixable)))
    print('  added to entries: %d' % changed)
    print('  wrote %s' % CATALOG.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
