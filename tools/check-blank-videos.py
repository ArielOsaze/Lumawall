"""Find catalogue entries whose video is blank - black, white, or a single flat colour.

Why this exists
---------------
"kenapa di catalog ada bbrp wallpaper yg cuma item" - some wallpapers show as nothing but
black. A catalogue of 22879 entries cannot be watched by hand, and a thumbnail is not
evidence: the thumbnail is a separate image the source site serves, so it can look fine
while the video itself is a black frame or a file that decodes to nothing.

This downloads the first part of each sampled video, decodes a frame from the middle of
what it got, and measures the frame. A frame is reported as blank when its pixels are
nearly uniform - the standard deviation of luminance is tiny - whatever the colour is.
That catches black, white and flat grey alike, which matters because a "white screen"
wallpaper is the same fault as a black one.

It also reports the frame's mean luminance, so a genuinely dark wallpaper (a night scene)
is distinguishable from an empty one: a night scene has structure, so its deviation is
high even when its mean is low.

Usage:
    python tools/check-blank-videos.py --sample 60
    python tools/check-blank-videos.py --sample 60 --json build/blank-report.json
"""

import argparse
import concurrent.futures as cf
import json
import random
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / 'LumaWall' / 'catalog.json'

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120 Safari/537.36',
    # desktophut and moewalls both check this.
    'Referer': 'https://www.desktophut.com/',
}

FFMPEG = shutil.which('ffmpeg') or shutil.which('ffmpeg.exe')
FFPROBE = shutil.which('ffprobe') or shutil.which('ffprobe.exe')


def safe_url(url):
    from urllib.parse import quote, urlsplit, urlunsplit
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%:@&=+$,~()!'*-._")
    query = quote(parts.query, safe="/%:@&=+$,~()!'*-._?=&")
    return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def fetch_head(url, want=2_000_000, timeout=60):
    """The first `want` bytes of the file. Enough for a frame from most videos."""
    req = urllib.request.Request(safe_url(url), headers={**UA, 'Range': 'bytes=0-%d' % want})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read()


