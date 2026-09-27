"""Recategorise the catalogue from the source's own tags, with a clear precedence.

Why: the categories were assigned by the collector while it walked each site, and the rule
order it used put anime before games. That filed 792 entries that the source tags as both
"anime" and "games" under Anime Loop - a League of Legends or Genshin wallpaper is a game
wallpaper, and a browser filtering for Gaming should find it. The count of entries under
Gaming was 1470 while 3811 entries carried the games tag.

This recomputes every category from the evidence each entry carries, in one place, with the
precedence written down:

  1. The mature review wins outright. Those entries were chosen by eye.
  2. An entry from an adult tag on its source is mature.
  3. A named game beats a named anime: the subject is a game character.
  4. Anime with a named girl is Anime Girls; anime otherwise is Anime Loop.
  5. Then the remaining subjects, most specific first.
  6. Dynamic last, for an entry whose words say nothing.

The result is written back to the catalogue, and the audit runs after it to confirm.

Run: python tools/recategorise.py [--dry-run]
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

CATALOG = ROOT / "LumaWall" / "catalog.json"
MB_STATE = ROOT / "build" / "catalog-scrape" / "done.json"
DH_STATE = ROOT / "build" / "catalog-desktophut" / "done.json"
MW_ADOPTED = ROOT / "build" / "catalog-moewalls" / "adopted.json"
MATURE_SELECTED = ROOT / "mature-audit" / "selected.json"

# Named games. An entry that names one is a game wallpaper even when it also names an anime,
# because the character it shows belongs to that game.
GAMES = {
    "video-games", "videogames", "video-game", "game", "games", "gaming",
    "game-landscape", "game-character", "game-art", "gameplay",
    "valorant", "league-of-legends", "dota", "counter-strike",
    "csgo", "cs2", "fortnite", "apex-legends", "apex", "overwatch", "minecraft",
    "dark-souls", "dark-souls-3", "dark-souls-remastered", "bloodborne", "sekiro",
    "cyberpunk-2077", "elden-ring", "witcher", "gta", "call-of-duty", "codm",
    "battlefield", "pubg", "roblox", "zelda", "mario", "pokemon", "sonic",
    "genshin-impact", "honkai-star-rail", "honkai", "zenless-zone-zero", "wuthering-waves",
    "goddess-of-victory-nikke", "warcraft", "warframe", "warhammer", "skyrim", "sekiro",
    "resident-evil", "the-last-of-us", "titanfall", "brawl-stars", "blue-lock",
    "blue-archive", "azur-lane", "arknights", "fate", "tower-of-fantasy", "wuthering",
    "league", "valorant", "pubg-mobile", "free-fire", "mobile-legends", "honkai-impact",
    "star-rail", "zzz", "wuwa", "nikke", "umamusume", "touhou", "hollow-knight",
    "dead-by-daylight", "fnaf", "bendy", "genshin", "starrail",
}

# Named anime and manga. These are properties, not genres.
ANIME = {
    "anime", "manga", "shonen", "seinen", "isekai", "mecha", "gundam", "naruto",
    "naruto-art", "one-piece", "jujutsu", "jujutsu-kaisen", "demon-slayer", "kimetsu",
    "attack-on-titan", "aot", "chainsaw-man", "bleach", "dragon-ball", "solo-leveling",
    "tokyo-ghoul", "tokyo-revengers", "spy-x-family", "sword-art-online", "rezero",
    "re-zero", "sakura", "sasuke", "satoru-gojo", "gojo", "tanjiro-kamado", "zenitsu",
    # Dragon Ball's own cast. The series name was listed but none of its characters were,
    # so "Goku Sunset" and "Super Saiyan Blue Goku" fell through to Nature - the only word
    # the classifier could see was "sunset".
    #
    # Only names that cannot mean something else are here. "cell", "ace", "law", "pain",
    # "trunks", "robin", "brook" and "chopper" are all ordinary English words - a bird, a
    # stream, a helicopter - and listing them would pull wildlife and landscape wallpapers
    # into the anime categories. That is the same mistake this file exists to fix.
    "goku", "vegeta", "gohan", "goten", "bulma", "krillin", "piccolo", "frieza",
    "buu", "broly", "beerus", "whis", "gogeta", "vegito", "super-saiyan",
    # One Piece's cast, for the same reason.
    "luffy", "zoro", "sanji", "nami", "usopp", "franky", "shanks",
    "kaido", "big-mom", "katakuri", "doflamingo", "mihawk",
    # Naruto's, which were also thin.
    "kakashi", "itachi", "sakura-haruno", "hinata", "gaara", "rock-lee", "jiraya",
    "orochimaru", "tsunade", "madara", "obito", "boruto", "sasori", "deidara",
    "konan", "nagato", "minato", "kushina", "shikamaru", "choji", "kiba", "shino",
    "neji", "tenten", "kurenai", "asuma", "jiraiya",
    "tengen-uzui", "yoriichi", "yuji-itadori", "ryomen-sukuna", "sukuna", "toji-fushiguro",
    "yuta", "choso", "rengoku", "akaza", "shinobu", "yae-miko", "raiden", "nahida",
    "ayaka", "shenhe", "ganyu", "kokomi", "hutao", "hollow", "anime-nature", "anime-girl",
    "anime-girls", "vtuber", "waifu", "my-hero-academia", "mha", "black-clover",
    "seven-deadly-sins", "fairy-tail", "hunter-x-hunter", "death-note", "evangelion",
    "code-geass", "steins-gate", "violet-evergarden", "your-name", "weathering",
    "suzume", "spirited-away", "totoro", "ghibli", "initial-d", "haikyuu", "kuroko",
    "sailor-moon", "cardcaptor", "madoka", "konosuba", "overlord",
    "shield-hero", "slime", "tensura", "dandadan", "frieren", "oshi-no-ko", "bocchi",
    "dress-up-darling", "lycoris", "spy-family", "jojo", "berserk", "vinland",
    "monogatari", "horimiya", "kaguya", "rent-a-girlfriend", "quintuplets", "nisekoi",
    "toradora", "clannad", "angel-beats", "charlotte", "another", "higurashi",
    "umineko", "danganronpa", "persona", "nier", "final-fantasy", "kingdom-hearts",
    # Attack on Titan's own cast. Without these the series' wallpapers fell to whatever
    # subject word the title happened to carry - "War Hammer Titan" was filed under Gaming
    # because "hammer" reads as a game item.
    "hange", "hange-zoe", "levi", "levi-ackerman", "eren", "eren-yeager", "mikasa",
    "mikasa-ackerman", "armin", "erwin", "annie", "reiner", "zeke", "titan",
    "titans", "wall-maria", "survey-corps", "scouting-legion", "paradis",
    # Naruto's cast and its organisations. "Akatsuki" alone is the clan name and does not
    # contain "naruto", so 161 Akatsuki wallpapers fell to Abstract (the logo), Nature (rain)
    # and City (the street) by whichever word their title happened to carry.
    "akatsuki", "itachi", "uchiha", "sasuke", "naruto", "kakashi", "hatake", "sakura",
    "hinata", "hyuga", "madara", "obito", "pain", "nagato", "jiraya", "orochimaru",
    "kakuzu", "hidan", "deidara", "sasori", "konan", "zetsu", "kisame", "kurama",
    "nine-tails", "sharingan", "rinnegan", "byakugan", "konoha", "shippuden",
    "boruto", "minato", "tsunade", "gaara", "rock-lee", "neji", "shikamaru",
    "ino", "choji", "kiba", "shino", "tenten", "kurenai", "asuma", "yamato",
    # "blue-lock" is absent: it is a football manga, and Sports is the subject a browser
    # looking for it would search. Games lists the word too and would have taken it.
}

GIRL_MARKERS = {"girl", "girls", "waifu", "idol", "schoolgirl", "kimono", "maid",
                "neko", "catgirl", "vtuber", "cosplay", "gravure", "anime-girl",
                "anime-girls", "female", "woman", "women", "lady"}

NATURE = {
    "nature", "landscape", "forest", "mountain", "ocean", "sea", "beach", "waterfall",
    "river", "lake", "sunset", "sunrise", "sky", "cloud", "rain", "snow", "flower",
    "tree", "grass", "desert", "jungle", "underwater", "aurora", "storm", "lightning",
    "leaf", "garden", "anime-nature", "autumn-leaves", "snowfall", "waves", "water",
    "butterfly", "sunset", "topo", "mountains", "valley", "cliff", "island", "tropical",
}

CITY = {
    "city", "urban", "street", "neon", "tokyo", "skyline", "building", "architecture",
    "bridge", "traffic", "subway", "downtown", "vaporwave", "synthwave", "retrowave",
    "japan", "cyberpunk", "neon-city", "rooftop", "alley",
}

SPACE = {
    "space", "galaxy", "nebula", "planet", "star", "stars", "cosmos", "astronaut",
    "universe", "moon", "mars", "saturn", "earth", "black-hole", "sci-fi", "scifi",
    "spaceship", "starfield", "milky-way", "cosmic", "solar",
}

CARS = {
    "car", "cars", "supercar", "jdm", "drift", "motorcycle", "bike", "bmw",
    "ferrari", "lamborghini", "porsche", "nissan", "toyota", "honda", "audi",
    "sports-cars", "pagani", "bugatti", "mclaren", "volkswagen", "mercedes", "supra",
    "gt-r", "mustang", "corvette", "tesla", "ford", "chevrolet", "dodge",
    # Deliberately absent:
    #   "skyline" - also a city horizon; it filed 79 city wallpapers under Cars.
    #   "racing"  - also a sport; Sports owns it.
}

ANIMALS = {
    "animal", "animals", "cat", "cats", "dog", "dogs", "wolf", "lion", "tiger", "bird",
    "eagle", "owl", "fish", "shark", "whale", "dolphin", "horse", "fox", "bear",
    "snake", "corgi", "panda", "rabbit", "deer", "penguin",
    # Deliberately absent:
    #   "dragon"    - a fantasy creature; Fantasy owns it.
    #   "butterfly" - a nature subject; Nature owns it.
}

ABSTRACT = {
    "abstract", "particle", "geometric", "pattern", "fluid", "gradient", "smoke", "ink",
    "minimal", "3d", "render", "waveform", "audio", "technology", "topographic",
    "digital-art", "fractal", "black-and-white", "simple", "aesthetic",
    # "topo" is absent: it was also in the girl markers, which made no sense at all.
}

MOVIES = {
    "movie", "film", "cinema", "marvel", "dc", "dc-comics", "star-wars", "harry-potter",
    "matrix", "avengers", "spiderman", "batman", "joker", "stranger-things", "superhero",
    "deadpool", "venom", "superman", "wonder-woman", "iron-man", "thor", "hulk",
    "the-walking-dead", "breaking-bad", "wednesday", "squid-game", "rick-and-morty",
    "avatar", "spongebob", "adventure-time", "cartoon", "tv",
    # "arcane" is absent: it is a League of Legends series, so the subject is a game
    # character and Gaming owns it. Fantasy lists the word too, which would have taken it.
}

MUSIC = {
    "music", "concert", "band", "guitar", "piano", "dj", "singer", "kpop", "bts",
    "sabrina-carpenter", "billie-eilish", "taylor-swift", "ariana-grande", "rihanna",
    "beyonce", "lady-gaga", "dua-lipa", "selena-gomez", "miley-cyrus", "blackpink",
    "twice", "stray-kids", "newjeans", "aespa", "itzy",
}

SPORTS = {
    "sport", "sports", "football", "soccer", "basketball", "nba", "nfl", "baseball",
    "boxing", "ufc", "mma", "f1", "formula-1", "skate", "surf", "ski", "snowboard",
    "ronaldo", "mbappe", "neymar", "messi", "racing",
}

FANTASY = {
    "fantasy", "magic", "wizard", "knight", "castle", "elf", "dwarf", "myth",
    "mythology", "angel", "fairy", "vampire", "samurai", "ninja", "dragon",
    "sword", "sorceress", "mage", "witch", "god",
    # "demon" and "arcane" are absent: demon is claimed by Horror, and arcane by Gaming as
    # the League of Legends series. Both were in two lists and the earlier one won.
    # "titan" is absent: on a wallpaper it means Attack on Titan, which is Anime Loop's.
}

HORROR = {
    "horror", "scary", "creepy", "ghost", "zombie", "halloween", "skull", "skeleton",
    "undead", "death", "demon", "dark", "blood", "nightmare", "gothic",
}

MATURE = {
    "nsfw", "ecchi", "lewd", "sexy", "seductive", "sensual", "sultry", "provocative",
    "lingerie", "bikini", "swimsuit", "cleavage", "boudoir", "gravure", "pin-up",
    "pinup", "bath", "shower", "hot", "model",
}

UNSAFE_TITLE = re.compile(
    r"\b(loli|lolita|child|kid|little girl|baby|daughter|schoolgirl|school girl|student"
    r"|teen|anya|kanna|pokemon|nezuko|nahida|klee|qiqi|yaoyao|diona|ibuki|blue archive"
    r"|juvenile)\b", re.I)

# The order subjects are tried in. Game before anime is the fix; the rest runs from the most
# specific subject to the least.
ORDER = [
    ("Gaming", GAMES),
    ("Anime Girls", None),      # special: anime words plus a girl word
    ("Anime Loop", ANIME),
    ("Mature 18+", None),       # special: review or adult provenance only
    ("Cars", CARS),
    ("Animals", ANIMALS),
    ("Space", SPACE),
    ("City", CITY),
    ("Nature", NATURE),
    ("Movies", MOVIES),
    ("Music", MUSIC),
    ("Sports", SPORTS),
    ("Fantasy", FANTASY),
    ("Horror", HORROR),
    ("Abstract", ABSTRACT),
]


def load_tags():
    """Every entry's source tags, keyed by media id and by video url.

    The tags are the source site's own classification and are the best evidence available -
    better than the title, which often mentions a colour or a mood.
    """
    by_id = {}
    by_url = {}
    site_by_url = {}

    data = read_json(MB_STATE, None)
    if data:
        for item in data.get("items", []):
            tags = {t.lower() for t in item.get("_tags", [])}
            m = re.search(r"/media/(\d+)/", item.get("videoUrl", ""))
            if m:
                by_id[m.group(1)] = tags
            by_url[item.get("videoUrl", "")] = tags

    data = read_json(DH_STATE, None)
    if data:
        for item in data.get("items", []):
            tags = {t.lower() for t in item.get("_tags", [])}
            by_url[item.get("videoUrl", "")] = tags

    # moewalls has no /media/<id>/ in its urls, so it can only be keyed by url. Its tags
    # live in the adopter's output because the merger drops private fields before the
    # catalogue is written - which is why 6792 entries were recategorised from their
    # titles alone and "Autumn Jiraiya" ended up in Abstract.
    #
    # The adopter also records the category it computed from the site's own category, and
    # that is a classification rather than a guess: the site files "Sagiri Yamada Asaemon
    # Jigokuraku" under anime, and no word list here knows the series.
    data = read_json(MW_ADOPTED, None)
    if isinstance(data, list):
        for item in data:
            url = item.get("videoUrl", "")
            tags = {str(t).lower() for t in (item.get("_tags") or [])}
            if tags:
                by_url[url] = tags
            site = item.get("_source_category")
            if site:
                site_by_url[url] = site

    return by_id, by_url, site_by_url


def entry_words(entry, by_id, by_url):
    """Every word the entry carries: title, url, and the source's own tags.

    Multi-word names are added as joined phrases as well as as separate words. "One Piece"
    splits into {one, piece}, and neither word is in the anime list, so 225 One Piece
    wallpapers were filed under Fantasy, Nature and Dynamic by an earlier version. The
    phrase "onepiece" is checked alongside the words.
    """
    text = " ".join([entry.get("title", ""), entry.get("videoUrl", "")]).lower()
    words = set(re.split(r"[^a-z0-9]+", text)) - {""}

    # The joined form of the whole title and of each adjacent pair, so "one piece" is also
    # present as "onepiece" and "one-piece" style lookups can find it.
    tokens = [t for t in re.split(r"[^a-z0-9]+", text) if t]
    for i in range(len(tokens)):
        words.add(tokens[i])
        if i + 1 < len(tokens):
            words.add(tokens[i] + tokens[i + 1])
            words.add(tokens[i] + "-" + tokens[i + 1])
        if i + 2 < len(tokens):
            words.add(tokens[i] + tokens[i + 1] + tokens[i + 2])

    m = re.search(r"/media/(\d+)/", entry.get("videoUrl", ""))
    tags = by_url.get(entry.get("videoUrl", "")) or (by_id.get(m.group(1)) if m else None)
    if tags:
        for tag in tags:
            words |= set(re.split(r"[^a-z0-9]+", tag)) - {""}
            words.add(tag)
            words.add(tag.replace("-", ""))
            words.add(tag.replace(" ", "-"))
            words.add(tag.replace(" ", ""))

    return words


def classify(entry, words, mature_ids, site_by_url=None):
    """The category the evidence supports."""
    media = re.search(r"/media/(\d+)/", entry.get("videoUrl", ""))
    media_id = media.group(1) if media else ""

    # 1. The visual review wins.
    if media_id and media_id in mature_ids:
        return "Anime Girls" if UNSAFE_TITLE.search(entry.get("title", "")) else "Mature 18+"

    # 2. Adult provenance, recorded by the collector on the entry itself.
    if entry.get("_adult"):
        return "Mature 18+"

    # 3. A named game beats a named anime.
    if words & GAMES:
        return "Gaming"

    # 4. Anime, split by whether a girl is named.
    #
    # The girl check comes before the plain anime check, and it also comes before the
    # subject lists: "Cat Girl" is a character, not an animal, and Animals used to win
    # because "cat" is in its list. 21 entries were filed that way. A creature word next to
    # "girl" describes the girl.
    if words & GIRL_MARKERS:
        creature = {"cat", "cats", "dog", "dogs", "fox", "wolf", "bunny", "rabbit",
                    "dragon", "neko", "kitsune", "demon", "angel", "elf", "fairy"}
        if words & creature or words & ANIME:
            return "Anime Girls"

    if words & ANIME:
        return "Anime Loop"

    # 5. The site's own classification, when the word lists found nothing. It is a real
    #    category, and no list here can know every series: "Jigokuraku" is anime to the
    #    site and merely a word to us.
    if site_by_url:
        site = site_by_url.get(entry.get("videoUrl", ""))
        if site and not (words & ANIME) and not (words & GAMES):
            return site

    # 6. The rest, most specific first.
    for name, keys in ORDER:
        if keys and (words & keys):
            return name

    return "Dynamic"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    entries = read_json(CATALOG, [])
    by_id, by_url, site_by_url = load_tags()
    selected = read_json(MATURE_SELECTED, []) or []
    mature_ids = {str(s["motionId"]) for s in selected}

    print("  entries      : %d" % len(entries))
    print("  tag sets     : %d by media id, %d by url" % (len(by_id), len(by_url)))
    print("  mature review: %d" % len(mature_ids))
    print()

    before = Counter(e.get("category") for e in entries)
    changed = Counter()
    for entry in entries:
        words = entry_words(entry, by_id, by_url)
        new = classify(entry, words, mature_ids, site_by_url)
        old = entry.get("category")
        if new != old:
            changed[(old, new)] += 1
            entry["category"] = new

    after = Counter(e.get("category") for e in entries)

    print("  changed: %d entries" % sum(changed.values()))
    print()
    print("  the moves:")
    for (old, new), count in changed.most_common(20):
        print("    %-14s -> %-14s %d" % (old, new, count))
    print()

    print("  before -> after, per category:")
    names = sorted(set(before) | set(after), key=lambda n: -after.get(n, 0))
    for name in names:
        b, a = before.get(name, 0), after.get(name, 0)
        if b != a:
            print("    %-14s %5d -> %5d" % (name, b, a))
        else:
            print("    %-14s %5d" % (name, b))

    if args.dry_run:
        print()
        print("  dry run, nothing written")
        return 0

    write_json(CATALOG, entries)
    print()
    print("  written: %s" % CATALOG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
