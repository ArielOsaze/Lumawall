"""Test a candidate site for direct HD video URLs before adding it as a source.

Why each check exists:
  * A listing page that shows no video URL is useless - the URL has to be in the HTML, not
    loaded by script, or collecting means running a browser.
  * A video URL that is not HD is the "pecah" the catalogue must not have.
  * robots.txt matters: a source that forbids crawling is not a source.
  * The licence has to permit free use, and it has to be stated on the page rather than
    assumed from the site's reputation.

Run: python tools/probe-source.py moewalls.com [more hosts...]
"""

import re
import ssl
import sys
import urllib.error
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace"), r.status


def check(host):
    base = "https://" + host
    print("=" * 74)
    print("  %s" % host)
    print("=" * 74)

    # 1. robots.txt
    try:
        text, _ = get(base + "/robots.txt")
        rules = [l.strip() for l in text.splitlines() if l.strip()]
        print("  robots.txt: %d rules" % len(rules))
        for line in rules[:6]:
            print("    %s" % line[:96])
    except Exception as e:
        print("  robots.txt: %s" % getattr(e, "code", type(e).__name__))
    print()

    # 2. The home page: does it carry video URLs, and a sitemap?
    try:
        html, _ = get(base)
    except Exception as e:
        print("  home failed: %s" % getattr(e, "code", type(e).__name__))
        return

    videos = sorted(set(re.findall(r'https?://[^"\'\s<>]+\.(?:mp4|webm)', html)))
    thumbs = sorted(set(re.findall(r'https?://[^"\'\s<>]+\.(?:jpg|jpeg|png|webp)', html)))
    hd = [v for v in videos if re.search(r"(1080|1440|2160|4k|1920)", v, re.I)]

    print("  home page: %d bytes" % len(html))
    print("    video URLs : %d (%d look HD)" % (len(videos), len(hd)))
    for v in videos[:3]:
        print("      %s" % v[:100])
    print("    image URLs : %d" % len(thumbs))
    print()

    # 3. A sitemap, which is how a large collection is enumerated without guessing.
    for path in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"):
        try:
            xml, _ = get(base + path)
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
            print("  %-18s %d loc" % (path, len(locs)))
            for l in locs[:5]:
                print("      %s" % l[:96])
            break
        except Exception as e:
            print("  %-18s %s" % (path, getattr(e, "code", type(e).__name__)))
    print()

    # 4. How a detail page exposes its video.
    links = re.findall(r'href="(/[a-z0-9\-]+/[a-z0-9\-]+/?)"', html)
    if links:
        detail = base + links[0]
        try:
            page, _ = get(detail)
            pv = sorted(set(re.findall(r'https?://[^"\'\s<>]+\.(?:mp4|webm)', page)))
            print("  detail: %s" % detail[:84])
            print("    %d bytes, %d video URL(s)" % (len(page), len(pv)))
            for v in pv[:4]:
                print("      %s" % v[:100])
            for label, pat in [
                ("resolution", r"(\d{3,4})\s*[x×]\s*(\d{3,4})"),
                ("licence", r"(CC0|CC-BY|Creative Commons|royalty[- ]free|free for personal|free to use)"),
                ("title", r'property="og:title"\s+content="([^"]{4,80})"'),
            ]:
                hits = re.findall(pat, page, re.I)
                if hits:
                    print("    %-10s %s" % (label, str(hits[:3])[:104]))
        except Exception as e:
            print("    detail failed: %s" % getattr(e, "code", type(e).__name__))
    else:
        print("  no detail links found on the home page")
    print()


def main():
    hosts = sys.argv[1:] or ["moewalls.com"]
    for host in hosts:
        try:
            check(host)
        except Exception as e:
            print("  %s: %s - %s" % (host, type(e).__name__, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
