"""Collect desktophut wallpapers whose real resolution is HD or better.

Why a second source: motionbgs supplies about 9600 entries and the catalogue needs 15000, so
a second source is required. desktophut advertises 67000+ live wallpapers and states its
uploads are CC0.

Why the file is measured rather than trusted: the listing pages carry no video URL at all,
and the site's own resolution text describes its page images, not the video. A file's real
size only appears in its MP4 header, so each candidate is measured with ffprobe before it is
kept - an entry that claimed 4K and delivered 640x360 would be exactly the "pecah" the
catalogue must not have.

The preview file is skipped: it is a 300 KB thumbnail animation, not the wallpaper.

Run: python tools/collect-desktophut.py [--limit N] [--workers N]
"""

import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json, read_json

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "catalog-desktophut"
DONE = OUT / "done.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# The catalogue's categories, matched against the slug. First match wins, so the specific
# words come first and the general ones act as a floor.
CATEGORY_RULES = [
    ("Mature 18+", {
        "nsfw", "ecchi", "lewd", "sexy", "seductive", "lingerie", "bikini", "cleavage",
        "sensual", "pin-up", "pinup", "boudoir", "sultry", "provocative", "gravure",
        "swimsuit", "hot-girl", "waifu", "bath", "shower",
    }),
    ("Anime Girls", {
        "anime-girl", "anime-girls", "waifu", "idol", "schoolgirl", "kimono", "maid",
        "neko", "catgirl", "vtuber", "girl",
    }),
    ("Anime Loop", {
        "anime", "manga", "shonen", "seinen", "isekai", "mecha", "gundam", "naruto",
        "one-piece", "jujutsu", "demon-slayer", "attack-on-titan", "genshin", "honkai",
        "arknights", "azur-lane", "blue-archive", "fate", "evangelion", "chainsaw-man",
    }),
    ("Gaming", {
        "game", "gaming", "valorant", "league-of-legends", "dota", "counter-strike",
        "csgo", "cs2", "fortnite", "apex", "overwatch", "minecraft", "cyberpunk",
        "elden-ring", "witcher", "gta", "call-of-duty", "battlefield", "pubg", "roblox",
        "zelda", "mario", "pokemon", "sonic", "destiny", "warcraft", "diablo", "halo",
    }),
    ("Nature", {
        # "summer", "spring", "autumn" and "winter" are deliberately NOT here. They are
        # season words that appear in titles about people far more often than in titles
        # about landscapes - "Sabrina Carpenter Summer" was filed as Nature by an earlier
        # version of this list. The landscape words that do appear are unambiguous.
        "nature", "landscape", "forest", "mountain", "ocean", "sea", "beach-sunset",
        "waterfall", "river", "lake", "sunset", "sunrise", "cloud", "rain", "snowfall",
        "autumn-leaves", "spring-flowers", "summer-beach", "flower", "tree", "grass",
        "desert", "jungle", "underwater", "aurora", "storm", "lightning", "garden",
        "waterfall", "mountain-range", "forest-path", "ocean-waves", "nature-scene",
    }),
    ("City", {
        "city", "urban", "street", "neon", "tokyo", "skyline", "building", "architecture",
        "bridge", "traffic", "subway", "downtown", "vaporwave", "synthwave", "retrowave",
    }),
    ("Space", {
        "space", "galaxy", "nebula", "planet", "star", "cosmos", "astronaut", "universe",
        "moon", "mars", "saturn", "earth", "black-hole", "sci-fi", "scifi", "spaceship",
    }),
    ("Cars", {
        "car", "cars", "supercar", "jdm", "drift", "racing", "motorcycle", "bike",
        "ferrari", "lamborghini", "porsche", "bmw", "nissan", "toyota", "honda", "audi",
    }),
    ("Animals", {
        "animal", "cat", "dog", "wolf", "lion", "tiger", "bird", "eagle", "owl", "fish",
        "shark", "whale", "dolphin", "horse", "fox", "bear", "dragon", "snake", "corgi",
    }),
    ("Abstract", {
        "abstract", "particle", "geometric", "pattern", "fluid", "gradient", "smoke",
        "ink", "glow", "minimal", "render", "waveform", "visualizer", "audio",
    }),
    ("Movies", {
        "movie", "film", "cinema", "marvel", "dc", "star-wars", "harry-potter", "matrix",
        "avengers", "spiderman", "batman", "joker", "stranger-things",
    }),
    ("Music", {
        "music", "concert", "band", "guitar", "piano", "dj", "singer", "kpop", "bts",
        # Named performers. A title that names one is about the person, and the sites file
        # those under music or celebrity rather than under whatever season the title mentions.
        "sabrina-carpenter", "billie-eilish", "taylor-swift", "ariana-grande", "rihanna",
        "beyonce", "lady-gaga", "dua-lipa", "selena-gomez", "demi-lovato", "miley-cyrus",
        "blackpink", "twice", "stray-kids", "newjeans", "aespa", "ive", "itzy",
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
        "horror", "scary", "creepy", "ghost", "zombie", "halloween", "skull",
        "skeleton", "undead", "death",
    }),
]

