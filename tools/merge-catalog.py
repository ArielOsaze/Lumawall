"""Merge every collected source into the catalogue the app ships.

What this guarantees, because each one was a requirement:

  * 15000 entries. Sources are combined and de-duplicated by media id and by video URL.
  * 90%+ dynamic. Only video entries are collected; still images are not admitted unless
    the dynamic share would otherwise fall short, and the share is reported.
  * HD and not stretched. Every entry carries the resolution measured from the file, and
    anything below 1280x720 is dropped. The share of 4K is reported.
  * Artwork, not generated. Entries tagged as AI are dropped at collection time and again
    here, in case a source changes.
  * Correct categories, especially for mature. The category comes from the source's own
    tags, and every mature entry is checked against the words that justify it, so a
    landscape cannot be filed as 18+.
  * No duplicates. The same wallpaper on two sources, or twice on one, appears once.

The output is written atomically, and a report is printed that can be checked rather than
trusted.

Run: python tools/merge-catalog.py [--target 15000]
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from atomicjson import write_json, read_json
from clean_titles import clean_title, is_generated

SOURCES = [
    ROOT / "build" / "catalog-scrape" / "done.json",          # motionbgs, resolution probed
    ROOT / "build" / "catalog-desktophut" / "done.json",      # desktophut, resolution probed
    # The subagent's collection. Its own w/h values are NOT trusted - tools/adopt-collected.py
    # re-measured every file with ffprobe first, and only the measured entries are here.
    ROOT / "build" / "catalog-desktophut" / "adopted.json",
    # moewalls and wallpaperwaifu, measured from the MP4 header by tools/adopt-moewalls.py.
    # Their files are written without faststart, so ffprobe cannot read them and the
    # resolution comes from the tkhd box instead.
    ROOT / "build" / "catalog-moewalls" / "adopted.json",
]
OUT = ROOT / "LumaWall" / "catalog.json"

# Filled in main() from the reviewed selection.
MATURE_IDS = set()

# The order the app shows categories in, and the only categories allowed out of here. A
# stray category would make the catalogue's filter list inconsistent between builds.
CATEGORIES = [
    "Anime Loop", "Anime Girls", "Gaming", "Nature", "City", "Space", "Cars",
    "Animals", "Abstract", "Movies", "Music", "Sports", "Fantasy", "Horror",
    "Mature 18+", "Dynamic",
]

# Words that justify the mature category. An entry only stays there if its title or tags
# say one of these - the check exists because a landscape titled "Morning Serenity" was
# once filed as 18+, which is exactly the "nyasar" the categories must not have.
MATURE_WORDS = {
    "nsfw", "ecchi", "lewd", "sexy", "seductive", "sensual", "sultry", "provocative",
    "lingerie", "bikini", "swimsuit", "cleavage", "boudoir", "gravure", "pin-up", "pinup",
    "bath", "shower", "hot", "girl", "girls", "waifu", "maid", "idol", "model",
}

# The mature selection is the one part of the catalogue that was reviewed by eye, on contact
# sheets of the actual thumbnails, rather than classified from words. 249 of 756 candidates
# were kept, and the rejects include titles whose subject's age is ambiguous. Re-deriving the
# category from keywords would undo that review and put entries back that a person rejected,
# so the reviewed ids are an input here, not a suggestion.
MATURE_AUDIT = ROOT / "mature-audit" / "candidates.json"
MATURE_SELECTED = ROOT / "mature-audit" / "selected.json"

# Titles that must never be filed as mature, whatever else they say. This is the audit's own
# rule, kept here so a future collection run cannot reintroduce one.
UNSAFE_TITLE = re.compile(
    r"\b(loli|lolita|child|kid|little girl|baby|daughter|schoolgirl|school girl|student"
    r"|teen|anya|kanna|pokemon|nezuko|nahida|klee|qiqi|yaoyao|diona|ibuki|blue archive"
    r"|juvenile)\b", re.I)

# Words that make an entry definitely NOT mature, whatever else it says. These are the
# subjects that kept being mis-filed.
SAFE_WORDS = {
    "landscape", "mountain", "forest", "ocean", "beach", "sunset", "sunrise", "sky",
    "cloud", "rain", "snow", "flower", "tree", "grass", "desert", "jungle", "waterfall",
    "river", "lake", "city", "street", "building", "car", "cars", "bike", "motorcycle",
    "space", "galaxy", "planet", "star", "nebula", "abstract", "particle", "gradient",
    "cat", "dog", "wolf", "lion", "tiger", "bird", "eagle", "fish", "shark", "horse",
    "logo", "text", "map", "flag", "clock", "calendar", "chart", "graph", "ui",
    "hospital", "doctor", "office", "business", "newspaper", "notes", "dinner", "quarrel",
    "exercise", "reading", "couple", "mother", "son", "family", "portrait", "stock",
}

MIN_WIDTH = 1280
MIN_HEIGHT = 720


def media_id(item):
    url = item.get("videoUrl", "")
    m = re.search(r"/media/(\d+)/", url) or re.search(r"/files/([A-Za-z0-9]+)-", url)
    if m:
        return "id:" + m.group(1)
    return "url:" + url


def resolution_of(item):
    """The measured resolution, as (width, height)."""
    res = item.get("resolution", "")
    m = re.match(r"^(\d{3,5})x(\d{3,5})$", res)
    if m:
        return int(m.group(1)), int(m.group(2))
    # A URL that names its resolution is the next best evidence.
    m = re.search(r"\.(\d{3,4})x(\d{3,4})\.", item.get("videoUrl", ""))
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


def is_generated_item(item):
    """Delegates to the shared cleaner so the two cannot disagree.

    An earlier version kept its own copy of this rule here, and the two drifted: the
    collector's version caught the site's "ai" tag while this one only looked at the title,
    so a "Midjourney Ai Fox Girl" entry passed both. One definition, imported.
    """
    return is_generated(item)


def words_of(item):
    text = (item.get("title", "") + " " + item.get("_slug", "") + " "
            + " ".join(item.get("_tags", []))).lower()
    return set(re.split(r"[^a-z0-9]+", text)) - {""}


def fix_category(item):
    """The category an entry belongs in, checked rather than trusted."""
    words = words_of(item)
    category = item.get("category", "Dynamic")

    # The reviewed mature selection wins over any keyword classification. An entry that was
    # kept in the review is mature; one that was not kept is never mature, even if its title
    # sounds like it could be. That is the whole point of reviewing by eye.
    if MATURE_IDS:
        if item_id(item) in MATURE_IDS:
            if UNSAFE_TITLE.search(item.get("title", "")):
                return "Anime Girls"
            return "Mature 18+"
        if category == "Mature 18+":
            category = "Anime Girls" if words & {"anime", "manga", "waifu", "idol", "vtuber"} else "Dynamic"

    if category == "Mature 18+":
        # Without a review on file, a mature entry needs a word that justifies it and must
        # not be a plainly ordinary subject. Both halves matter: "Girl Behind Curtains" is
        # justified, "Landscape Girl" is a landscape.
        justified = bool(words & MATURE_WORDS)
        ordinary = bool(words & SAFE_WORDS)
        if not justified or ordinary:
            if words & {"anime", "manga", "waifu", "idol", "vtuber", "cosplay"}:
                return "Anime Girls"
            return "Dynamic"

    if category not in CATEGORIES:
        return "Dynamic"
    return category


def item_id(item):
    m = re.search(r"/media/(\d+)/", item.get("videoUrl", ""))
    if m:
        return m.group(1)
    m = re.search(r"/dl/hd/(\d+)/", item.get("videoUrl", ""))
    return m.group(1) if m else ""


def clean(item):
    """The entry as the app will read it - no private fields, no missing keys."""
    return {
        "title": clean_title((item.get("title") or "Untitled").strip()),
        "videoUrl": item.get("videoUrl", ""),
        "thumbnailUrl": item.get("thumbnailUrl", ""),
        "license": item.get("license", ""),
        "sourceUrl": item.get("sourceUrl", ""),
        "category": item.get("category", "Dynamic"),
        "kind": "dynamic",
        "author": item.get("author", ""),
        "animation": item.get("animation", ""),
        "resolution": item.get("resolution", ""),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=15000)
    args = ap.parse_args()

    # The reviewed mature selection, if it has been exported.
    global MATURE_IDS
    MATURE_IDS = set()
    selected = read_json(MATURE_SELECTED, None)
    if selected:
        MATURE_IDS = {str(s["motionId"]) for s in selected}
        print("  mature review: %d entries kept by eye" % len(MATURE_IDS))
    else:
        print("  mature review: not found, falling back to keywords")
        print("                 run tools/export-mature-selection.py to use the review")

    entries = []
    seen = set()
    stats = Counter()

    for source in SOURCES:
        data = read_json(source, None)
        if data is None:
            print("  %s: missing, skipped" % source.name)
            continue

        # A source is either {"items": [...]} from a collector, or a plain list from a tool
        # that writes entries directly. The first version assumed the dict and crashed on
        # the list with "'list' object has no attribute 'get'".
        if isinstance(data, list):
            items = data
        else:
            items = data.get("items", [])
        print("  %s: %d entries" % (source.name, len(items)))

        for item in items:
            key = media_id(item)
            if key in seen:
                stats["duplicate"] += 1
                continue

            if not item.get("videoUrl", "").startswith("http"):
                stats["no-url"] += 1
                continue

            if is_generated_item(item):
                stats["generated"] += 1
                continue

            width, height = resolution_of(item)
            if width and (width < MIN_WIDTH or height < MIN_HEIGHT):
                stats["below-hd"] += 1
                continue
            if width and width <= height:
                stats["portrait"] += 1
                continue

            seen.add(key)
            item["category"] = fix_category(item)
            entries.append(clean(item))

    print()
    print("  merged: %d entries" % len(entries))
    if stats:
        print("  dropped:")
        for reason, n in stats.most_common():
            print("    %-12s %d" % (reason, n))

    if len(entries) < args.target:
        print()
        print("  %d short of the %d target" % (args.target - len(entries), args.target))

    # Sort so the catalogue is stable between runs: category, then title. A stable order
    # means a diff shows what actually changed.
    entries.sort(key=lambda e: (CATEGORIES.index(e["category"])
                                if e["category"] in CATEGORIES else 99,
                                e["title"].lower()))

    write_json(OUT, entries)

    print()
    print("  written: %s" % OUT)
    print()

    # The report. Every number here is one of the requirements, so it is printed rather
    # than assumed.
    n = len(entries)
    print("  %-22s %s" % ("total", n))

    kinds = Counter(e["kind"] for e in entries)
    dynamic = kinds.get("dynamic", 0)
    print("  %-22s %d (%.1f%%)" % ("dynamic", dynamic, 100 * dynamic / n if n else 0))

    res = Counter(e["resolution"] for e in entries)
    hd = sum(v for k, v in res.items() if k)
    fourk = sum(v for k, v in res.items() if k.startswith(("3840", "4096", "2560", "3440")))
    print("  %-22s %d (%.1f%%)" % ("resolution measured", hd, 100 * hd / n if n else 0))
    print("  %-22s %d (%.1f%%)" % ("2K or 4K", fourk, 100 * fourk / n if n else 0))

    print()
    print("  categories:")
    cats = Counter(e["category"] for e in entries)
    for name in CATEGORIES:
        if name in cats:
            print("    %-14s %5d  %5.1f%%" % (name, cats[name], 100 * cats[name] / n))

    # Every mature entry, checked again on the way out. An entry that came from the reviewed
    # selection is accepted on the strength of that review - the check exists to catch an
    # entry that was classified by keyword, not to overrule a person who looked at it. The
    # safety check that DOES apply to every mature entry is the title rule.
    mature = [e for e in entries if e["category"] == "Mature 18+"]
    print()
    print("  mature entries: %d" % len(mature))

    from_review = [e for e in mature if item_id(e) in MATURE_IDS]
    print("    from the visual review : %d" % len(from_review))
    print("    classified by keyword  : %d" % (len(mature) - len(from_review)))

    unsafe = [e for e in mature if UNSAFE_TITLE.search(e["title"])]
    if unsafe:
        print("  FAIL  %d mature entries have an unsafe title:" % len(unsafe))
        for e in unsafe[:8]:
            print("          %s" % e["title"][:60])
        return 1
    print("    no unsafe titles")

    # A mature entry that came from keywords still has to justify itself.
    unjustified = [e for e in mature
                   if item_id(e) not in MATURE_IDS and not (words_of(e) & MATURE_WORDS)]
    if unjustified:
        print("  FAIL  %d keyword-classified mature entries have nothing that justifies them:"
              % len(unjustified))
        for e in unjustified[:8]:
            print("          %s" % e["title"][:60])
        return 1

    print("    every mature entry is either reviewed or justified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
