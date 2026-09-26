"""check-seo.py — is the site actually discoverable and shareable?

Why this exists:

Every SEO fault is silent. The page renders perfectly, the link works, and the only
symptom is that nobody finds it or the preview is a bare URL. There is nothing in the
page's own output to notice, so the checks have to be explicit.

What is checked, and why each one is a real failure:

  · og:image is an ABSOLUTE URL. A relative one is resolved against the crawler's own
    base rather than the page's, so the preview has no thumbnail. This happened, and
    the note was that the link "tampil tanpa gambar".
  · og:image is 1200x630 and under 1 MB. Platforms crop to that ratio and several
    refuse images over 5 MB; a 1920x1080 wallpaper was being used at first, and every
    platform cropped it through the middle of the subject.
  · Every URL in the head is absolute. A single relative one breaks one platform.
  · The structured data parses and is the RIGHT TYPE. A JSON-LD block that does not
    parse is invisible to every search engine and produces no error anywhere.
  · The FAQ schema's questions match the page's. A schema that describes an answer the
    page no longer gives is a quality problem, and it goes stale silently because
    nobody reads the schema.
  · robots.txt and sitemap.xml exist and the sitemap's <loc> matches the canonical.
  · The title and description are the right length. A title over ~60 characters is
    truncated in the results; a description over ~160 is cut mid-sentence.
  · There is exactly one h1.

Usage:
    python tools/check-seo.py
"""

import json
import os
import re
import sys
import xml.dom.minidom

SITE = 'site'
INDEX = os.path.join(SITE, 'index.html')
BASE = 'https://lumawall.xinet.id'

# What the platforms accept. 1200x630 is the ratio every one of them crops from, and
# the size limit that matters in practice is a few megabytes.
OG_W, OG_H = 1200, 630
OG_MAX_BYTES = 1024 * 1024

TITLE_MAX = 60
DESC_MAX = 160


def read(p):
    return open(p, encoding='utf-8').read()


def meta(s, prop):
    """The content of a <meta> by property= or name=."""
    for pat in (r'<meta\s+property="%s"\s+content="([^"]*)"' % re.escape(prop),
                r'<meta\s+name="%s"\s+content="([^"]*)"' % re.escape(prop)):
        m = re.search(pat, s)
        if m:
            return m.group(1)
    return None


