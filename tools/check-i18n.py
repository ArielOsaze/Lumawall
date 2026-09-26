"""check-i18n.py — is the site actually bilingual, and is each page complete?

Why this exists:

Two faults, both silent, and both happened while building this:

  1. A BROKEN TABLE. An edit left a key outside its object and the closing brace on the
     wrong line, so site-copy.js was a syntax error. The generator then reported "could
     not read the EN table" and produced no English page - and a build that produces no
     page is not a build failure, it is a directory that stops being updated. The
     English site would have gone stale in place while every check passed.

  2. A PAGE THAT IS HALF TRANSLATED. The generator reports what it could not translate,
     but "not translated" is not an error it raises - the page renders perfectly with
     Indonesian sentences in it. Only a check that reads the output can see it.

So this validates the tables by loading them, and then reads both built pages and
confirms each one is in its own language.

Usage:
    python tools/check-i18n.py
"""

import json
import os
import re
import subprocess
import sys

SITE = 'site'
COPY = os.path.join(SITE, 'assets', 'js', 'site-copy.js')
ID_PAGE = os.path.join(SITE, 'index.html')
EN_PAGE = os.path.join(SITE, 'en', 'index.html')

BASE = 'https://lumawall.xinet.id'

# Indonesian words that must NOT appear in the English page's visible text. Chosen so
# each one is unambiguous - a word that exists in both languages would report a fault
# on a correct page, and a check that cries wolf gets ignored.
INDONESIAN_MARKERS = [
    'Wallpaper hidup', 'Unduh', 'Apakah', 'Bagaimana', 'tanpa iklan', 'Kamu bisa',
    'Tiap layar', 'Pilih, klik', 'Buka game', 'Gratis, tanpa', 'Dengan LumaWall',
    'lebih baru', 'mengunduh', 'pengaturan',
]

# English words that must appear in the English page - the positive direction, so a
# page that was emptied rather than translated is caught too.
ENGLISH_MARKERS = [
    'Live wallpaper', 'Download', 'Performance', 'Questions', 'Free',
]


def read(p):
    return open(p, encoding='utf-8').read()


def load_tables():
    """Load site-copy.js through node, so a syntax error is reported as one.

    Reading the file with a regex would find keys in a broken table and report it as
    fine - which is exactly the fault that produced no English page.
    """
    tmp = os.path.join('build', '_i18n_check.mjs')
    os.makedirs('build', exist_ok=True)
    open(tmp, 'w', encoding='utf-8').write(read(COPY))

    script = (
        "import('./%s').then(m => {"
        "  const id = Object.keys(m.ID || {}), en = Object.keys(m.EN || {});"
        "  process.stdout.write(JSON.stringify({id, en}));"
        "}).catch(e => { process.stderr.write(e.message); process.exit(1); });"
    ) % tmp.replace('\\', '/')

    r = subprocess.run(['node', '-e', script], capture_output=True, text=True,
                       timeout=60, cwd='.')
    if r.returncode != 0:
        return None, None, (r.stderr or r.stdout or 'unknown error').strip()[:300]
    try:
        d = json.loads(r.stdout)
        return d['id'], d['en'], None
    except (json.JSONDecodeError, KeyError):
        return None, None, 'the tables did not load as an object'


def visible(path):
    """The page's text, with scripts and styles removed."""
    s = read(path)
    s = re.sub(r'<script.*?</script>', '', s, flags=re.S)
    s = re.sub(r'<style.*?</style>', '', s, flags=re.S)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
    return s


