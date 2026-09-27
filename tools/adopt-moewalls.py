"""Adopt the moewalls and wallpaperwaifu collections, measuring every file.

Why these two sources: the catalogue needs entries and these supply 12347 with a direct
video url each. Both were collected by a subagent, and both need work before they can be
used:

  * The resolution was recorded from the page, and on these sites the page states its own
    image size rather than the video's. The same mistake produced 960x540 files labelled
    1920x1080 once already, so every file is measured here and the measurement is what the
    catalogue keeps.

  * The download endpoint answers with `application/octet-stream` and often without a
    Content-Length, so a HEAD request cannot tell whether the file is real. The first
    kilobyte is fetched instead and the MP4 signature (`ftyp`) is checked - a file that
    starts with `ftypmp42` is a video, and an HTML error page is not.

  * moewalls and wallpaperwaifu are where the mature entries come from. A site's own
    category is used when it has one, and the tag list otherwise.

Both sites rate-limit, so the run pauses on 429 and keeps its progress in a file.

Run: python tools/adopt-moewalls.py [--workers 10] [--limit N]
"""

import argparse
import concurrent.futures as cf
import json
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from atomicjson import write_json, read_json
from clean_titles import clean_title
from mp4size import size_from_bytes, size_from_sample_entry

COLLECT = ROOT / "build" / "collect"
OUT = ROOT / "build" / "catalog-moewalls"
STATE = OUT / "state.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

FFPROBE = shutil.which("ffprobe") or shutil.which("ffprobe.exe")

# The words that make an entry mature. These sites file swimwear, lingerie and boudoir under
# their own categories, and the tag list says the same thing in words.
MATURE_WORDS = {
    "nsfw", "ecchi", "lewd", "sexy", "seductive", "sensual", "sultry", "provocative",
    "lingerie", "bikini", "swimsuit", "cleavage", "boudoir", "gravure", "pin-up", "pinup",
    "bath", "shower", "hot", "seductive", "risque", "suggestive", "sexy-girl", "hot-girl",
}

# Subjects that mean an entry is NOT mature, whatever else its words say. A landscape with
# the word "hot" in its title - "Hot Desert" - is a landscape.
SAFE_WORDS = {
    "landscape", "mountain", "forest", "ocean", "sea", "beach-sunset", "sunset", "sunrise",
    "sky", "cloud", "rain", "snow", "flower", "tree", "grass", "desert", "jungle",
    "waterfall", "river", "lake", "city", "street", "building", "car", "cars", "bike",
    "space", "galaxy", "planet", "star", "nebula", "abstract", "particle", "gradient",
    "cat", "dog", "wolf", "lion", "tiger", "bird", "eagle", "fish", "shark", "horse",
    "logo", "text", "map", "clock", "calendar", "chart", "graph",
}


def safe_url(url):
    """Percent-encode the path so urllib can send it."""
    from urllib.parse import quote, urlsplit, urlunsplit
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%:@&=+$,~()!'*-._")
    query = quote(parts.query, safe="/%:@&=+$,~()!'*-._?=&")
    return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def measure(url, attempts=4):
    """The video's real pixel size, and whether the file is a video at all.

    The download endpoint gives no Content-Length, so a HEAD cannot confirm the file. The
    first bytes are read instead: an MP4 begins with a box header containing `ftyp`, and an
    HTML error page begins with `<`.

    The dimensions are read out of the `tkhd` box directly rather than through ffprobe.
    These files are written without faststart, so the `moov` atom - which holds `tkhd` - sits
    at the end, and ffprobe refuses a tail-only file because the box offsets inside `moov`
    point into a file that is not there ("moov atom not found"). Reading the fixed offset
    inside `tkhd` needs neither the whole file nor an external tool. The first version of
    this measured 3 files out of 30 for exactly that reason.
    """
    url = safe_url(url)
    tmp = Path(tempfile.gettempdir()) / ("mw-%d.bin" % abs(hash(url)))

    for attempt in range(attempts):
        try:
            # The head carries `ftyp`, and `moov` too when faststart was used.
            req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-1200000"})
            with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
                head = r.read()
                total = 0
                cr = r.headers.get("Content-Range") or ""
                if "/" in cr:
                    try:
                        total = int(cr.split("/")[-1])
                    except ValueError:
                        total = 0

            if not head or b"ftyp" not in head[:64]:
                return None

            found = size_from_bytes(head) or size_from_sample_entry(head)
            if found:
                return found

            # No dimensions in the head, so `moov` is at the end.
            if total > 1200000:
                start = max(0, total - 1200000)
                req = urllib.request.Request(
                    url, headers={**UA, "Range": "bytes=%d-%d" % (start, total - 1)})
                with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                    tail = r.read()
                found = size_from_bytes(tail) or size_from_sample_entry(tail)
                if found:
                    return found

            # The total size was not in the header; ask for a suffix range instead, which
            # some servers honour even when they omit Content-Range.
            req = urllib.request.Request(url, headers={**UA, "Range": "bytes=-1500000"})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                tail = r.read()
            if tail:
                found = size_from_bytes(tail) or size_from_sample_entry(tail)
                if found:
                    return found

            return None
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < attempts - 1:
                time.sleep(3 * (attempt + 1) + 3)
                continue
            return None
        except Exception:
            if attempt < attempts - 1:
                time.sleep(2)
                continue
            return None
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass

    return None


