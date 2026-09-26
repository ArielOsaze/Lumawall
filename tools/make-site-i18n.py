"""make-site-i18n.py — build the English site from the Indonesian one.

Why a generated page rather than a language switcher:

A page that swaps its text with JavaScript is ONE URL. A search engine indexes one
language and the other is invisible, so half the work of writing it is thrown away.
Two real documents - `/` and `/en/` - are each indexed on their own, and hreflang tells
a search engine they are the same page in two languages rather than two pages competing
with each other.

The Indonesian page is the SOURCE. This script reads it, replaces every text node and
every head value through the table in site/assets/js/site-copy.js, and writes
site/en/index.html. Structure is therefore identical by construction - only the words
differ - so the two pages cannot drift in layout.

What it rewrites:
  · <html lang>, <title>, meta description, og:*, twitter:*
  · every text node that matches a key in the table
  · the structured data (SoftwareApplication, FAQPage, WebSite) - re-derived from the
    English page's own text, so the schema cannot describe the Indonesian answers
  · the video source, so the English page plays the English render
  · hreflang links on BOTH pages, and the canonical on each

Usage:
    python tools/make-site-i18n.py
"""

import html
import json
import os
import re
import shutil
import sys

SITE = 'site'
INDEX = os.path.join(SITE, 'index.html')
EN_DIR = os.path.join(SITE, 'en')
EN_INDEX = os.path.join(EN_DIR, 'index.html')

BASE = 'https://lumawall.xinet.id'

# The English promo. The Indonesian page keeps its own.
VIDEO_ID = 'lumawall-promo'
VIDEO_EN = 'lumawall-promo-en'


def read(p):
    return open(p, encoding='utf-8').read()


def table(lang):
    """The site copy table for a language, parsed out of site-copy.js.

    Parsed rather than duplicated here: the table is the single source of the words, and
    a second copy in Python is the one that goes stale.
    """
    src = read(os.path.join(SITE, 'assets', 'js', 'site-copy.js'))
    m = re.search(r'export const %s = \{(.*?)\n\};' % lang.upper(), src, re.S)
    if not m:
        return {}

    out = {}
    body = m.group(1)
    for em in re.finditer(r"^\s*'((?:[^'\\]|\\.)*)':", body, re.M):
        key = em.group(1).replace("\\'", "'").replace('\\\\', '\\')
        start = em.end()
        nxt = re.search(r"^\s*'(?:[^'\\]|\\.)*':", body[start:], re.M)
        chunk = body[start:start + nxt.start()] if nxt else body[start:]
        vm = re.search(r"'((?:[^'\\]|\\.)*)'", chunk, re.S)
        if vm:
            out[key] = vm.group(1).replace("\\'", "'").replace('\\\\', '\\')
    return out


