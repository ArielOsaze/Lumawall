"""Collect motionbgs wallpapers that have a real 1920x1080 video.

Why this shape: the detail page links a 960x540 file and mentions 1920x1080 only in its
markup, so a catalogue built from the page would be a catalogue of SD files stretched to a
desktop - the "pecah" this must not have. The HD variant lives at the same path with a
different resolution suffix, so every entry is confirmed with a HEAD request before it is
kept, and anything without a 1920x1080 file is dropped rather than downgraded.

Progress is written after every batch so the run can be resumed rather than restarted.

Run: python tools/collect-motionbgs.py [--limit N] [--workers N]
"""

import argparse
import concurrent.futures as cf
import json
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json, read_json

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "catalog-scrape"
DONE = OUT / "done.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

LOCK = threading.Lock()


def get(url, method="GET", timeout=25):
    req = urllib.request.Request(url, method=method, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace"), r.status, dict(r.headers)


def head_ok(url):
    """True when the URL exists and is a video. Content-Type is checked because the site
    answers some missing files with an HTML error page at status 200."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            size = int(r.headers.get("Content-Length") or 0)
            if r.status != 200:
                return None
            if "video" not in ctype and not url.endswith((".mp4", ".webm")):
                return None
            if size < 100_000:      # a real 1080p loop is megabytes, not kilobytes
                return None
            return size
    except Exception:
        return None


# Tag words mapped to the catalogue's own categories. The order matters: the first match
# wins, so the specific words come before the general ones. Without this every entry would
# land in one bucket and the "kategorinya sesuai" requirement would not be met.
CATEGORY_RULES = [
    ("Mature 18+", {
        "nsfw", "ecchi", "lewd", "sexy", "seductive", "lingerie", "bikini", "cleavage",
        "sensual", "pin-up", "pinup", "boudoir", "lingerie", "sultry", "provocative",
        "hot-girl", "waifu", "gravure",
    }),
    ("Anime Girls", {
        "anime-girl", "anime-girls", "waifu", "girl", "girls", "idol", "schoolgirl",
        "kimono", "maid", "neko", "catgirl", "vtuber",
    }),
    ("Anime Loop", {
        "anime", "manga", "shonen", "seinen", "isekai", "mecha", "gundam", "naruto",
        "one-piece", "jujutsu", "demon-slayer", "attack-on-titan", "genshin", "honkai",
        "arknights", "azur-lane", "blue-archive", "fate", "evangelion",
    }),
    ("Gaming", {
        "game", "gaming", "valorant", "league-of-legends", "dota", "counter-strike",
        "csgo", "cs2", "fortnite", "apex", "overwatch", "minecraft", "cyberpunk",
        "elden-ring", "witcher", "gta", "call-of-duty", "battlefield", "pubg", "roblox",
        "genshin-impact", "zelda", "mario", "pokemon", "sonic",
    }),
    ("Nature", {
        "nature", "landscape", "forest", "mountain", "ocean", "sea", "beach", "waterfall",
        "river", "lake", "sunset", "sunrise", "sky", "cloud", "rain", "snow", "winter",
        "autumn", "spring", "summer", "flower", "tree", "grass", "desert", "jungle",
        "underwater", "aurora", "storm", "lightning",
    }),
    ("City", {
        "city", "urban", "street", "neon", "cyberpunk", "tokyo", "night-city", "skyline",
        "building", "architecture", "bridge", "traffic", "subway", "downtown", "vaporwave",
        "synthwave", "retrowave",
    }),
    ("Space", {
        "space", "galaxy", "nebula", "planet", "star", "cosmos", "astronaut", "universe",
        "moon", "mars", "saturn", "earth", "black-hole", "sci-fi", "scifi", "spaceship",
    }),
    ("Cars", {
        "car", "cars", "supercar", "jdm", "drift", "racing", "motorcycle", "bike",
        "ferrari", "lamborghini", "porsche", "bmw", "nissan", "toyota", "honda",
    }),
    ("Animals", {
        "animal", "animals", "cat", "cats", "dog", "dogs", "wolf", "lion", "tiger",
        "bird", "eagle", "owl", "fish", "shark", "whale", "dolphin", "horse", "fox",
        "bear", "dragon", "snake", "corgi",
    }),
    ("Abstract", {
        "abstract", "particle", "geometric", "pattern", "fluid", "gradient", "smoke",
        "ink", "light", "glow", "loop", "minimal", "3d", "render", "waveform", "audio",
    }),
    ("Movies", {
        "movie", "film", "cinema", "marvel", "dc", "star-wars", "harry-potter", "matrix",
        "avengers", "spiderman", "batman", "joker", "stranger-things",
    }),
    ("Music", {
        "music", "concert", "band", "guitar", "piano", "dj", "singer", "kpop", "bts",
        "sabrina-carpenter", "billie-eilish", "taylor-swift",
    }),
    ("Sports", {
        "sport", "football", "soccer", "basketball", "nba", "nfl", "baseball", "boxing",
        "ufc", "mma", "f1", "formula-1", "skate", "surf", "ski", "snowboard",
    }),
    ("Fantasy", {
        "fantasy", "magic", "wizard", "knight", "castle", "elf", "dwarf", "myth",
        "mythology", "demon", "angel", "fairy", "vampire", "samurai", "ninja",
    }),
    ("Horror", {
        "horror", "scary", "creepy", "dark", "ghost", "zombie", "halloween", "skull",
        "skeleton", "death", "demon",
    }),
]

MATURE_HINTS = CATEGORY_RULES[0][1]


def categorise(title, tags, slug):
    """Pick the category from the tags, then the title, then the slug."""
    words = set()
    for t in tags:
        words.add(t.lower().replace(" ", "-").replace("_", "-"))
    title_words = re.split(r"[^a-z0-9]+", title.lower())
    words.update(w for w in title_words if w)
    slug_words = set(re.split(r"[^a-z0-9]+", slug.lower()))
    words |= slug_words

    for name, keys in CATEGORY_RULES:
        if words & keys:
            return name

    # A joined form, because tags often arrive as "animegirl" rather than "anime-girl".
    joined = " ".join(sorted(words))
    for name, keys in CATEGORY_RULES:
        for key in keys:
            if len(key) >= 5 and key.replace("-", "") in joined.replace("-", ""):
                return name

    return "Dynamic"


# The catalogue must be artwork, not generated images. The site tags its generated pieces
# with "ai", and a title that says "(AI)" is the same statement in words.
AI_TAGS = {"ai", "ai-art", "ai-generated", "midjourney", "stable-diffusion", "sdxl"}


def is_generated(item):
    tags = {t.lower() for t in item.get("_tags", [])}
    if tags & AI_TAGS:
        return True
    title = item.get("title", "").lower()
    return "(ai)" in title or "ai generated" in title or "midjourney" in title


def page_tags(html):
    """The tags belonging to THIS wallpaper.

    The page carries a site-wide tag menu listing hundreds of tags - football, ronaldo,
    japan, torii - and a regex over the whole document picks those up instead of the page's
    own. That made every entry look like it was tagged "anime", so the whole catalogue was
    filed under Anime Girls. The page's own tags are the ones in the subtags list.
    """
    block = re.search(r'<ul class="subtags[^"]*">(.*?)</ul>', html, re.S)
    if not block:
        return []
    tags = re.findall(r"/tag:([a-z0-9\-_]+)/", block.group(1), re.I)
    # Keep the order they appear in and drop duplicates.
    seen = []
    for t in tags:
        t = t.lower()
        if t not in seen:
            seen.append(t)
    return seen


def parse_page(html, url, slug):
    """Pull the title, tags, poster and the HD video URL out of a detail page."""
    title = ""
    m = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html)
    if m:
        title = m.group(1)
    if not title:
        m = re.search(r"<title>([^<]*)</title>", html)
        if m:
            title = m.group(1)
    title = re.sub(r"\s*[-|]\s*MotionBGs.*$", "", title, flags=re.I).strip()
    title = title.replace("&amp;", "&").replace("&#039;", "'").replace("&quot;", '"')

    poster = ""
    m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
    if m:
        poster = m.group(1)

    tags = page_tags(html)

    # The HD video, if the page offers it.
    mp4 = re.search(r"https?://motionbgs\.com/media/\d+/[^\"'\s\\<>]+\.1920x1080\.mp4", html)
    sd = re.search(r"https?://motionbgs\.com/media/\d+/[^\"'\s\\<>]+\.960x540\.mp4", html)

    video = mp4.group(0) if mp4 else ""
    if not video and sd:
        # The HD sibling shares the path, so it can be probed directly.
        video = re.sub(r"\.960x540\.mp4$", ".1920x1080.mp4", sd.group(0))

    return {
        "title": title or slug.replace("-", " ").title(),
        "videoUrl": video,
        "thumbnailUrl": poster,
        "license": "MotionBGs · free for personal use",
        "sourceUrl": url,
        "category": "",
        "kind": "dynamic",
        "author": "MotionBGs community",
        "animation": "",
        "_tags": tags,
        "_slug": slug,
    }


def work(slug):
    url = "https://motionbgs.com/" + slug
    try:
        html, _, _ = get(url)
    except urllib.error.HTTPError as e:
        return {"slug": slug, "status": "http-%d" % e.code}
    except Exception as e:
        return {"slug": slug, "status": type(e).__name__}

    item = parse_page(html, url, slug)
    if not item["videoUrl"]:
        return {"slug": slug, "status": "no-video"}

    if is_generated(item):
        return {"slug": slug, "status": "ai-generated"}

    size = head_ok(item["videoUrl"])
    if not size:
        return {"slug": slug, "status": "no-hd"}

    if item["thumbnailUrl"]:
        if not head_ok(item["thumbnailUrl"].replace(".960x540.", ".1920x1080.")):
            item["thumbnailUrl"] = item["thumbnailUrl"]

    item["_bytes"] = size
    item["category"] = categorise(item["title"], item["_tags"], slug)
    return {"slug": slug, "status": "ok", "item": item}


def load_done():
    if DONE.exists():
        return json.loads(DONE.read_text(encoding="utf-8"))
    return {"slugs": [], "items": [], "failed": {}}


def save_done(state):
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(DONE, state)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    state = load_done()
    seen = set(state["slugs"])

    # The slug list comes from the sitemap, which is the site's own index of its pages.
    sitemap_file = OUT / "sitemap-slugs.txt"
    if not sitemap_file.exists():
        print("  fetching the sitemap")
        xml, _, _ = get("https://motionbgs.com/sitemap.xml")
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
        slugs = []
        for loc in locs:
            path = loc.replace("https://motionbgs.com/", "").strip("/")
            if not path or path.startswith("tag:") or "/" in path:
                continue
            if path in ("4k", "gifs", "mobile"):
                continue
            slugs.append(path)
        sitemap_file.write_text("\n".join(slugs), encoding="utf-8")
        print("  %d slugs" % len(slugs))

    slugs = [s for s in sitemap_file.read_text(encoding="utf-8").split("\n") if s]
    todo = [s for s in slugs if s not in seen]
    if args.limit:
        todo = todo[:args.limit]

    print("  slugs total   : %d" % len(slugs))
    print("  already done  : %d" % len(seen))
    print("  this run      : %d" % len(todo))
    print()

    if not todo:
        print("  nothing to do")
        return 0

    started = time.time()
    batch = []
    done_count = 0
    ok_count = 0

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(work, s): s for s in todo}
        for future in cf.as_completed(futures):
            result = future.result()
            batch.append(result)
            done_count += 1

            if result["status"] == "ok":
                ok_count += 1
                state["items"].append(result["item"])
            else:
                state["failed"][result["slug"]] = result["status"]

            state["slugs"].append(result["slug"])

            # Save every 100 so a stop does not lose the work.
            if len(batch) >= 100:
                with LOCK:
                    save_done(state)
                elapsed = time.time() - started
                rate = done_count / elapsed if elapsed else 0
                remaining = (len(todo) - done_count) / rate if rate else 0
                print("  %5d/%d  ok=%-5d  %.1f/s  eta %.0fs"
                      % (done_count, len(todo), ok_count, rate, remaining))
                batch = []

    save_done(state)
    print()
    print("  done     : %d" % done_count)
    print("  with HD  : %d" % ok_count)
    print("  dropped  : %d" % (done_count - ok_count))
    print("  total now: %d" % len(state["items"]))
    print("  state    : %s" % DONE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