def load_source():
    """Both collections, joined to their page metadata by url."""
    entries = []

    for token_file, meta_file, host in [
        ("tokens-moewalls.jsonl", "moewalls.jsonl", "moewalls"),
        ("tokens-wallpaperwaifu.jsonl", "wallpaperwaifu.jsonl", "wallpaperwaifu"),
    ]:
        tokens = COLLECT / token_file
        meta = COLLECT / meta_file
        if not tokens.exists():
            print("  %s: missing" % token_file)
            continue

        # The metadata file has the title, category and tags; the token file has the url.
        by_url = {}
        if meta.exists():
            for line in meta.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                by_url[d.get("url", "")] = d

        count = 0
        for line in tokens.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                t = json.loads(line)
            except Exception:
                continue
            page = t.get("url", "")
            m = by_url.get(page, {})
            entries.append({
                "title": m.get("title", ""),
                "videoUrl": t.get("videoUrl", ""),
                "thumbnailUrl": m.get("thumb", ""),
                "sourceUrl": page,
                "pageCategory": m.get("cat", ""),
                "tags": m.get("tags", []) or [],
                "w": m.get("w", 0),
                "h": m.get("h", 0),
                "host": host,
            })
            count += 1
        print("  %-24s %d entries" % (token_file, count))

    return entries


# Tags that mark an entry as generated rather than drawn. moewalls labels 306 of its 9748
# entries this way; the catalogue must be artwork, so they are dropped at the source rather
# than filtered later where the tag is no longer available.
AI_TAGS = {"ai-art", "ai", "ai-generated", "aiart", "midjourney", "stable-diffusion",
           "sdxl", "novelai", "dall-e"}


def is_generated(entry):
    """True when the source labels this entry as generated art."""
    tags = {str(t).lower().strip() for t in (entry.get("tags") or [])}
    if tags & AI_TAGS:
        return True
    return False


