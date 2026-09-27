"""Harvest motionbgs slugs from every tag page, which reach past the sitemap.

Why: the sitemap lists 9664 detail pages and the catalogue needs 15000. Tag pages carry
media ids the sitemap does not - ids in the 10050-10191 range appear on a tag page while the
sitemap stops around 10120 - so the site's own index is incomplete and the tag pages are the
part it omits. This walks all of them and records every slug they link to.

Run: python tools/harvest-tag-slugs.py
"""

import concurrent.futures as cf
import json
import re
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "catalog-scrape"
EXTRA = OUT / "tag-slugs.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def slugs_on(html):
    """The detail-page slugs a listing page links to.

    The markup is unquoted - <a title="Celestial Veil live wallpaper" href=/celestial-veil> -
    so a pattern expecting href="..." finds nothing at all. An earlier version of this
    guessed the slug from the title instead, and every guess 404'd because the title is
    "Celestial Veil live wallpaper" while the page is /celestial-veil. The href is the
    authority; the title is only a label.
    """
    found = set()

    # href may be quoted or bare, and the attribute order varies.
    for href in re.findall(r'href=[\'"]?([^\'" >]+)', html):
        if href.startswith(("http", "#", "javascript", "/static", "/i/", "/media", "/dl")):
            continue
        slug = href.strip("/")
        if slug.startswith(("tag:", "page", "4k", "mobile", "gifs", "search", "submit")):
            continue
        if "/" in slug or len(slug) < 4:
            continue
        if re.match(r"^[a-z0-9][a-z0-9\-_.]+$", slug):
            found.add(slug)

    return found


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    index = get("https://motionbgs.com/sitemap.xml")
    tags = sorted(set(re.findall(r"motionbgs\.com/tag:([a-z0-9\-_]+)/", index, re.I)))
    print("  %d tag pages" % len(tags))
    print()

    all_slugs = set()
    if EXTRA.exists():
        all_slugs = set(json.loads(EXTRA.read_text(encoding="utf-8")).get("slugs", []))
        print("  %d slugs already harvested" % len(all_slugs))

    def fetch(tag):
        try:
            return slugs_on(get("https://motionbgs.com/tag:%s/" % tag))
        except Exception:
            return set()

    done = 0
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        for found in ex.map(fetch, tags):
            all_slugs |= found
            done += 1
            if done % 40 == 0:
                print("    %d/%d tags, %d slugs" % (done, len(tags), len(all_slugs)))

    write_json(EXTRA, {"slugs": sorted(all_slugs)})
    print()
    print("  harvested: %d slugs" % len(all_slugs))
    print("  written  : %s" % EXTRA)

    # How many are new relative to the sitemap?
    sitemap_file = OUT / "sitemap-slugs.txt"
    if sitemap_file.exists():
        known = {s for s in sitemap_file.read_text(encoding="utf-8").split("\n") if s}
        print("  sitemap  : %d slugs" % len(known))
        print("  new      : %d" % len(all_slugs - known))
    return 0


if __name__ == "__main__":
    sys.exit(main())
