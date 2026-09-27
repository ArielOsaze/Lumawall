"""Clean the catalogue's titles and drop anything that is generated art.

Two faults, both visible to a user:

  1. Some titles carry the source site's own suffix - "... Live Wallpaper - Free Animated
     Desktop Background | 67,000+ Free Live & Animated Wallpapers for PC". That is the page
     title, not the wallpaper's name, and it made one entry's title 118 characters long.

  2. Generated art slipped in. The motionbgs collector filters on the site's "ai" tag, but
     desktophut has no such tag - it only says so in the title, and two entries say it
     plainly: "Midjourney Ai Fox Girl" and "Ai Generated Girl". The requirement is artwork,
     not generated images, so these are removed.

The check is deliberately broad: it looks for the words in the title, the url and the
description, because a generated image is not always labelled the same way.

Run: python tools/clean_titles.py [--dry-run]
"""

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from atomicjson import write_json, read_json

CATALOG = ROOT / "LumaWall" / "catalog.json"

# The site's own page-title suffix, and the other boilerplate that follows a wallpaper's
# real name. Each pattern is anchored so it cannot eat a genuine part of a title.
SUFFIXES = [
    r"\s*[–—-]\s*Free Animated Desktop Background.*$",
    r"\s*\|\s*\d[\d,]*\+?\s*Free Live.*$",
    r"\s*[–—-]\s*Free Live Wallpaper.*$",
    r"\s*[–—-]\s*Free Download.*$",
    r"\s*\|\s*DesktopHut.*$",
    r"\s*\|\s*MotionBGs.*$",
    # A title that begins with the uploader's file id, e.g. "GD035WAnQoVn603_Ai Generated Girl".
    # The id is not part of the name and the underscore is what made the AI check miss it.
    r"^[A-Za-z0-9]{8,}[_-]\s*",
    # A title that begins with the resolution as a word: "2K Ganyu Genshin Impact",
    # "4K Luffy Sun God Nika". 118 entries carried this, and the resolution is already in
    # the entry's own resolution field - repeating it in the name is noise.
    r"^(?:8K|4K|2K|UHD|HD|FHD|QHD)\s+(?:\d+\s+)?",
    # The same thing written as dimensions, sometimes with a version word: "1920x1080 ver
    # Shinobi Live Anime", "3150x2160 batch".
    r"^\d{3,4}\s*x\s*\d{3,4}\s*(?:ver\b|version\b|batch\b)?\s*",
    r"\s+(?:4k|uhd|hd|2k)\s+live\s+wallpaper\b.*$",
    r"\s+live\s+wallpaper\s+(?:for|on)\s+(?:pc|windows|mac|desktop)\b.*$",
    r"\s+for\s+pc\b.*$",
    r"\s*[-–—]\s*Live Wallpaper\s*$",          # only when it trails the whole title
]

# Generated art. A wallpaper that says any of this is not a drawing, a render or a painting.
#
# The leading boundary is a lookbehind for "not a letter or digit" rather than \b, because
# the word often follows an underscore: the entry "GD035WAnQoVn603_Ai Generated Girl" slipped
# through a \b pattern, since "_" is a word character and the boundary never matched.
GENERATED = re.compile(
    r"(?<![a-z0-9])(?:ai\s+generated|ai-generated|generated\s+by\s+ai|midjourney"
    r"|stable\s+diffusion|sdxl|dall-?e\s*\d?|novelai|ai\s+art|made\s+with\s+ai)",
    re.I)

# A title that is just the word AI in brackets, e.g. "Gamer Girl (AI)".
GENERATED_BRACKET = re.compile(r"\((?:ai|a\.i\.)\)", re.I)

# A title that says "AI" as the subject of a person: "AI Girl", "AI Waifu", "AI Model".
# These are generated images that name themselves, and they are distinct from "Ai Hoshino",
# which is a character's name - so the pattern requires the AI to modify a person rather
# than to be a standalone word.
GENERATED_PERSON = re.compile(
    r"^\s*ai\s+(?:girl|girls|woman|women|waifu|model|art|portrait|anime|character)s?\b"
    r"|\bai\s+(?:girl|waifu|model|portrait)s?\b",
    re.I)


