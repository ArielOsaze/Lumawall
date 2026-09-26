"""make-seo.py — the SEO files the site was missing.

What was missing, and why each one matters:

  · robots.txt          Without it, a crawler has no explicit permission and no
                        sitemap location. It defaults to "allowed", but it also has
                        nowhere to learn where the sitemap is.
  · sitemap.xml         The one file that tells a search engine which URLs exist. With
                        one page it is short, and it still has to exist: a crawler that
                        finds a sitemap indexes sooner and re-crawls on change.
  · FAQPage schema      The page already answers ten questions, and none of them were
                        marked up. FAQPage is what turns those answers into an
                        expandable block under the result in Google - it is the single
                        highest-value piece of structured data a page like this can
                        carry, because it is the only one that changes what the visitor
                        SEES on the results page rather than just describing the page.

The FAQ text is read out of index.html rather than typed here. Two copies of the same
answer drift, and the copy in the schema is the one nobody looks at - so it is the one
that goes stale without anyone noticing. Reading it means the schema cannot disagree
with the page.

The SoftwareApplication schema already existed and is left alone; this adds FAQPage and
WebSite beside it, and writes the two files.

Run:  python tools/make-seo.py
"""

import html
import json
import os
import re
import sys

SITE = 'site'
INDEX = os.path.join(SITE, 'index.html')
BASE = 'https://lumawall.xinet.id'

# How many questions to mark up. Google shows a handful; all ten are included because
# the schema is what a search engine reads, and the display limit is Google's business.
MAX_FAQ = 10


def read(p):
    return open(p, encoding='utf-8').read()


def faq_from_page():
    """The FAQ questions and answers, read out of the rendered page.

    The page uses <details><summary>question</summary> ... <p>answer</p></details>.
    Reading it means the schema and the page cannot disagree - a schema that describes
    an answer the page no longer gives is worse than no schema, because Google treats
    the mismatch as a quality problem.
    """
    s = read(INDEX)
    i = s.find('Pertanyaan yang paling sering')
    if i < 0:
        return []

    seg = s[i:i + 12000]
    out = []
    for q, body in re.findall(r'<summary[^>]*>(.*?)</summary>(.*?)</details>', seg, re.S):
        q = html.unescape(re.sub(r'<[^>]+>', '', q)).strip()
        m = re.search(r'<p[^>]*>(.*?)</p>', body, re.S)
        if not m:
            continue
        a = html.unescape(re.sub(r'<[^>]+>', '', m.group(1)))
        a = re.sub(r'\s+', ' ', a).strip()
        # A schema answer should be the whole answer, not a truncated one. The page
        # holds a paragraph per question, so this is it.
        if q and a:
            out.append({'q': q, 'a': a})
    return out[:MAX_FAQ]


def build_faq_schema(faq):
    return {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        'mainEntity': [
            {
                '@type': 'Question',
                'name': f['q'],
                'acceptedAnswer': {'@type': 'Answer', 'text': f['a']},
            }
            for f in faq
        ],
    }


def build_website_schema():
    """The site itself.

    WebSite tells a search engine the site's name and its language, which is what
    produces the site name above the result rather than the bare domain. InLanguage is
    the part that matters here: the page is in Indonesian and the app is distributed to
    an Indonesian-speaking audience, so saying so is worth more than the rest of it.
    """
    return {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'name': 'LumaWall',
        'alternateName': 'LumaWall - Wallpaper Hidup untuk Windows',
        'url': BASE + '/',
        'inLanguage': 'id-ID',
        'publisher': {
            '@type': 'Organization',
            'name': 'Xinet Group',
            'url': 'https://xinet.id',
        },
    }


