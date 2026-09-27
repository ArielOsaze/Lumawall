"""Add desktophut tag pages as a source, including the adult tags.

Why: the app-sitemap yields about 15% usable entries and the catalogue is short of its
target, while the site's tag pages reach items the sitemap orders differently. The adult tags
in particular are the only route found so far to genuinely mature wallpapers - /tag/adult and
/tag/bikini carry real swimwear and lingerie content, which the general listing buries among
stock footage.

Each tag page lists its items with pagination, so the tag pages are walked page by page and
the item URLs are appended to the collector's own url list.

Run: python tools/add-tag-pages.py [--tags adult bikini ...]
"""

import argparse
import concurrent.futures as cf
import re
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from atomicjson import write_json, read_json

OUT = ROOT / "build" / "catalog-desktophut"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# The tags worth walking. The adult ones come first because they are the reason this exists.
DEFAULT_TAGS = [
    # adult-adjacent - the mature category's only real source on this site
    "adult", "adults", "bikini", "lingerie", "swimsuit", "sexy", "hot", "seductive",
    "sensual", "pinup", "gravure", "boudoir", "nude", "lingerie-model", "beach-bikini",
    # the subjects that carry most of the catalogue
    "anime-girl", "anime-girls", "waifu", "cosplay", "idol", "maid", "kimono", "cat-girl",
    "anime", "manga", "games", "gaming", "nature", "landscape", "city", "neon",
    "space", "galaxy", "car", "supercar", "animal", "cat", "dog", "wolf", "dragon",
    "abstract", "particle", "cyberpunk", "synthwave", "vaporwave", "retro",
    "movie", "superhero", "marvel", "dc", "fantasy", "horror", "music", "sports",
]


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def items_on(html):
    """The wallpaper URLs a tag page links to."""
    found = set()
    for href in re.findall(r'href="(/[A-Za-z0-9][A-Za-z0-9\-_.%]+)"', html):
        # An item page ends in -live-wallpaper, sometimes with a short id suffix.
        if "-live-wallpaper" in href.lower() or "-wallpaper" in href.lower():
            found.add("https://www.desktophut.com" + href)
    return found


def walk_tag(tag, max_pages=40):
    """Every item the tag lists, following its pagination."""
    urls = set()
    for page in range(1, max_pages + 1):
        url = "https://www.desktophut.com/tag/%s" % tag
        if page > 1:
            url += "?page=%d" % page
        try:
            html = get(url)
        except Exception:
            break

        found = items_on(html)
        before = len(urls)
        urls |= found

        # A page that adds nothing new, or has no next-page link, is the last one.
        if len(urls) == before and page > 1:
            break
        if '?page=%d' % (page + 1) not in html and 'page=%d' % (page + 1) not in html:
            break

    return tag, urls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", nargs="*", default=None)
    args = ap.parse_args()

    tags = args.tags or DEFAULT_TAGS
    print("  %d tags to walk" % len(tags))
    print()

    all_urls = {}
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for tag, urls in ex.map(walk_tag, tags):
            all_urls[tag] = urls
            print("    %-18s %4d items" % (tag, len(urls)))

    combined = set()
    for urls in all_urls.values():
        combined |= urls

    # Append to the collector's url list, so the collector picks them up on its next run.
    list_file = OUT / "slugs.txt"
    existing = set()
    if list_file.exists():
        existing = {u for u in list_file.read_text(encoding="utf-8").split("\n") if u}

    merged = sorted(existing | combined)
    list_file.write_text("\n".join(merged), encoding="utf-8")

    print()
    print("  urls from tags : %d" % len(combined))
    print("  already listed : %d" % len(existing))
    print("  new            : %d" % len(combined - existing))
    print("  total list     : %d" % len(merged))
    print("  written        : %s" % list_file)

    # Record which urls came from adult tags, so the collector can file them as mature
    # without guessing from the slug.
    adult_tags = [t for t in tags if t in {
        "adult", "adults", "bikini", "lingerie", "swimsuit", "sexy", "hot", "seductive",
        "sensual", "pinup", "gravure", "boudoir", "nude", "lingerie-model", "beach-bikini",
    }]
    adult_urls = sorted(set().union(*[all_urls[t] for t in adult_tags if t in all_urls])
                        if adult_tags else set())
    write_json(OUT / "adult-urls.json", {"urls": adult_urls})
    print("  adult urls     : %d (recorded)" % len(adult_urls))
    return 0


if __name__ == "__main__":
    sys.exit(main())