def categorise(entry, tags, title):
    """The category, from the site's own category first and the tags second."""
    words = set()
    for t in tags:
        words |= set(re.split(r"[^a-z0-9]+", str(t).lower())) - {""}
    words |= set(re.split(r"[^a-z0-9]+", (title or "").lower())) - {""}

    # Mature needs both a justifying word and no plainly ordinary subject.
    if words & MATURE_WORDS and not (words & SAFE_WORDS):
        return "Mature 18+"

    rules = [
        ("Gaming", {"game", "games", "gaming", "valorant", "league", "genshin", "honkai",
                    "zelda", "mario", "pokemon", "fortnite", "minecraft", "elden", "witcher"}),
        ("Anime Girls", {"anime-girl", "waifu", "idol", "kimono", "maid", "neko", "catgirl",
                         "vtuber", "cosplay", "girl"}),
        ("Anime Loop", {"anime", "manga", "naruto", "one-piece", "bleach", "gundam",
                        "jujutsu", "demon-slayer", "attack-on-titan", "chainsaw"}),
        ("Nature", {"nature", "landscape", "forest", "mountain", "ocean", "sea", "beach",
                    "waterfall", "river", "lake", "sunset", "sunrise", "flower", "tree",
                    "rain", "snow", "autumn", "spring", "summer", "winter"}),
        ("City", {"city", "urban", "street", "neon", "tokyo", "skyline", "building",
                  "cyberpunk", "vaporwave", "synthwave"}),
        ("Space", {"space", "galaxy", "nebula", "planet", "star", "cosmos", "astronaut",
                   "universe", "moon", "mars", "saturn", "earth"}),
        ("Cars", {"car", "cars", "supercar", "jdm", "racing", "motorcycle", "bike", "bmw",
                  "ferrari", "lamborghini", "porsche", "nissan", "toyota"}),
        ("Animals", {"animal", "cat", "dog", "wolf", "lion", "tiger", "bird", "fish",
                     "shark", "horse", "fox", "dragon"}),
        ("Abstract", {"abstract", "particle", "geometric", "pattern", "fluid", "gradient",
                      "smoke", "ink", "minimal", "3d", "render", "loop"}),
        ("Movies", {"movie", "film", "marvel", "dc", "star-wars", "batman", "joker",
                    "superhero", "avengers"}),
        ("Music", {"music", "concert", "band", "guitar", "piano", "dj", "singer", "kpop"}),
        ("Sports", {"sport", "football", "soccer", "basketball", "nba", "boxing", "ufc"}),
        ("Fantasy", {"fantasy", "magic", "wizard", "knight", "castle", "elf", "dragon",
                     "myth", "samurai", "ninja", "demon", "angel"}),
        ("Horror", {"horror", "scary", "creepy", "ghost", "zombie", "halloween", "skull",
                    "dark", "blood"}),
    ]
    for name, keys in rules:
        if words & keys:
            return name
    return "Dynamic"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    print("  loading sources")
    entries = load_source()
    print("  total: %d entries" % len(entries))
    print()

    if not entries:
        return 1

    state = read_json(STATE, {})
    done = state.get("measured", {})
    print("  already measured: %d" % len(done))

    todo = [e for e in entries if e["videoUrl"] and e["videoUrl"] not in done]
    if args.limit:
        todo = todo[:args.limit]
    print("  to measure: %d" % len(todo))
    print()

    processed = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(measure, e["videoUrl"]): e for e in todo}
        for future in cf.as_completed(futures):
            item = futures[future]
            try:
                size = future.result()
            except Exception:
                size = None
            done[item["videoUrl"]] = list(size) if size else None
            processed += 1
            if processed % 200 == 0:
                write_json(STATE, {"measured": done})
                readable = sum(1 for v in done.values() if v)
                print("    %d/%d measured, %d readable" % (processed, len(todo), readable))

    write_json(STATE, {"measured": done})

    # Build the adopted entries.
    adopted = []
    reasons = Counter()
    for e in entries:
        size = done.get(e["videoUrl"])
        if not size:
            reasons["unmeasurable"] += 1
            continue

        # The source's own label for generated art. Checked here rather than later because
        # the tag is only available at this point.
        if is_generated(e):
            reasons["generated"] += 1
            continue

        w, h = size
        if w < 1280 or h < 720:
            reasons["below-hd"] += 1
            continue
        if w <= h:
            reasons["portrait"] += 1
            continue

        title = clean_title(e["title"]) or "Untitled"
        adopted.append({
            "title": title,
            "videoUrl": e["videoUrl"],
            "thumbnailUrl": e["thumbnailUrl"],
            "license": "%s · free for personal use" % e["host"].capitalize(),
            "sourceUrl": e["sourceUrl"],
            "category": categorise(e, e["tags"], title),
            "kind": "dynamic",
            "author": "%s community" % e["host"].capitalize(),
            "animation": "",
            "resolution": "%dx%d" % (w, h),
        })

    write_json(OUT / "adopted.json", adopted)

    print()
    print("  measured : %d of %d" % (sum(1 for v in done.values() if v), len(done)))
    print("  adopted  : %d" % len(adopted))
    for reason, n in reasons.most_common():
        print("    dropped %-14s %d" % (reason, n))
    print()

    res = Counter(e["resolution"] for e in adopted)
    print("  resolution:")
    for k, n in res.most_common(8):
        print("    %-12s %5d  %4.1f%%" % (k, n, 100 * n / len(adopted)))
    big = sum(n for k, n in res.items() if int(k.split("x")[0]) >= 2560)
    print()
    print("  2K or better: %d (%.1f%%)" % (big, 100 * big / len(adopted)))

    cats = Counter(e["category"] for e in adopted)
    print()
    print("  categories:")
    for k, n in cats.most_common():
        print("    %-14s %5d  %4.1f%%" % (k, n, 100 * n / len(adopted)))

    print()
    print("  written: %s" % (OUT / "adopted.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