def write_sitemap():
    """One page, with its real lastmod.

    The date comes from the file's own mtime rather than from today. A sitemap that
    claims the page changed every time the sitemap is regenerated trains a crawler to
    ignore lastmod, which is the opposite of the point.
    """
    import datetime
    mtime = os.path.getmtime(INDEX)
    lastmod = datetime.datetime.utcfromtimestamp(mtime).strftime('%Y-%m-%d')

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url>\n'
        '    <loc>%s/</loc>\n'
        '    <lastmod>%s</lastmod>\n'
        '    <changefreq>weekly</changefreq>\n'
        '    <priority>1.0</priority>\n'
        '  </url>\n'
        '</urlset>\n'
    ) % (BASE, lastmod)
    open(os.path.join(SITE, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n').write(xml)
    return lastmod


def write_robots():
    """Permission, and where the sitemap is.

    The download folder is disallowed deliberately. The installer is 15 MB and is not a
    page; letting a crawler walk into it wastes crawl budget on a binary and can put
    the .exe in a search result, which is worse than not being indexed.

    The assets are allowed - the screenshots and the poster are what appear in image
    search and in link previews, and a crawler that cannot fetch them cannot render the
    preview.
    """
    txt = (
        'User-agent: *\n'
        'Allow: /\n'
        '\n'
        '# The installer and the portable build are downloads, not pages.\n'
        'Disallow: /assets/downloads/\n'
        '\n'
        'Sitemap: %s/sitemap.xml\n'
    ) % BASE
    open(os.path.join(SITE, 'robots.txt'), 'w', encoding='utf-8', newline='\n').write(txt)


def inject_schema(schemas):
    """Put the new schemas in the page's <head>, replacing any previous copy.

    Replaced rather than appended: this runs on every build, and appending would add a
    second FAQPage on the second run. A page with two FAQPage blocks is a schema error.
    """
    s = read(INDEX)

    marker_start = '<!-- seo-schema:start -->'
    marker_end = '<!-- seo-schema:end -->'
    block = marker_start + '\n'
    for sc in schemas:
        block += ('<script type="application/ld+json">%s</script>\n'
                  % json.dumps(sc, ensure_ascii=False, separators=(',', ':')))
    block += marker_end

    if marker_start in s:
        s = re.sub(re.escape(marker_start) + r'.*?' + re.escape(marker_end),
                   block, s, flags=re.S)
    else:
        # After the existing SoftwareApplication block, so all the structured data sits
        # together in the head.
        m = re.search(r'<script type="application/ld\+json">.*?</script>\s*', s, re.S)
        if not m:
            print('  could not find where to put the schema')
            return False
        s = s[:m.end()] + block + '\n' + s[m.end():]

    open(INDEX, 'w', encoding='utf-8', newline='\n').write(s)
    return True


def main():
    if not os.path.exists(INDEX):
        print('  no %s' % INDEX)
        return 1

    faq = faq_from_page()
    if not faq:
        print('  no FAQ found in the page - the schema would describe nothing')
        return 1

    print('  FAQ read from the page: %d questions' % len(faq))
    for f in faq:
        print('    · %s' % f['q'][:64])

    schemas = [build_faq_schema(faq), build_website_schema()]
    if not inject_schema(schemas):
        return 1
    print('  FAQPage + WebSite schema written into index.html')

    lastmod = write_sitemap()
    print('  sitemap.xml written (lastmod %s)' % lastmod)

    write_robots()
    print('  robots.txt written')

    # ── and validate what was written ────────────────────────────────────────
    #
    # A JSON-LD block that does not parse is invisible to every search engine and
    # produces no error anywhere, which is exactly the failure mode this whole file
    # exists to prevent. So every block in the page is parsed back.
    s = read(INDEX)
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    print()
    print('  validating %d schema block(s):' % len(blocks))
    types = []
    for b in blocks:
        try:
            d = json.loads(b)
            types.append(d.get('@type', '?'))
        except json.JSONDecodeError as e:
            print('    INVALID: %s' % e)
            return 1
    print('    %s' % ', '.join(types))

    import xml.dom.minidom
    try:
        xml.dom.minidom.parse(os.path.join(SITE, 'sitemap.xml'))
        print('    sitemap.xml parses')
    except Exception as e:
        print('    sitemap.xml INVALID: %s' % e)
        return 1

    print()
    print('  SEO files complete')
    return 0


if __name__ == '__main__':
    sys.exit(main())
