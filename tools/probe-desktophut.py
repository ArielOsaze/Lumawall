"""Probe a desktophut detail page for a direct video URL and its resolution.

Why: the catalogue needs 15000 entries and motionbgs supplies about 9600, so a second
source is required. desktophut advertises 67000+ live wallpapers, but its listing pages
carry no video URLs at all - the file is only revealed on a detail page. Whether it is
usable therefore has to be answered by opening a detail page, not by reading a listing.

Run: python tools/probe-desktophut.py
"""

import re
import ssl
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return r.read().decode("utf-8", "replace"), r.status


def main():
    # Take real slugs from the site's own sitemap rather than inventing one.
    index, _ = get("https://www.desktophut.com/sitemap.xml")
    subs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", index)
    item_maps = [s for s in subs if "app-sitemap" in s]
    print("  item sitemaps: %d" % len(item_maps))
    print()

    if not item_maps:
        print("  no item sitemap found")
        return 1

    page, _ = get(item_maps[0])
    slugs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", page)
    print("  %d slugs on the first page" % len(slugs))
    print()

    # Open a few and look for a video.
    checked = 0
    with_video = 0
    for url in slugs[:5]:
        try:
            html, status = get(url)
        except Exception as e:
            print("  %-70s %s" % (url[-70:], getattr(e, "code", type(e).__name__)))
            continue

        checked += 1
        videos = sorted(set(re.findall(r"https?://[^\"'\s<>]+\.(?:mp4|webm)", html)))
        hd = [v for v in videos if re.search(r"(1080|2160|1440|4k|hd)", v, re.I)]
        print("  %s" % url[-74:])
        print("    %d bytes, %d video URL(s), %d HD" % (len(html), len(videos), len(hd)))
        for v in videos[:3]:
            print("      %s" % v[:110])

        # The resolution, and the licence, if either is stated.
        for label, pattern in [
            ("resolution", r'(\d{3,4})\s*[x×]\s*(\d{3,4})'),
            ("og:video", r'property="og:video[^"]*"\s+content="([^"]+)"'),
            ("licence", r"(CC0|CC-BY|Creative Commons|royalty[- ]free|free to use)"),
        ]:
            hits = re.findall(pattern, html, re.I)
            if hits:
                print("      %-10s %s" % (label, str(hits[:3])[:100]))
        print()

        if videos:
            with_video += 1

    print("  %d of %d detail pages carried a video URL" % (with_video, checked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
