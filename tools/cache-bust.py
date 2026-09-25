"""cache-bust.py — gives every long-cached asset a content hash in its URL.

Why this exists, and the bug it explains:

vercel.json serves /assets/video/ with `max-age=604800, immutable` - seven days. The
filenames never changed, so a browser that had fetched the promo once kept using its
own copy for a week. Every re-render was invisible to that browser: the file on the
server was new, `curl` saw the new bytes, and the user watched the OLD video and
reported the same problems again.

That is what happened here. The promo was re-rendered five times, each time fixing
exactly what was reported - and the reports kept describing the first version.

`immutable` is the right policy for a hashed URL and the wrong policy for a stable
one. So the URL becomes the version: `<name>.<hash>.mp4`. A new render changes the
hash, the URL changes with it, and the browser fetches it. The old file can be
deleted, because nothing references it any more.

Run:  python tools/cache-bust.py [--check]
      --check reports whether the references are current without changing anything.
"""

import hashlib
import io
import os
import re
import shutil
import sys

SITE = 'site'
INDEX = os.path.join(SITE, 'index.html')

# Which assets are served with a long cache and therefore need a versioned URL.
# CSS and JS are included because they change just as often as the video does.
WATCHED = [
    'assets/video/lumawall-promo.mp4',
    'assets/video/hero-loop.mp4',
    'assets/css/style.css',
    'assets/css/fonts.css',
    'assets/js/main.js',
    'assets/shots/poster-promo.png',
    'assets/shots/hero-bg.jpg',
]

HASH_LEN = 10


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:HASH_LEN]


def versioned(rel, path):
    """assets/video/x.mp4  ->  assets/video/x.<hash>.mp4"""
    folder, name = os.path.split(rel)
    stem, ext = os.path.splitext(name)
    # Strip a hash that is already there, so re-running does not stack them.
    stem = re.sub(r'\.[0-9a-f]{%d}$' % HASH_LEN, '', stem)
    return os.path.join(folder, '%s.%s%s' % (stem, digest(path), ext))


def main():
    check_only = '--check' in sys.argv

    html = io.open(INDEX, encoding='utf-8').read()
    original = html
    moved = []

    for rel in WATCHED:
        src = os.path.join(SITE, rel)
        folder, name = os.path.split(rel)
        stem, ext = os.path.splitext(name)
        folder_path = os.path.join(SITE, folder)

        # Which versioned name does the html currently reference for this asset?
        # It may be an OLD hash, which is exactly the state a re-render produces: the
        # file on disk is new, the html still points at the previous version, and the
        # old versioned file still exists. Treating "a versioned name exists" as "up
        # to date" skipped the update and shipped a page pointing at the old video -
        # the same failure this whole mechanism exists to prevent.
        ref_re = re.compile(re.escape(stem) + r'\.([0-9a-f]{%d})' % HASH_LEN + re.escape(ext))
        refs = ref_re.findall(html)
        referenced = ref_re.search(html)
        referenced_name = referenced.group(0) if referenced else None

        if not os.path.exists(src):
            # No base file. Either the html is already correct, or the asset is gone.
            if referenced_name:
                on_disk = os.path.join(folder_path, referenced_name)
                if os.path.exists(on_disk):
                    print('  %-38s up to date (%s)' % (rel, referenced_name))
                    continue
                print('  %-38s BROKEN - html points at %s, which does not exist'
                      % (rel, referenced_name))
                return 1
            print('  %-38s MISSING' % rel)
            continue

        want = versioned(rel, src)
        want_path = os.path.join(SITE, want)

        if referenced_name == os.path.basename(want):
            print('  %-38s up to date' % rel)
            continue

        if check_only:
            print('  %-38s STALE - html has %s, file needs %s'
                  % (rel, referenced_name or '(unversioned)', os.path.basename(want)))
            continue

        # Copy (not move) so a reference elsewhere cannot break, then point the html
        # at the versioned copy.
        shutil.copy2(src, want_path)
        if referenced_name:
            html = html.replace(referenced_name, want.replace(os.sep, '/'))
        else:
            html = html.replace(rel, want.replace(os.sep, '/'))
        moved.append((rel, want))

        # Any earlier versioned copy of this file is now dead weight: nothing in the
        # html references it, so it would sit in the deploy forever. A re-render
        # produces a new hash each time, and without this the assets folder
        # accumulates every past version.
        if os.path.isdir(folder_path):
            for f in os.listdir(folder_path):
                if ref_re.fullmatch(f) and f != os.path.basename(want) and f not in html:
                    os.remove(os.path.join(folder_path, f))
                    print('    removed the superseded %s' % f)

    if check_only:
        stale = [l for l in moved]
        return 1 if stale else 0

    if html != original:
        io.open(INDEX, 'w', encoding='utf-8').write(html)
        print()
        print('  index.html updated:')
        for rel, want in moved:
            print('    %-38s -> %s' % (rel, os.path.basename(want)))

        # Remove the unversioned originals now nothing points at them.
        for rel, _ in moved:
            src = os.path.join(SITE, rel)
            if os.path.exists(src):
                os.remove(src)
                print('    removed the unversioned %s' % rel)
    else:
        print()
        print('  nothing to do - every reference is already versioned')

    return 0


if __name__ == '__main__':
    sys.exit(main())