def translate_html(s, tbl):
    """Replace every text node and every head value that is a key in the table.

    The table's keys hold the text with its whitespace collapsed to single spaces, and
    the page has the same paragraph wrapped across several lines with indentation. So
    the lookup is done on the collapsed form - matching raw text would miss every
    paragraph longer than one line, which is most of the page's body copy.
    """
    changed = []
    missing = []

    # ── text nodes ───────────────────────────────────────────────────────────
    def repl(m):
        open_tag, body, close_tag = m.group(1), m.group(2), m.group(3)
        text = body.strip()
        if not text or '{' in text:
            return m.group(0)

        collapsed = re.sub(r'\s+', ' ', text)
        # The page uses HTML entities for punctuation (`&middot;`, `&rsaquo;`) and the
        # table holds the character they stand for, so the lookup decodes them. Two
        # strings missed without this - the version line and the uninstall answer - and
        # a miss here is silent: the English page renders the Indonesian sentence.
        decoded = re.sub(r'\s+', ' ', html.unescape(collapsed))

        for candidate in (collapsed, decoded):
            if candidate in tbl:
                if tbl[candidate] != candidate:
                    changed.append(candidate)
                # The replacement is plain text, so the entities in the original are
                # replaced by their characters - which is correct and reads the same.
                return '%s%s%s' % (open_tag, tbl[candidate], close_tag)

        # Not a key. Report it if it looks like prose - punctuation, numbers and
        # one-word labels are not translatable, and listing them buries the misses.
        if re.search(r'[A-Za-zÀ-ÿ]{4,}', decoded) and len(decoded) > 12:
            missing.append(decoded)
        return m.group(0)

    s = re.sub(r'(<[a-zA-Z][\w-]*\b[^>]*>)([^<>{}]+)(</[a-zA-Z][\w-]*>)', repl, s)

    # ── text that shares its parent with an element ──────────────────────────
    #
    # A button like `<a ...><svg>...</svg> Unduh gratis </a>` has its label as a text
    # node beside an element, not inside one - so the pattern above cannot see it, and
    # five button labels on the English page stayed in Indonesian. This pass finds a
    # text run that sits directly after a closing tag and before another opening one.
    def repl_beside(m):
        before, text, after = m.group(1), m.group(2), m.group(3)
        stripped = text.strip()
        if not stripped:
            return m.group(0)
        collapsed = re.sub(r'\s+', ' ', html.unescape(stripped))
        if collapsed in tbl and tbl[collapsed] != collapsed:
            changed.append(collapsed)
            # Keep one space either side so the label does not touch the icon.
            return '%s %s %s' % (before, tbl[collapsed], after)
        return m.group(0)

    s = re.sub(r'(</(?:svg|span|i|b|em)>)([^<>{}]+)(<(?:/)?[a-zA-Z])', repl_beside, s)

    # ── text followed by a line break ────────────────────────────────────────
    #
    # `<h1>Wallpaper hidup di setiap monitor.<br> <span>...</span></h1>` has its first
    # line as a text node that ends at a `<br>`, not at a closing tag - so neither
    # pattern above sees it, and the English page's main heading kept its Indonesian
    # first line. The heading is the single most important string on the page.
    def repl_br(m):
        before, text = m.group(1), m.group(2)
        stripped = text.strip()
        if not stripped:
            return m.group(0)
        collapsed = re.sub(r'\s+', ' ', html.unescape(stripped))
        if collapsed in tbl and tbl[collapsed] != collapsed:
            changed.append(collapsed)
            return '%s%s<br>' % (before, tbl[collapsed])
        return m.group(0)

    s = re.sub(r'(>) ?([^<>{}]+?)<br\s*/?>', repl_br, s)

    # ── attributes that carry copy ───────────────────────────────────────────
    for attr in ('content', 'placeholder', 'aria-label', 'alt', 'title'):
        def repl_attr(m, attr=attr):
            val = m.group(2)
            collapsed = re.sub(r'\s+', ' ', val)
            if collapsed in tbl and tbl[collapsed] != collapsed:
                changed.append(collapsed)
                return '%s="%s"' % (m.group(1), tbl[collapsed])
            return m.group(0)
        s = re.sub(r'(%s)="([^"]*)"' % attr, repl_attr, s)

    return s, changed, missing


def set_html_lang(s, lang):
    return re.sub(r'<html\s+lang="[^"]*"', '<html lang="%s"' % lang, s, count=1)


def set_hreflang(s, canonical_url, alt_url, alt_lang, default_url, default_lang):
    """Replace any existing hreflang block with a correct one.

    hreflang is what stops the two pages competing: without it a search engine sees two
    pages with the same content and picks one, discarding the other.

    The parameters are (this page's url, the other page's url, the other page's
    language, the default url, the default language). The first version of this function
    passed the same language for both entries, so the English page declared itself as
    the Indonesian alternate - which tells a search engine the two pages are the same
    language, defeating the whole point.
    """
    s = re.sub(r'\n\s*<link\s+rel="alternate"\s+hreflang="[^"]*"[^>]*>', '', s)
    this_lang = 'id' if alt_lang == 'en' else 'en'
    block = (
        '\n<link rel="alternate" hreflang="%s" href="%s">'
        '\n<link rel="alternate" hreflang="%s" href="%s">'
        '\n<link rel="alternate" hreflang="x-default" href="%s">'
    ) % (this_lang, canonical_url, alt_lang, alt_url, default_url)
    m = re.search(r'(<link\s+rel="canonical"[^>]*>)', s)
    if m:
        return s[:m.end()] + block + s[m.end():]
    return s


def set_og_locale(s, locale):
    """og:locale must match the page's language.

    Facebook and several other platforms read it to decide which audience the link is
    for. Left as id_ID on the English page, the English link is served to the Indonesian
    audience - which is the opposite of what the page is for.
    """
    if re.search(r'property="og:locale"', s):
        return re.sub(r'(<meta\s+property="og:locale"\s+content=")[^"]*(")',
                      r'\g<1>%s\g<2>' % locale, s, count=1)
    return s