def fetch_all(url, limit=60_000_000, timeout=180):
    """The whole file, up to `limit` bytes.

    Needed because a lot of these files are not faststart: the `moov` atom - the index
    ffmpeg needs before it can decode anything - sits at the END of the file. A range
    request for the first two megabytes of such a file contains no index, so ffmpeg reports
    "no frame decoded" and the entry looks broken when it is only un-indexed. Eight of the
    first sixty sampled entries failed exactly that way.
    """
    req = urllib.request.Request(safe_url(url), headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        data = r.read(limit)
    return data


def frame_stats(url, tmpdir):
    """Decode frames and describe them. Returns None when nothing could be decoded.

    Several frames are taken, not one, because a single frame cannot tell a blank video
    from a dark moment: a scene that fades in from black, or a title card, is genuinely
    black for a second and perfectly fine afterwards. A video is only reported as blank
    when EVERY sampled frame is blank.
    """
    try:
        data = fetch_head(url)
    except Exception as e:
        return {'error': 'fetch: %s' % type(e).__name__}

    if len(data) < 20000:
        return {'error': 'too small (%d bytes)' % len(data)}

    name = re.sub(r'[^A-Za-z0-9]+', '_', url)[-70:] + '.bin'
    path = Path(tmpdir) / name
    path.write_bytes(data)

    # Try the head first; if ffmpeg cannot find an index, fetch the whole file, because
    # these are often not faststart and the index lives at the end.
    frames = extract_frames(path, tmpdir, name)
    if not frames:
        try:
            full = fetch_all(url)
        except Exception as e:
            return {'error': 'full fetch: %s' % type(e).__name__}
        if len(full) < 20000:
            return {'error': 'too small (%d bytes)' % len(full)}
        path.write_bytes(full)
        frames = extract_frames(path, tmpdir, name)

    if not frames:
        return {'error': 'no frame decoded'}

    # The blankest frame decides: a wallpaper that is black for most of its length is a
    # black wallpaper, whatever the other frames look like.
    worst = min(frames, key=lambda f: f['std'])
    darkest = min(frames, key=lambda f: f['mean'])
    result = dict(worst)
    result['darkest_mean'] = darkest['mean']
    result['frames'] = len(frames)
    result['black_fraction'] = max(f['black_fraction'] for f in frames)
    return result


def extract_frames(path, tmpdir, name, count=4):
    """Decode `count` frames spread across the clip and measure each."""
    out = []
    for i, at in enumerate([1.5, 4.0, 8.0, 14.0]):
        png = Path(tmpdir) / ('%s.%d.png' % (name, i))
        cmd = [FFMPEG, '-v', 'error', '-y', '-ss', str(at), '-i', str(path),
               '-frames:v', '1', '-vf', 'scale=160:-2', str(png)]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            continue
        if not png.exists():
            continue
        try:
            im = Image.open(png).convert('RGB')
        except Exception:
            continue
        a = np.asarray(im).astype(np.float64)
        lum = a.mean(axis=2)
        out.append({
            'mean': float(lum.mean()),
            'std': float(lum.std()),
            'min': float(lum.min()),
            'max': float(lum.max()),
            'channel_range': float(a.max(axis=2).mean() - a.min(axis=2).mean()),
            # The share of pixels that are essentially black. A wallpaper that is 99%
            # black with a faint logo in the corner reads as "just black" on a desktop,
            # which is the complaint - even though its deviation is not zero.
            'black_fraction': float((lum < 12.0).mean()),
            'size': list(im.size),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', type=int, default=60)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--json', default='')
    args = ap.parse_args()

    if not FFMPEG:
        print('  ffmpeg is required to decode a frame. Install it first.')
        return 1

    entries = json.loads(CATALOG.read_text(encoding='utf-8'))
    random.seed(args.seed)
    sample = random.sample(entries, min(args.sample, len(entries)))

    print('  catalogue : %d entries' % len(entries))
    print('  sampling  : %d' % len(sample))
    print()

    tmpdir = tempfile.mkdtemp(prefix='lw-blank-')
    results = []
    try:
        with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(frame_stats, e['videoUrl'], tmpdir): e for e in sample}
            done = 0
            for future in cf.as_completed(futures):
                e = futures[future]
                try:
                    stats = future.result()
                except Exception as exc:
                    stats = {'error': '%s' % type(exc).__name__}
                done += 1
                results.append((e, stats))
                if done % 10 == 0:
                    print('    %d/%d' % (done, len(sample)))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print()

    blank = []
    unreadable = []
    fine = []
    for e, stats in results:
        if stats is None or 'error' in stats:
            unreadable.append((e, stats.get('error') if stats else 'unknown'))
            continue
        # Blank means the desktop would show nothing: either the frame has no structure at
        # all (a flat colour), or it is almost entirely black with only a speck of detail.
        # The second test is what catches a wallpaper that is 99% black with a small logo,
        # which reads as "just black" to the user even though its deviation is not zero.
        flat = stats['std'] < 3.0
        mostly_black = stats['black_fraction'] > 0.97 and stats['mean'] < 20.0
        if flat or mostly_black:
            stats = dict(stats)
            stats['why'] = 'flat colour' if flat else 'almost all black'
            blank.append((e, stats))
        else:
            fine.append((e, stats))

    print('  readable  : %d' % len(fine + blank))
    print('  unreadable: %d' % len(unreadable))
    print('  BLANK     : %d' % len(blank))
    print()

    if blank:
        print('  blank frames:')
        for e, s in blank[:25]:
            print('    %-38s %-16s mean=%5.1f std=%4.1f black=%4.0f%%'
                  % (e['title'][:38], s['why'], s['mean'], s['std'],
                     s['black_fraction'] * 100))
        print()

    if unreadable:
        print('  could not be read:')
        for e, why in unreadable[:10]:
            print('    %-40s %s' % (e['title'][:40], why))
        print()

    # The darkest readable frames, so a dark-but-real wallpaper can be eyeballed.
    dark = sorted(fine, key=lambda t: t[1]['mean'])[:5]
    if dark:
        print('  darkest readable frames (structure present, so not blank):')
        for e, s in dark:
            print('    %-40s mean=%5.1f std=%4.1f' % (e['title'][:40], s['mean'], s['std']))

    if args.json:
        out = ROOT / args.json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            'sampled': len(sample),
            'blank': [{'title': e['title'], 'videoUrl': e['videoUrl'], **s} for e, s in blank],
            'unreadable': [{'title': e['title'], 'videoUrl': e['videoUrl'], 'why': w}
                           for e, w in unreadable],
            'fine': [{'title': e['title'], 'mean': s['mean'], 'std': s['std']} for e, s in fine],
        }, indent=2, ensure_ascii=False), encoding='utf-8')
        print()
        print('  wrote %s' % out.relative_to(ROOT))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