def main():
    problems = []

    print()
    print('  i18n: is the site bilingual, and is each page complete?')
    print()

    # ── 1. the tables ────────────────────────────────────────────────────────
    if not os.path.exists(COPY):
        print('  no %s' % COPY)
        return 1

    id_keys, en_keys, err = load_tables()
    if err:
        print('  THE COPY TABLE DOES NOT LOAD:')
        print('    %s' % err)
        print()
        print('  A table that does not parse produces no English page at all, and the')
        print('  build reports nothing - the site just stops being updated.')
        return 1

    print('    site-copy.js     %d keys, %d English' % (len(id_keys), len(en_keys)))
    missing = [k for k in id_keys if k not in en_keys]
    extra = [k for k in en_keys if k not in id_keys]
    if missing:
        problems.append('%d key(s) have no English value' % len(missing))
        for k in missing[:8]:
            print('      · no English: %s' % k[:64])
    if extra:
        problems.append('%d English entr(ies) match no source string' % len(extra))
        for k in extra[:8]:
            print('      · no source: %s' % k[:64])

    # ── 2. the pages ─────────────────────────────────────────────────────────
    for label, path, lang in (('index.html', ID_PAGE, 'id'),
                              ('en/index.html', EN_PAGE, 'en')):
        print()
        if not os.path.exists(path):
            problems.append('%s does not exist' % path)
            print('    %-14s MISSING' % label)
            continue

        s = read(path)
        body = visible(path)

        m = re.search(r'<html\s+lang="([^"]*)"', s)
        html_lang = m.group(1) if m else None
        m = re.search(r'<link\s+rel="canonical"\s+href="([^"]*)"', s)
        canonical = m.group(1) if m else None
        m = re.search(r'<title>(.*?)</title>', s, re.S)
        title = m.group(1).strip() if m else ''

        print('    %-14s lang=%s  %d bytes' % (label, html_lang, len(s)))
        print('    %-14s canonical=%s' % ('', canonical or 'MISSING'))
        print('    %-14s title=%s' % ('', title[:58]))

        if html_lang != lang:
            problems.append('%s declares lang="%s" but is the %s page'
                            % (path, html_lang, lang))

        expected_canonical = BASE + ('/en/' if lang == 'en' else '/')
        if canonical != expected_canonical:
            problems.append('%s canonical is %s, expected %s'
                            % (path, canonical, expected_canonical))

        # hreflang: this page and the other one, plus x-default.
        alts = dict(re.findall(r'hreflang="([^"]*)"\s+href="([^"]*)"', s))
        print('    %-14s hreflang=%s' % ('', ', '.join(sorted(alts)) or 'MISSING'))
        if lang not in alts:
            problems.append('%s has no hreflang="%s" entry pointing at itself' % (path, lang))
        other = 'id' if lang == 'en' else 'en'
        if other not in alts:
            problems.append('%s has no hreflang="%s" entry for the other language'
                            % (path, other))
        if 'x-default' not in alts:
            problems.append('%s has no hreflang="x-default"' % path)

        # og:locale must match the page.
        m = re.search(r'property="og:locale"\s+content="([^"]*)"', s)
        og_locale = m.group(1) if m else None
        want_locale = 'en_US' if lang == 'en' else 'id_ID'
        print('    %-14s og:locale=%s' % ('', og_locale or 'MISSING'))
        if og_locale != want_locale:
            problems.append('%s og:locale is %s, expected %s'
                            % (path, og_locale, want_locale))

        # og:url must be this page.
        m = re.search(r'property="og:url"\s+content="([^"]*)"', s)
        og_url = m.group(1) if m else None
        if og_url != expected_canonical:
            problems.append('%s og:url is %s, expected %s'
                            % (path, og_url, expected_canonical))

        # ── the language of the visible text ─────────────────────────────────
        if lang == 'en':
            found = [w for w in INDONESIAN_MARKERS if w in body]
            if found:
                problems.append('%s still contains Indonesian: %s'
                                % (path, ', '.join(found[:5])))
                print('    %-14s INDONESIAN STILL PRESENT: %s' % ('', ', '.join(found[:5])))
            else:
                print('    %-14s no Indonesian text found' % '')

            absent = [w for w in ENGLISH_MARKERS if w not in body]
            if absent:
                problems.append('%s is missing expected English text: %s'
                                % (path, ', '.join(absent)))

        # A page must not point at the other language's video.
        m = re.search(r'<source\s+src="([^"]*lumawall-promo[^"]*)"', s)
        video = m.group(1) if m else ''
        want_en = '-en' in video
        if lang == 'en' and not want_en:
            problems.append('%s plays the Indonesian video (%s)' % (path, video))
        if lang == 'id' and want_en:
            problems.append('%s plays the English video (%s)' % (path, video))
        print('    %-14s video=%s' % ('', video.split('/')[-1] if video else 'MISSING'))

    print()
    if problems:
        print('  %d problem(s):' % len(problems))
        for p in problems:
            print('    · %s' % p)
        return 1

    print('  both pages exist, each in its own language, linked by hreflang')
    return 0


if __name__ == '__main__':
    sys.exit(main())