def set_og_url(s, url):
    """og:url must be the page's own URL, not the site root.

    A wrong og:url makes a platform treat every share as the same page, so shares of
    the English page are credited to the Indonesian one and the English page never
    accumulates any.
    """
    if re.search(r'property="og:url"', s):
        return re.sub(r'(<meta\s+property="og:url"\s+content=")[^"]*(")',
                      r'\g<1>%s\g<2>' % url, s, count=1)
    return s


def set_og_image(s, url):
    """A page in another language needs its own card, or the preview is in the wrong one."""
    for prop in ('og:image', 'twitter:image'):
        if re.search(r'property="%s"|name="%s"' % (prop, prop), s):
            s = re.sub(r'((?:property|name)="%s"\s+content=")[^"]*(")' % prop,
                       r'\g<1>%s\g<2>' % url, s, count=1)
    return s


def set_canonical(s, url):
    if re.search(r'<link\s+rel="canonical"', s):
        return re.sub(r'<link\s+rel="canonical"[^>]*>',
                      '<link rel="canonical" href="%s">' % url, s, count=1)
    return s


def rewrite_video(s, name):
    """Point the page at a different promo render.

    The video block names its file with a content hash, so this replaces the stem and
    clears the hash - deliberately NOT leaving whatever hash was there. The hash
    belongs to the Indonesian render's bytes, and the English render is a different
    file with a different hash, so copying it across produced a reference to
    `lumawall-promo-en.18231fc9a2.mp4` - a file that does not exist. A missing video
    is not silent on the server side (the page returns 200 and the HTML is valid) and
    it is the one thing the visitor came to watch.

    So the reference is left unhashed here and cache-bust.py gives it the hash of the
    file that actually exists. Same path the Indonesian poster takes, and it means
    this script never has to know anything about file contents.
    """
    return re.sub(r'(assets/video/)' + re.escape(VIDEO_ID) + r'(\.[0-9a-f]+)?\.mp4',
                  lambda m: m.group(1) + name + '.mp4', s)


def rewrite_og_card(s):
    """Give the English page its own share card.

    og:image was left pointing at the Indonesian card, so an English link previewed
    with an Indonesian thumbnail - a preview the visitor cannot read, on the page
    whose entire purpose is to be readable in English. Nothing about the page itself
    showed the fault; it only appears when the link is pasted somewhere.

    Unhashed, like the poster, so cache-bust.py supplies the right hash.
    """
    return re.sub(r'(assets/shots/)og-card(\.[0-9a-f]+)?\.png',
                  lambda m: m.group(1) + 'og-card-en.png', s)


def rewrite_poster(s):
    """Give the English page its own poster, so the still is English too.

    The English poster's content hash is NOT the same as the Indonesian one - they
    are different images and cache-bust.py hashes content - so this cannot copy the
    hash across. It did exactly that in its first version, and the result was an
    English page pointing at `poster-promo-en.759c8626ec.png`, a file that does not
    exist. A missing poster is silent: the video block still plays, and only a visitor
    whose browser blocks autoplay sees a blank rectangle.

    So the reference is rewritten to the plain name and cache-bust.py gives it the
    right hash afterwards, which is the same path the Indonesian poster takes.
    """
    return re.sub(r'assets/shots/poster-promo(\.[0-9a-f]+)?\.png',
                  'assets/shots/poster-promo-en.png', s)