FFPROBE = shutil.which("ffprobe") or shutil.which("ffprobe.exe")

# The words that mark camera footage rather than artwork. The site mixes the two in one
# listing, and a catalogue of artwork must not contain a quarter stock video of a doctor in
# an office. Compiled once and used by both the filter and the adult list.
STOCK_MARKERS_RE = re.compile(
    r"stock-video|free-stock|stock-footage|video-stock|-stock-|footage|free-video"
    r"|stock-clip|royalty-free|business-people|office-worker", re.I)

# The urls that came from an adult tag on the source site, loaded once at startup. An entry
# from one of these is filed as mature on the strength of the site's own filing rather than
# on a word in its slug.
#
# Stock footage is filtered out of this list as well: the site's /tag/adult contains camera
# footage of women in offices and mirrors, which is "adult" in the demographic sense and not
# the sense this category means. A mature entry has to be artwork.
ADULT_URLS = set()
_adult_file = OUT / "adult-urls.json"
if _adult_file.exists():
    try:
        import json as _json
        _all = _json.loads(_adult_file.read_text(encoding="utf-8")).get("urls", [])
        ADULT_URLS = {u for u in _all if not STOCK_MARKERS_RE.search(u)}
    except Exception:
        ADULT_URLS = set()


def safe_url(url):
    """Percent-encode the path so urllib can send it.

    Wallpaper files carry titles in Japanese and Chinese, and urllib raises
    UnicodeEncodeError on a path it cannot encode. That was recorded as "unmeasurable" and
    silently dropped real files. Only the path is re-encoded.
    """
    from urllib.parse import quote, urlsplit, urlunsplit
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%:@&=+$,~()!'*-._")
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace"), r.status


def probe_resolution(url):
    """The video's real pixel size, read from the file itself.

    The site states a resolution in its page markup, but that text describes its page
    images - every detail page says 1500x1000, 1800x1125 and 1280x1200 regardless of the
    video. Reading the file is the only way to know what a wallpaper actually is.

    Only the first 2 MB and the last 2 MB are fetched, because the MP4 header may be at
    either end and the files run to tens of megabytes.
    """
    if not FFPROBE:
        return None

    tmp = Path(tempfile.gettempdir()) / ("dh-%s.mp4" % abs(hash(url)))
    try:
        # ffprobe needs a seekable file for the moov atom, so the head is fetched first and
        # the tail appended when the head does not carry the header.
        req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-2000000"})
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            head = r.read()
        tmp.write_bytes(head)

        result = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", str(tmp)],
            capture_output=True, text=True, timeout=40,
        )
        text = (result.stdout or "").strip()
        if "," in text:
            w, h = text.split(",")[:2]
            return int(w), int(h)
        return None
    except Exception:
        return None
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass


def categorise(slug, adult=False):
    """The category for an entry.

    When the url came from an adult tag the entry is mature by provenance, which is stronger
    evidence than any word in the slug: the site itself filed it under /tag/adult or
    /tag/bikini, and a person browsing that tag would expect to find it there.
    """
    if adult:
        return "Mature 18+"

    words = set(re.split(r"[^a-z0-9]+", slug.lower()))
    joined = "-".join(sorted(words))
    for name, keys in CATEGORY_RULES:
        if words & keys:
            return name
    for name, keys in CATEGORY_RULES:
        for key in keys:
            if len(key) >= 5 and key.replace("-", "") in joined.replace("-", ""):
                return name
    return "Dynamic"


def work(url):
    slug = url.rstrip("/").split("/")[-1]
    try:
        html, _ = get(url)
    except urllib.error.HTTPError as e:
        return {"slug": slug, "status": "http-%d" % e.code}
    except Exception as e:
        return {"slug": slug, "status": type(e).__name__}

    # Stock footage is not artwork. The site mixes camera footage and business clips into the
    # same listing as drawn and rendered wallpapers, and a catalogue of "artwork" that is a
    # quarter stock video of a doctor in an office is not the catalogue that was asked for.
    if STOCK_MARKERS_RE.search(slug):
        return {"slug": slug, "status": "stock-footage"}

    # The wallpaper file, not the small preview animation.
    files = re.findall(r'https?://[^"\'\s<>]+/files/[^"\'\s<>]+\.mp4', html)
    if not files:
        return {"slug": slug, "status": "no-file"}
    video = files[0]

    poster = ""
    m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
    if m:
        poster = m.group(1)

    title = ""
    m = re.search(r'<meta\s+property="og:title"\s+content="([^"]*)"', html)
    if m:
        title = m.group(1)
    if not title:
        m = re.search(r"<title>([^<]*)</title>", html)
        if m:
            title = m.group(1)
    title = re.sub(r"\s*[-|]\s*DesktopHut.*$", "", title, flags=re.I).strip()
    title = title.replace("&amp;", "&").replace("&#039;", "'").replace("&quot;", '"')

    size = probe_resolution(video)
    if not size:
        return {"slug": slug, "status": "unmeasurable"}

    width, height = size

    # HD means 1280x720 or better, and a desktop wallpaper has to be landscape. The site
    # carries a large number of portrait phone clips, and 720x1280 stretched across a
    # monitor is exactly the "pecah" this catalogue must not have.
    if width < 1280 or height < 720:
        return {"slug": slug, "status": "below-hd"}
    if width <= height:
        return {"slug": slug, "status": "portrait"}

    return {
        "slug": slug,
        "status": "ok",
        "item": {
            "title": title or slug.replace("-", " ").title(),
            "videoUrl": video,
            "thumbnailUrl": poster,
            "license": "DesktopHut · CC0",
            "sourceUrl": url,
            "category": categorise(slug, adult=url in ADULT_URLS),
            "kind": "dynamic",
            "author": "DesktopHut community",
            "animation": "",
            "resolution": "%dx%d" % (width, height),
        },
    }