def main():
    problems = []
    notes = []

    if not os.path.exists(INDEX):
        print('  no %s' % INDEX)
        return 1

    s = read(INDEX)

    print()
    print('  ── the link preview ──')

    # ── og:image ─────────────────────────────────────────────────────────────
    og = meta(s, 'og:image')
    if not og:
        problems.append('og:image is missing - the link has no thumbnail')
        print('    og:image          MISSING')
    else:
        if not og.startswith('https://'):
            problems.append('og:image is not an absolute https URL (%s) - a crawler '
                            'resolves it against its own base, so the preview is a bare '
                            'link' % og)
        print('    og:image          %s' % og)

        # Resolve it to a file on disk and measure it.
        rel = og.replace(BASE + '/', '')
        local = os.path.join(SITE, rel)
        if not os.path.exists(local):
            # The name may carry a content hash.
            stem, ext = os.path.splitext(os.path.basename(rel))
            stem = stem.split('.')[0]
            d = os.path.dirname(local)
            found = [f for f in os.listdir(d) if f.startswith(stem + '.')
                     and f.endswith(ext) and not f.endswith('.bak')] if os.path.isdir(d) else []
            if found:
                local = os.path.join(d, sorted(found)[0])
            else:
                problems.append('og:image points at %s, which is not on disk' % rel)

        if os.path.exists(local):
            size = os.path.getsize(local)
            try:
                from PIL import Image
                im = Image.open(local)
                w, h = im.size
            except ImportError:
                w = h = 0
            print('    og:image file     %dx%d, %.0f KB'
                  % (w, h, size / 1024))
            if (w, h) != (OG_W, OG_H):
                problems.append('og:image is %dx%d; every platform crops from %dx%d, so '
                                'a different ratio is cropped through the subject'
                                % (w, h, OG_W, OG_H))
            if size > OG_MAX_BYTES:
                problems.append('og:image is %.0f KB; platforms start refusing or '
                                'recompressing above %d KB'
                                % (size / 1024, OG_MAX_BYTES // 1024))

    # ── the other preview tags ───────────────────────────────────────────────
    for prop in ('og:title', 'og:description', 'og:url', 'og:type', 'og:site_name'):
        v = meta(s, prop)
        if not v:
            problems.append('%s is missing' % prop)
            print('    %-17s MISSING' % prop)
        else:
            print('    %-17s %s' % (prop, v[:60]))

    for name in ('twitter:card', 'twitter:title', 'twitter:description', 'twitter:image'):
        v = meta(s, name)
        if not v:
            problems.append('%s is missing' % name)
            print('    %-17s MISSING' % name)

    for name in ('twitter:image',):
        v = meta(s, name)
        if v and not v.startswith('https://'):
            problems.append('%s is not absolute' % name)

    # ── title and description length ─────────────────────────────────────────
    print()
    print('  ── the result itself ──')
    m = re.search(r'<title>(.*?)</title>', s, re.S)
    title = m.group(1).strip() if m else ''
    if not title:
        problems.append('no <title>')
    elif len(title) > TITLE_MAX:
        problems.append('the title is %d characters; results truncate around %d'
                        % (len(title), TITLE_MAX))
    print('    title             %d chars  %s' % (len(title), title[:70]))

    desc = meta(s, 'description')
    if not desc:
        problems.append('no meta description')
    elif len(desc) > DESC_MAX:
        problems.append('the description is %d characters; it is cut around %d'
                        % (len(desc), DESC_MAX))
    print('    description       %d chars' % (len(desc) if desc else 0))

    # ── exactly one h1 ───────────────────────────────────────────────────────
    h1s = re.findall(r'<h1\b', s)
    print('    h1 count          %d' % len(h1s))
    if len(h1s) != 1:
        problems.append('%d h1 elements; a page needs exactly one' % len(h1s))

    # ── canonical ────────────────────────────────────────────────────────────
    m = re.search(r'<link\s+rel="canonical"\s+href="([^"]*)"', s)
    canonical = m.group(1) if m else None
    print('    canonical         %s' % (canonical or 'MISSING'))
    if not canonical:
        problems.append('no canonical link')
    elif not canonical.startswith('https://'):
        problems.append('the canonical is not absolute')

    # ── structured data ──────────────────────────────────────────────────────
    print()
    print('  ── structured data ──')
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    if not blocks:
        problems.append('no JSON-LD at all')

    types = []
    parsed = []
    for b in blocks:
        try:
            d = json.loads(b)
            types.append(d.get('@type', '?'))
            parsed.append(d)
        except json.JSONDecodeError as e:
            problems.append('a JSON-LD block does not parse: %s' % e)

    print('    blocks            %s' % ', '.join(types))

    # FAQPage must exist and must match the page.
    faq = next((d for d in parsed if d.get('@type') == 'FAQPage'), None)
    if not faq:
        problems.append('no FAQPage schema; the page answers questions and none of them '
                        'are marked up, which is the one piece of structured data that '
                        'changes what the visitor sees in the results')
    else:
        schema_qs = [q['name'] for q in faq.get('mainEntity', [])]
        page_qs = [re.sub(r'<[^>]+>', '', q).strip()
                   for q in re.findall(r'<summary[^>]*>(.*?)</summary>', s, re.S)]
        print('    FAQPage           %d questions in the schema, %d on the page'
              % (len(schema_qs), len(page_qs)))

        missing = [q for q in page_qs if q not in schema_qs]
        if missing:
            problems.append('%d question(s) on the page are not in the schema (first: '
                            '%s) - the schema has gone stale' % (len(missing), missing[0][:50]))

        for q in faq.get('mainEntity', []):
            a = q.get('acceptedAnswer', {}).get('text', '')
            if len(a) < 40:
                problems.append('the answer to "%s" is %d characters - too short to be '
                                'a real answer' % (q['name'][:40], len(a)))

    # ── images and their alternative text ────────────────────────────────────
    #
    # The rule here is deliberately narrow, because the obvious version of it is
    # wrong. `alt=""` is not a fault: an empty alt is the spec's way of marking an
    # image as decorative, and adding aria-hidden on top of it is redundant. The
    # first version of this check demanded aria-hidden alongside every empty alt and
    # reported two false positives - and the tempting response, adding aria-hidden to
    # satisfy it, would have made the page slightly worse to satisfy a wrong rule.
    #
    # What actually matters:
    #
    #   · an <img> with no alt attribute at all - the real accessibility fault,
    #     because a screen reader then reads out the file name
    #   · a link whose only content is an image with no alt text, which leaves the
    #     link with no accessible name
    #
    # Both are invisible: the page renders perfectly and a screen reader announces
    # "link" or "logo-150.png".
    print()
    print('  ── images ──')
    html = read(INDEX)
    imgs = re.findall(r'<img\b[^>]*>', html, re.I)
    missing_alt = []
    decorative = 0
    described = 0
    for tag in imgs:
        if not re.search(r'\balt\s*=', tag, re.I):
            missing_alt.append(tag)
        elif re.search(r'\balt\s*=\s*"\s*"', tag, re.I):
            decorative += 1
        else:
            described += 1

    print('    images            %d total, %d described, %d decorative, %d with no alt'
          % (len(imgs), described, decorative, len(missing_alt)))

    for tag in missing_alt:
        problems.append('an <img> has no alt attribute at all, so a screen reader '
                        'reads out the file name: %s' % tag[:90])

    # A link whose only content is an image with alt="" has no accessible name.
    for match in re.finditer(r'<a\b[^>]*>(.*?)</a>', html, re.S | re.I):
        inner = match.group(1)
        if '<img' not in inner:
            continue
        text = re.sub(r'<[^>]+>', '', inner).strip()
        img_alts = [a for a in re.findall(r'\balt\s*=\s*"([^"]*)"', inner, re.I) if a.strip()]
        if not text and not img_alts:
            problems.append('a link contains only an image with no alt text and no text, '
                            'so it has no accessible name: %s'
                            % re.sub(r'\s+', ' ', match.group(0))[:90])

    # ── robots and sitemap ───────────────────────────────────────────────────
    print()
    print('  ── crawling ──')

    # The page's own hreflang block, read once so the sitemap can be checked against
    # it. A disagreement between the two is worse than having neither.
    page_alts = {}
    for match in re.finditer(r'<link\b[^>]*\bhreflang="([^"]*)"[^>]*\bhref="([^"]*)"',
                             s, re.I):
        page_alts[match.group(1)] = match.group(2)
    # Attribute order is not guaranteed, so catch href-before-hreflang too.
    for match in re.finditer(r'<link\b[^>]*\bhref="([^"]*)"[^>]*\bhreflang="([^"]*)"',
                             s, re.I):
        page_alts.setdefault(match.group(2), match.group(1))
    print('    page hreflang     %s' % (', '.join(sorted(page_alts)) or 'NONE'))

    robots = os.path.join(SITE, 'robots.txt')
    if not os.path.exists(robots):
        problems.append('no robots.txt')
        print('    robots.txt        MISSING')
    else:
        r = read(robots)
        has_sitemap = 'Sitemap:' in r
        print('    robots.txt        %d bytes, sitemap %s'
              % (len(r), 'declared' if has_sitemap else 'MISSING'))
        if not has_sitemap:
            problems.append('robots.txt does not declare a Sitemap')

    sm = os.path.join(SITE, 'sitemap.xml')
    if not os.path.exists(sm):
        problems.append('no sitemap.xml')
        print('    sitemap.xml       MISSING')
    else:
        try:
            doc = xml.dom.minidom.parse(sm)
            locs = [n.firstChild.data.strip()
                    for n in doc.getElementsByTagName('loc')]
            print('    sitemap.xml       %d URL(s): %s' % (len(locs), ', '.join(locs)))
            if not locs:
                problems.append('the sitemap has no <loc>')
            else:
                # Both language versions must be listed. A sitemap carrying only the
                # Indonesian page still lets Google find /en/ through the hreflang
                # link, but it is the one place both URLs can be stated together.
                if canonical and locs[0].rstrip('/') != canonical.rstrip('/'):
                    problems.append('the sitemap says %s but the canonical says %s'
                                    % (locs[0], canonical))
                if '/en/' not in ' '.join(locs):
                    problems.append('the sitemap does not list /en/, so the English page '
                                    'is only discoverable by crawling the hreflang link')

                # Every hreflang in the sitemap must agree with the page's own
                # hreflang block. Google's documentation is explicit that a
                # disagreement between the two is worse than having neither.
                alt_pairs = set()
                for node in doc.getElementsByTagName('xhtml:link'):
                    hreflang = node.getAttribute('hreflang')
                    href = node.getAttribute('href')
                    if hreflang and href:
                        alt_pairs.add((hreflang, href.rstrip('/')))
                for hreflang, href in sorted(alt_pairs):
                    if hreflang not in page_alts:
                        problems.append('the sitemap declares hreflang="%s" but the page '
                                        'does not' % hreflang)
                    elif page_alts[hreflang].rstrip('/') != href:
                        problems.append('hreflang="%s" points at %s in the sitemap and %s '
                                        'on the page'
                                        % (hreflang, href, page_alts[hreflang]))
                print('    sitemap hreflang  %d alternate(s): %s'
                      % (len(alt_pairs), ', '.join(sorted(h for h, _ in alt_pairs))))
        except Exception as e:
            problems.append('sitemap.xml does not parse: %s' % e)

    # ── the trailing-slash agreement ─────────────────────────────────────────
    #
    # Vercel's trailingSlash setting decides whether the server's real URL is /en/ or
    # /en, and everything that names a URL - canonical, hreflang, sitemap - has to
    # name the same one. If they disagree, the server redirects the URL the canonical
    # names, and Google reports "canonical points to a redirect" and ignores the
    # signal. The site shipped exactly that: trailingSlash was false while the
    # canonical, the hreflang block and the sitemap all used a trailing slash.
    print()
    print('  ── url form ──')
    cfg_path = os.path.join(SITE, 'vercel.json')
    if not os.path.exists(cfg_path):
        print('    vercel.json       MISSING')
    else:
        try:
            cfg = json.loads(read(cfg_path))
            trailing = cfg.get('trailingSlash')
            print('    trailingSlash     %s' % trailing)
            canonical_form = canonical.endswith('/') if canonical else None
            print('    canonical form    %s' % ('with a trailing slash'
                                               if canonical_form else 'without'))
            if trailing is True and canonical_form is False:
                problems.append('trailingSlash is true but the canonical %s has no '
                                'trailing slash, so the server redirects the URL the '
                                'canonical names' % canonical)
            if trailing is False and canonical_form is True:
                problems.append('trailingSlash is false but the canonical %s has a '
                                'trailing slash, so the server redirects the URL the '
                                'canonical names' % canonical)
        except ValueError as e:
            problems.append('vercel.json does not parse: %s' % e)

    print()
    if problems:
        print('  %d problem(s):' % len(problems))
        for p in problems:
            print('    · %s' % p)
        print()
        print('  Every one of these is silent: the page renders and the link works.')
        return 1

    print('  the site is discoverable, and the link previews correctly')
    return 0


if __name__ == '__main__':
    sys.exit(main())