def clean_title(title):
    """The wallpaper's own name, without the source site's boilerplate."""
    out = title.strip()

    # HTML entities are not decoded by the collectors, so titles arrive as
    # "Howl&#8217;s Moving Castle" and "King Kai&#8217;s Planet". 142 entries carried one.
    # unescape handles named and numeric forms, and is applied twice because a double
    # escape - &amp;#8217; - is common in page titles.
    out = html.unescape(html.unescape(out))

    # The page title often ends with the site's name repeated; cut at the first separator
    # that introduces it.
    for pattern in SUFFIXES:
        out = re.sub(pattern, "", out, flags=re.I)

    # Collapse the whitespace the removals leave behind.
    out = re.sub(r"\s{2,}", " ", out).strip(" -–—|·")

    # A trailing "Live Wallpaper" is boilerplate when something else remains.
    stripped = re.sub(r"\s*[-–—]?\s*Live Wallpaper\s*$", "", out, flags=re.I).strip()
    if len(stripped) >= 4:
        out = stripped

    # A trailing "Live Anime" is the same boilerplate with a different word. 42 entries
    # carried it, and the site writes it as a suffix rather than a prefix.
    stripped = re.sub(r"\s*[-–—]?\s*Live Anime\s*$", "", out, flags=re.I).strip()
    if len(stripped) >= 4:
        out = stripped

    # A bare uploader id with no name after it, e.g. "1667938588-cassie-quinn-live". The
    # digits and the trailing "live" are both noise; what remains is the name.
    m = re.match(r"^\d{8,}[-_]\s*(.+?)[-_]?live\s*$", out, re.I)
    if m:
        out = m.group(1)

    return out.strip(" -–—|·_")


def is_generated(entry):
    text = " ".join([entry.get("title", ""), entry.get("videoUrl", ""),
                     entry.get("sourceUrl", "")])
    title = entry.get("title", "")
    return bool(GENERATED.search(text)
                or GENERATED_BRACKET.search(title)
                or GENERATED_PERSON.search(title))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    entries = read_json(CATALOG, [])
    print("  entries: %d" % len(entries))
    print()

    # 1. Remove generated art.
    kept = []
    removed = []
    for entry in entries:
        if is_generated(entry):
            removed.append(entry)
        else:
            kept.append(entry)

    print("  generated art removed: %d" % len(removed))
    for entry in removed[:10]:
        print("    %s" % entry.get("title", "")[:78])
    print()

    # 2. Clean the titles.
    changed = 0
    shortened = 0
    for entry in kept:
        before = entry.get("title", "")
        after = clean_title(before)
        if after != before:
            changed += 1
            shortened += max(0, len(before) - len(after))
            entry["title"] = after

    print("  titles cleaned: %d" % changed)
    print("  characters removed: %d" % shortened)
    print()

    if changed:
        print("  examples:")
        shown = 0
        for entry in kept:
            title = entry.get("title", "")
            if len(title) > 80:
                continue
        # Show a few of the longest remaining titles, which is where the boilerplate was.
        for entry in sorted(kept, key=lambda e: -len(e.get("title", "")))[:8]:
            print("    (%3d) %s" % (len(entry["title"]), entry["title"][:84]))
        print()

    lengths = [len(e.get("title", "")) for e in kept]
    if lengths:
        print("  title length: shortest %d, longest %d, average %.0f"
              % (min(lengths), max(lengths), sum(lengths) / len(lengths)))
        over = [e for e in kept if len(e.get("title", "")) > 90]
        if over:
            print("  still over 90 characters: %d" % len(over))
            for e in over[:5]:
                print("    %s" % e["title"][:96])
        print()

    if args.dry_run:
        print("  dry run, nothing written")
        return 0

    write_json(CATALOG, kept)
    print("  written: %s" % CATALOG)
    print("  entries: %d" % len(kept))
    return 0


if __name__ == "__main__":
    sys.exit(main())