def load():
    if DONE.exists():
        return json.loads(DONE.read_text(encoding="utf-8"))
    return {"slugs": [], "items": [], "failed": {}}


LOCK = OUT / "collector.lock"


def take_lock():
    """Refuse to start when another collector is already writing this state file.

    Two collectors writing done.json at once is what killed two runs with
    `PermissionError [WinError 5]` on os.replace: Windows will not replace a file another
    process holds open, and the retry window is not long enough for a run that writes every
    50 entries. The run that lost the race died after 11650 URLs.

    The lock records the pid so a stale lock - from a run that was killed, not one that is
    running - can be told apart and cleared.
    """
    if LOCK.exists():
        try:
            other = json.loads(LOCK.read_text(encoding="utf-8"))
            pid = int(other.get("pid", 0))
        except Exception:
            pid = 0
        alive = False
        if pid:
            import subprocess
            out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                                 capture_output=True, text=True)
            alive = str(pid) in (out.stdout or "")
        if alive:
            print("  another collector is already running (pid %d)." % pid)
            print("  Two writers on one state file lose writes: stop it, or wait.")
            return False
        print("  clearing a stale lock from pid %d" % pid)
    LOCK.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
    return True


def drop_lock():
    try:
        LOCK.unlink()
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--shuffle", action="store_true",
                    help="visit the sitemap in random order instead of page order")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    if not FFPROBE:
        print("  ffprobe was not found, so no file's resolution can be verified.")
        print("  Every entry would be an unverified claim. Install ffmpeg first.")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)

    if not take_lock():
        return 1

    state = load()
    seen = set(state["slugs"])

    # The slug list comes from the site's own sitemap.
    slugs_file = OUT / "slugs.txt"
    if not slugs_file.exists():
        print("  fetching the sitemap index")
        index, _ = get("https://www.desktophut.com/sitemap.xml")
        subs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", index)
        item_maps = [s for s in subs if "app-sitemap" in s]
        print("  %d item sitemaps" % len(item_maps))

        urls = []
        for i, sm in enumerate(item_maps, 1):
            try:
                page, _ = get(sm)
                urls += re.findall(r"<loc>\s*(https://www\.desktophut\.com/[^<\s]+)\s*</loc>", page)
            except Exception:
                pass
            if i % 20 == 0:
                print("    %d/%d sitemaps, %d urls" % (i, len(item_maps), len(urls)))

        urls = sorted(set(urls))
        slugs_file.write_text("\n".join(urls), encoding="utf-8")
        print("  %d urls" % len(urls))

    urls = [u for u in slugs_file.read_text(encoding="utf-8").split("\n") if u]

    # The sitemap is in page order, and page order is not a random sample: the first 300
    # entries were almost entirely stock footage and phone clips, which is why a run
    # limited to them kept nothing. Shuffling makes a partial run representative.
    if args.shuffle:
        import random
        random.Random(args.seed).shuffle(urls)

    todo = [u for u in urls if u.rstrip("/").split("/")[-1] not in seen]
    if args.limit:
        todo = todo[:args.limit]

    print()
    print("  urls total   : %d" % len(urls))
    print("  already done : %d" % len(seen))
    print("  this run     : %d" % len(todo))
    print()

    if not todo:
        print("  nothing to do")
        drop_lock()
        return 0

    done = 0
    ok = 0
    batch = []

    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(work, u): u for u in todo}
        for future in cf.as_completed(futures):
            result = future.result()
            batch.append(result)
            done += 1
            state["slugs"].append(result["slug"])
            if result["status"] == "ok":
                ok += 1
                state["items"].append(result["item"])
            else:
                state["failed"][result["slug"]] = result["status"]

            if len(batch) >= 50:
                # A state write that cannot land must not kill the run. Losing one snapshot
                # costs at most 50 URLs; dying costs everything collected so far, which is
                # what happened twice before the lock was added.
                try:
                    write_json(DONE, state)
                except Exception as e:
                    print("  %5d/%d  ok=%-5d  (state write deferred: %s)"
                          % (done, len(todo), ok, type(e).__name__))
                else:
                    print("  %5d/%d  ok=%-5d" % (done, len(todo), ok))
                batch = []

    write_json(DONE, state)
    print()
    print("  done     : %d" % done)
    print("  HD kept  : %d" % ok)
    print("  dropped  : %d" % (done - ok))
    print("  total now: %d" % len(state["items"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