def rebuild_schema(s, lang):
    """Rebuild the structured data from the page's own text.

    The FAQ schema has to describe THIS page's questions. Copying the Indonesian schema
    into the English page would make the schema describe answers the page does not give,
    which is a quality problem a search engine treats as a fault - and it is invisible,
    because the page renders perfectly.
    """
    faq = []
    for q, body in re.findall(r'<summary[^>]*>(.*?)</summary>(.*?)</details>', s, re.S):
        q = html.unescape(re.sub(r'<[^>]+>', '', q)).strip()
        m = re.search(r'<p[^>]*>(.*?)</p>', body, re.S)
        if not m:
            continue
        a = html.unescape(re.sub(r'<[^>]+>', '', m.group(1)))
        a = re.sub(r'\s+', ' ', a).strip()
        if q and a:
            faq.append((q, a))

    schemas = []

    # SoftwareApplication - the existing one, with its text fields translated.
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    if m:
        try:
            app = json.loads(m.group(1))
            if app.get('@type') == 'SoftwareApplication':
                app['description'] = app.get('description', '')
                schemas.append(app)
        except json.JSONDecodeError:
            pass

    if faq:
        schemas.append({
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            'inLanguage': '%s-%s' % (lang, lang.upper()),
            'mainEntity': [
                {'@type': 'Question', 'name': q,
                 'acceptedAnswer': {'@type': 'Answer', 'text': a}}
                for q, a in faq
            ],
        })

    schemas.append({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'name': 'LumaWall',
        'alternateName': 'LumaWall - Live Wallpaper for Windows' if lang == 'en'
                         else 'LumaWall - Wallpaper Hidup untuk Windows',
        'url': BASE + ('/en/' if lang == 'en' else '/'),
        'inLanguage': '%s-%s' % (lang, lang.upper()),
        'publisher': {'@type': 'Organization', 'name': 'Xinet Group',
                      'url': 'https://xinet.id'},
    })

    # Replace every existing block with the rebuilt set.
    s = re.sub(r'<script type="application/ld\+json">.*?</script>\s*', '', s, flags=re.S)
    block = ''.join('<script type="application/ld+json">%s</script>\n'
                    % json.dumps(sc, ensure_ascii=False, separators=(',', ':'))
                    for sc in schemas)
    m = re.search(r'</head>', s)
    if m:
        s = s[:m.start()] + block + s[m.start():]
    return s


def main():
    if not os.path.exists(INDEX):
        print('  no %s' % INDEX)
        return 1

    tbl = table('en')
    if not tbl:
        print('  could not read the EN table from site-copy.js')
        return 1
    print('  %d English strings in the table' % len(tbl))

    src = read(INDEX)

    # ── the Indonesian page gets its hreflang, so the pair is linked ─────────
    id_page = set_canonical(src, BASE + '/')
    id_page = set_hreflang(id_page, BASE + '/', BASE + '/en/', 'en', BASE + '/', 'id')
    if id_page != src:
        open(INDEX, 'w', encoding='utf-8', newline='\n').write(id_page)
        print('  index.html: canonical + hreflang written')

    # ── the English page ─────────────────────────────────────────────────────
    en, changed, missing = translate_html(src, tbl)
    en = set_html_lang(en, 'en')
    en = set_canonical(en, BASE + '/en/')
    # this page = /en/ (en), the other = / (id), default = /
    en = set_hreflang(en, BASE + '/en/', BASE + '/', 'id', BASE + '/', 'id')
    en = set_og_locale(en, 'en_US')
    en = set_og_url(en, BASE + '/en/')
    en = rewrite_video(en, VIDEO_EN)
    en = rewrite_poster(en)
    en = rewrite_og_card(en)
    en = rebuild_schema(en, 'en')

    os.makedirs(EN_DIR, exist_ok=True)
    open(EN_INDEX, 'w', encoding='utf-8', newline='\n').write(en)

    print('  en/index.html: %d text node(s) translated' % len(changed))

    # ── what is left in Indonesian ───────────────────────────────────────────
    #
    # A text node that has letters and is not a key is either deliberately untranslated
    # (a product name, a number) or a miss. Reporting them is the only way to see a
    # miss: the page renders perfectly either way.
    if missing:
        # De-duplicate, and drop the ones that are obviously not copy.
        uniq = []
        for t in missing:
            if t not in uniq and not re.fullmatch(r'[\d\s.,%×x·/+-]+', t):
                uniq.append(t)
        if uniq:
            print()
            print('  %d text node(s) have no English entry:' % len(uniq))
            for t in uniq[:24]:
                print('    · %s' % t[:76])

    # ── the assets the English page needs ────────────────────────────────────
    #
    # The English page is at /en/, so every relative asset path would resolve against
    # /en/ and 404. Rewriting them to absolute is what makes the page work from a
    # subdirectory at all.
    en = read(EN_INDEX)
    en2 = re.sub(r'(src|href)="(?!https?:|/|#|mailto:)([^"]+)"',
                 lambda m: '%s="/%s"' % (m.group(1), m.group(2)), en)
    # ...except the two links that are meant to stay relative within /en/.
    en2 = en2.replace('href="/./"', 'href="/"')
    if en2 != en:
        open(EN_INDEX, 'w', encoding='utf-8', newline='\n').write(en2)
        print('  en/index.html: asset paths made absolute (the page lives in /en/)')

    print()
    print('  built %s' % EN_INDEX)
    return 0


if __name__ == '__main__':
    sys.exit(main())
