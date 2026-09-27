"""Audit the catalogue's categories against the evidence in each entry.

Why: the requirement is "kategorinya sesuai jangan nyasar" - a category that does not match
its contents is the failure being described. A count of categories says nothing about that:
1000 entries filed under Nature could all be anime girls. This reads each entry's title, url
and tags and reports the ones whose category is not supported by any of the words that
category means.

It is deliberately conservative: it reports a mismatch only when the entry contains words
that belong to a DIFFERENT category and none that belong to its own. That is the "nyasar"
case. An entry whose title says nothing either way is left alone rather than guessed at.

Run: python tools/audit-categories.py [--show 40] [--fix]
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from atomicjson import write_json, read_json

CATALOG = ROOT / "LumaWall" / "catalog.json"

# The words that belong to each category. These are the same lists the collectors classify
# with, kept here so the audit is independent of them - a check that shares the classifier's
# own table can only confirm the classifier, not test it.
CATEGORY_WORDS = {
    "Anime Loop": {
        "anime", "manga", "shonen", "seinen", "isekai", "mecha", "gundam", "naruto",
        "one-piece", "jujutsu", "demon-slayer", "attack-on-titan", "genshin", "honkai",
        "arknights", "azur-lane", "blue-archive", "fate", "evangelion", "chainsaw-man",
        "bleach", "naruto-art", "dragon-ball", "solo-leveling", "tokyo-ghoul", "aot",
    },
    "Anime Girls": {
        "anime-girl", "anime-girls", "waifu", "idol", "schoolgirl", "kimono", "maid",
        "neko", "catgirl", "vtuber", "cosplay", "gravure-idol",
    },
    "Gaming": {
        "game", "games", "gaming", "valorant", "league-of-legends", "dota", "counter-strike",
        "csgo", "cs2", "fortnite", "apex", "overwatch", "minecraft", "cyberpunk-2077",
        "elden-ring", "witcher", "gta", "call-of-duty", "battlefield", "pubg", "roblox",
        "zelda", "mario", "pokemon", "sonic", "genshin-impact", "honkai-star-rail",
        "zenless-zone-zero", "wuthering-waves", "goddess-of-victory-nikke", "warcraft",
    },
    "Nature": {
        "nature", "landscape", "forest", "mountain", "ocean", "sea", "beach", "waterfall",
        "river", "lake", "sunset", "sunrise", "sky", "cloud", "rain", "snow", "flower",
        "tree", "grass", "desert", "jungle", "underwater", "aurora", "storm", "lightning",
        "autumn-leaves", "leaf", "garden", "anime-nature",
    },
    "City": {
        "city", "urban", "street", "neon", "tokyo", "skyline", "building", "architecture",
        "bridge", "traffic", "subway", "downtown", "vaporwave", "synthwave", "retrowave",
    },
    "Space": {
        "space", "galaxy", "nebula", "planet", "star", "cosmos", "astronaut", "universe",
        "moon", "mars", "saturn", "earth", "black-hole", "sci-fi", "scifi", "spaceship",
    },
    "Cars": {
        "car", "cars", "supercar", "jdm", "drift", "racing", "motorcycle", "bike",
        "ferrari", "lamborghini", "porsche", "bmw", "nissan", "toyota", "honda", "audi",
        "sports-cars", "pagani", "bugatti", "mclaren",
    },
    "Animals": {
        "animal", "animals", "cat", "cats", "dog", "dogs", "wolf", "lion", "tiger",
        "bird", "eagle", "owl", "fish", "shark", "whale", "dolphin", "horse", "fox",
        "bear", "dragon", "snake", "corgi",
    },
    "Abstract": {
        "abstract", "particle", "geometric", "pattern", "fluid", "gradient", "smoke",
        "ink", "light", "glow", "loop", "minimal", "3d", "render", "waveform", "audio",
    },
    "Movies": {
        "movie", "film", "cinema", "marvel", "dc", "star-wars", "harry-potter", "matrix",
        "avengers", "spiderman", "batman", "joker", "stranger-things", "superhero",
    },
    "Music": {
        "music", "concert", "band", "guitar", "piano", "dj", "singer", "kpop", "bts",
    },
    "Sports": {
        "sport", "football", "soccer", "basketball", "nba", "nfl", "baseball", "boxing",
        "ufc", "mma", "f1", "formula-1", "skate", "surf", "ski", "snowboard",
    },
    "Fantasy": {
        "fantasy", "magic", "wizard", "knight", "castle", "elf", "dwarf", "myth",
        "mythology", "demon", "angel", "fairy", "vampire", "samurai", "ninja",
    },
    "Horror": {
        "horror", "scary", "creepy", "ghost", "zombie", "halloween", "skull",
        "skeleton", "undead", "death", "dark",
    },
    "Mature 18+": {
        "nsfw", "ecchi", "lewd", "sexy", "seductive", "sensual", "sultry", "provocative",
        "lingerie", "bikini", "swimsuit", "cleavage", "boudoir", "gravure", "pin-up",
        "pinup", "bath", "shower", "hot", "girl", "girls", "waifu", "maid", "idol", "model",
    },
}

# Dynamic is the fallback, so it is never a mismatch on its own - but an entry that plainly
# belongs somewhere else should not be sitting there either.
FALLBACK = "Dynamic"


def words_of(entry):
    text = " ".join([
        entry.get("title", ""),
        entry.get("videoUrl", ""),
        entry.get("sourceUrl", ""),
    ]).lower()
    return set(re.split(r"[^a-z0-9]+", text)) - {""}


def categories_for(words):
    """Every category the entry's own words support."""
    hits = set()
    for name, keys in CATEGORY_WORDS.items():
        if words & keys:
            hits.add(name)
        else:
            # A joined form, for tags written without separators.
            joined = "-".join(sorted(words))
            for key in keys:
                if len(key) >= 6 and key.replace("-", "") in joined.replace("-", ""):
                    hits.add(name)
                    break
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=int, default=30)
    ap.add_argument("--fix", action="store_true",
                    help="rewrite entries whose category no word supports")
    args = ap.parse_args()

    entries = read_json(CATALOG, [])
    print("  entries: %d" % len(entries))
    print()

    mismatch = []
    for entry in entries:
        words = words_of(entry)
        supported = categories_for(words)
        current = entry.get("category", FALLBACK)

        # The entry's category is wrong when its own words point elsewhere and not here.
        if supported and current not in supported:
            # Anime Loop and Anime Girls overlap heavily; a swap between them is not the
            # "nyasar" that matters.
            if {current, supported and next(iter(supported))} <= {"Anime Loop", "Anime Girls"}:
                continue
            mismatch.append((entry, current, sorted(supported)))

    print("  entries whose words point to a different category: %d (%.1f%%)"
          % (len(mismatch), 100 * len(mismatch) / len(entries)))
    print()

    if mismatch:
        by_move = Counter((cur, sup[0]) for _, cur, sup in mismatch)
        print("  the moves, most common first:")
        for (cur, sup), count in by_move.most_common(15):
            print("    %-14s -> %-14s %d" % (cur, sup, count))
        print()

        print("  examples:")
        for entry, cur, sup in mismatch[:args.show]:
            print("    [%s -> %s]" % (cur, sup[0]))
            print("      %s" % entry.get("title", "")[:78])
        print()

    # A category that is empty, or nearly so, is a sign its rule never fires.
    counts = Counter(e.get("category") for e in entries)
    print("  entries per category:")
    for name, count in counts.most_common():
        print("    %-14s %5d  %5.1f%%" % (name, count, 100 * count / len(entries)))

    if args.fix and mismatch:
        print()
        for entry, cur, sup in mismatch:
            entry["category"] = sup[0]
        write_json(CATALOG, entries)
        print("  rewrote %d entries" % len(mismatch))
    elif mismatch:
        print()
        print("  run with --fix to rewrite them")

    return 0


if __name__ == "__main__":
    sys.exit(main())
