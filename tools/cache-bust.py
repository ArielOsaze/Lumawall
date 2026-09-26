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

── why it handles two pages ────────────────────────────────────────────────

The site is bilingual, and the two pages reference some different assets: the English
promo, the English poster, the English share card. The first version of this script
processed one page from a hard-coded list, so those three files were never versioned
at all - and, worse, the English page was left pointing at the Indonesian video's
hash, which is a reference to a file that does not exist.

So it now walks every page, and each asset is looked up in each page independently.
An asset a page does not reference is skipped for that page rather than being blindly
name-replaced, because a blind replace on the wrong page is how a URL ends up doubled
or pointing at the other language's file.

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

# Every page that references long-cached assets. Order does not matter; the files are
# written at the end, after every page has been rewritten and verified.
PAGES = [
    os.path.join(SITE, 'index.html'),
    os.path.join(SITE, 'en', 'index.html'),
]

# Which assets are served with a long cache and therefore need a versioned URL.
# CSS and JS are included because they change just as often as the video does.
WATCHED = [
    'assets/video/lumawall-promo.mp4',
    'assets/video/lumawall-promo-en.mp4',
    'assets/video/hero-loop.mp4',
    'assets/css/style.css',
    'assets/css/fonts.css',
    'assets/js/main.js',
    'assets/shots/poster-promo.png',
    'assets/shots/poster-promo-en.png',
    # The share cards are fetched by crawlers rather than browsers, and a crawler that
    # has cached the old card will keep showing it. They belong on this list for the
    # same reason the video does.
    'assets/shots/og-card.png',
    'assets/shots/og-card-en.png',
    'assets/shots/hero-bg.jpg',
    # The app screenshots are served with a 24-hour cache and their names never
    # changed, so a re-captured screenshot was invisible for a day. That is the same
    # failure as the video's, at a shorter interval - and it happened: the window
    # controls in all four carried a hover highlight, and fixing them on disk would
    # still have shown the old images.
    'assets/shots/ui-discover.png',
    'assets/shots/ui-library.png',
    'assets/shots/ui-displays.png',
    'assets/shots/ui-performance.png',
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

    pages = [p for p in PAGES if os.path.exists(p)]
    if not pages:
        print('  no pages found; looked for %s' % ', '.join(PAGES))
        return 1

    # Read every page once. Each is rewritten in memory and written at the end, so a
    # failure part-way through cannot leave one page updated and the other stale.
    html = dict((p, io.open(p, encoding='utf-8').read()) for p in pages)
    original = dict(html)
    moved = []

    for rel in WATCHED:
        src = os.path.join(SITE, rel)
        folder, name = os.path.split(rel)
        stem, ext = os.path.splitext(name)
        folder_path = os.path.join(SITE, folder)

        # Which versioned name does each page currently reference for this asset?
        # It may be an OLD hash, which is exactly the state a re-render produces: the
        # file on disk is new, the html still points at the previous version, and the
        # old versioned file still exists. Treating "a versioned name exists" as "up
        # to date" skipped the update and shipped a page pointing at the old video -
        # the same failure this whole mechanism exists to prevent.
        ref_re = re.compile(re.escape(stem) + r'\.([0-9a-f]{%d})' % HASH_LEN + re.escape(ext))

        # Find this asset's reference in each page, independently.
        refs = {}
        for p in pages:
            m = ref_re.search(html[p])
            refs[p] = m.group(0) if m else None

        if not os.path.exists(src):
            # No base file. Either the pages are already correct, or the asset is gone.
            handled = False
            for p in pages:
                referenced_name = refs[p]
                if not referenced_name:
                    continue
                on_disk = os.path.join(folder_path, referenced_name)
                if not os.path.exists(on_disk):
                    print('  %-38s BROKEN - %s points at %s, which does not exist'
                          % (rel, os.path.basename(p), referenced_name))
                    return 1
                handled = True
                # The base file is gone because a previous run removed it after
                # versioning. The versioned file is therefore the asset, and it may
                # have been edited in place since - in which case its name carries a
                # hash of its OLD content and the browser will keep the old copy.
                # That is exactly how the video-autoplay fix would have shipped
                # invisibly.
                actual = digest(on_disk)
                if actual != ref_re.search(referenced_name).group(1):
                    stem_clean = re.sub(r'\.[0-9a-f]{%d}$' % HASH_LEN, '', stem)
                    fixed = '%s.%s%s' % (stem_clean, actual, ext)
                    if check_only:
                        print('  %-38s STALE in %s - name says %s, content is %s'
                              % (rel, os.path.basename(p),
                                 ref_re.search(referenced_name).group(1), actual))
                        continue
                    # Rename once, even if both pages reference it.
                    on_disk_abs = os.path.join(folder_path, referenced_name)
                    if os.path.exists(on_disk_abs):
                        os.rename(on_disk_abs, os.path.join(folder_path, fixed))
                    for q in pages:
                        if refs[q] == referenced_name:
                            html[q] = html[q].replace(referenced_name, fixed)
                    moved.append((rel, os.path.join(folder, fixed)))
                    print('  %-38s renamed to %s (content changed)' % (rel, fixed))
                else:
                    print('  %-38s up to date (%s)' % (rel, referenced_name))
                    break
            if not handled:
                print('  %-38s MISSING' % rel)
            continue

        want = versioned(rel, src)
        want_path = os.path.join(SITE, want)
        want_name = os.path.basename(want)

        # A page that does not reference this asset at all is skipped for it. This is
        # the English/Indonesian split: only one page references each promo.
        targets = [p for p in pages if refs[p] or name in html[p]]
        if not targets:
            continue

        if all(refs[p] == want_name for p in targets):
            print('  %-38s up to date' % rel)
            continue

        if check_only:
            for p in targets:
                print('  %-38s STALE in %s - has %s, file needs %s'
                      % (rel, os.path.basename(p), refs[p] or '(unversioned)', want_name))
            continue

        # Copy (not move) so a reference elsewhere cannot break, then point the pages
        # at the versioned copy.
        #
        # The replacement must be NAME for NAME. An earlier version replaced the old
        # name with the new full path, so `assets/shots/hero-bg.OLD.jpg` became
        # `assets/shots/assets/shots/hero-bg.NEW.jpg` - every asset 404'd, including
        # the promo video, and the page loaded with a broken hero and no video. The
        # live behaviour check caught it (4x "Failed to load resource: 404").
        shutil.copy2(src, want_path)
        for p in targets:
            if refs[p]:
                html[p] = html[p].replace(refs[p], want_name)
            else:
                html[p] = html[p].replace(name, want_name)
        moved.append((rel, want))

        # Any earlier versioned copy of this file is now dead weight: nothing in any
        # page references it, so it would sit in the deploy forever. A re-render
        # produces a new hash each time, and without this the assets folder
        # accumulates every past version.
        #
        # Checked against EVERY page's text, because a file referenced only by the
        # English page is not dead weight - and deleting it would break that page
        # while the Indonesian one looked fine.
        if os.path.isdir(folder_path):
            all_text = ''.join(html.values())
            for f in os.listdir(folder_path):
                if ref_re.fullmatch(f) and f != want_name and f not in all_text:
                    os.remove(os.path.join(folder_path, f))
                    print('    removed the superseded %s' % f)

    if check_only:
        return 1 if moved else 0

    # ── every reference must resolve ──────────────────────────────────────────
    #
    # A versioning step that rewrites URLs can break them, and a broken URL is
    # invisible from the server side: the page returns 200, the html is valid, and
    # the asset 404s in the browser. That happened - a name-for-path replacement
    # produced `assets/shots/assets/shots/hero-bg.jpg` and the promo video stopped
    # loading while every server-side check passed.
    #
    # So the rewrite is verified here, on every page, before anything is written.
    for p in pages:
        refs = set(re.findall(r'assets/[a-z]+/[a-zA-Z0-9._-]+\.[a-z0-9]+', html[p]))
        broken = [r for r in refs if not os.path.exists(os.path.join(SITE, r))]
        if broken:
            print()
            print('  REFUSING TO WRITE: %s has %d reference(s) that do not resolve:'
                  % (os.path.basename(p), len(broken)))
            for b in broken:
                print('    ' + b)
            return 1

        doubled = [r for r in refs if r.count('assets/') > 1]
        if doubled:
            print()
            print('  REFUSING TO WRITE: %s has %d doubled path(s):'
                  % (os.path.basename(p), len(doubled)))
            for d in doubled:
                print('    ' + d)
            return 1

    changed = [p for p in pages if html[p] != original[p]]
    if changed:
        for p in changed:
            io.open(p, 'w', encoding='utf-8', newline='\n').write(html[p])
        print()
        print('  updated:')
        for p in changed:
            print('    %s' % p)
        for rel, want in moved:
            print('      %-38s -> %s' % (rel, os.path.basename(want)))

        # Remove the unversioned originals now nothing points at them. Only after
        # every page has been written, because the two pages share several assets and
        # removing an original while one page still referenced it would 404 that page.
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
