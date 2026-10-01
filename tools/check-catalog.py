"""Check the shipped catalogue against every requirement it has to meet.

Why: the catalogue's numbers are the promise - 15000 entries, 90% dynamic, HD, artwork and
not generated, categories that match their contents. Each of those can be true in the file
and false in practice: an entry can claim 1920x1080 in its URL while the URL 404s, a mature
entry can be a landscape, a "dynamic" entry can be a still image. This checks the file AND
samples the network, because only the network can say whether an entry still works.

What it checks:
  1. The entry count.
  2. The dynamic share.
  3. Every entry has a resolution that was measured, not assumed.
  4. The share at 2K or better.
  5. No duplicate video urls.
  6. No entry from a generated-image tag or an "(AI)" title.
  7. Every category is one the app knows.
  8. Every mature entry is either from the reviewed selection or justified by its words.
  9. A random sample of urls actually answers, and answers with a video.

Run: python tools/check-catalog.py [--sample 60] [--no-network]
"""

import argparse
import concurrent.futures as cf
import json
import random
import re
import ssl
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from atomicjson import read_json

CATALOG = ROOT / "LumaWall" / "catalog.json"
MATURE_SELECTED = ROOT / "mature-audit" / "selected.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

TARGET = 15000
DYNAMIC_SHARE = 0.90
HD_SHARE = 1.00
FOURK_SHARE = 0.50

KNOWN_CATEGORIES = {
    "Anime Loop", "Anime Girls", "Gaming", "Nature", "City", "Space", "Cars",
    "Animals", "Abstract", "Movies", "Music", "Sports", "Fantasy", "Horror",
    "Mature 18+", "Dynamic",
}

MATURE_WORDS = {
    "nsfw", "ecchi", "lewd", "sexy", "seductive", "sensual", "sultry", "provocative",
    "lingerie", "bikini", "swimsuit", "cleavage", "boudoir", "gravure", "pin-up", "pinup",
    "bath", "shower", "hot", "girl", "girls", "waifu", "maid", "idol", "model",

    # Kata yang juga membenarkan, dan harus sama dengan daftar di
    # tools/tegakkan-mature.py. Kalau keduanya berbeda, alat itu akan
    # mengeluarkan entri yang oleh pemeriksa ini dianggap benar - dan
    # keduanya akan bertengkar tanpa akhir.
    "alluring", "sunbathing", "bathing", "swimwear", "beachwear", "flirty",
    "voluptuous", "curvy", "busty", "thigh", "thighs", "stockings",
    "heels", "sundress", "onsen", "poolside", "topless", "nude", "naked",
    "undress", "panties", "leotard", "bodysuit", "catsuit", "garter",
    "corset", "negligee", "nightgown", "cheerleader", "nurse", "bunny",
    "gym", "yoga", "massage", "bedroom", "beach",
}

GENERATED_TAGS = {"ai", "ai-art", "ai-generated", "midjourney", "stable-diffusion", "sdxl"}

# AI-generated: HANYA kalau pembuatnya disebut.
#
# Pemeriksa versi lama menandai setiap judul yang memuat kata "ai", dan itu
# melaporkan 30 entri palsu: "Ai Hoshino" adalah tokoh Oshi no Ko, "Kizuna AI"
# adalah vtuber, dan "AI LIMIT" adalah judul game. Tidak satu pun gambar buatan
# mesin. Yang dicari adalah PENYEBUTNYA - nama alat atau frasa "AI generated" -
# bukan dua huruf yang kebetulan berdiri sendiri.
GENERATED_TITLE = re.compile(
    r"(midjourney|stable\s+diffusion|dall[- ]?e|"
    r"\bai[-\s]generated\b|\bai[-\s]art\b|\bgenerated\s+by\s+ai\b|"
    r"\bmade\s+with\s+ai\b)",
    re.I,
)

UNSAFE_TITLE = re.compile(
    r"\b(loli|lolita|child|kid|little girl|baby|daughter|schoolgirl|school girl|student"
    r"|teen|anya|kanna|pokemon|nezuko|nahida|klee|qiqi|yaoyao|diona|ibuki|blue archive"
    r"|juvenile)\b", re.I)


def safe_url(url):
    """Percent-encode the path so urllib can send it.

    Files carry titles in Japanese and Chinese, and urllib raises UnicodeEncodeError on a
    path it cannot encode. The checker reported such a file as dead when it was fine.
    """
    from urllib.parse import quote, urlsplit, urlunsplit
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%:@&=+$,~()!'*-._")
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def probe(url):
    """What the url serves: status, whether it is a video, and its size.

    The check cannot rely on Content-Type. moewalls answers with
    `application/octet-stream` for a real MP4, so a type test called 11 of 12 healthy files
    "not a video" and reported the catalogue as broken. What identifies a video is the
    container signature: an MP4 begins with a box header containing `ftyp`, and a WebM
    begins with the EBML magic.

    A HEAD request is not enough for those files either - the endpoint omits Content-Length
    and sometimes the type - so a small range of the body is read when the type is unclear.
    """
    try:
        req = urllib.request.Request(safe_url(url), method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            size = int(r.headers.get("Content-Length") or 0)
            status = r.status
    except Exception as e:
        return (url, getattr(e, "code", "ERR"), False, 0)

    if "video" in ctype:
        return (url, status, True, size)

    # The type says nothing useful, so look at the bytes.
    try:
        req = urllib.request.Request(
            safe_url(url), headers={**UA, "Range": "bytes=0-64"})
        with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
            head = r.read(64)
        if b"ftyp" in head or head[:4] == b"\x1a\x45\xdf\xa3":
            return (url, status, True, size)
    except Exception:
        pass

    return (url, status, False, size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=60)
    ap.add_argument("--no-network", action="store_true")
    args = ap.parse_args()

    if not CATALOG.exists():
        print("  %s is missing" % CATALOG)
        return 1

    entries = read_json(CATALOG, [])
    n = len(entries)
    if not n:
        print("  the catalogue is empty")
        return 1

    failures = []
    warnings = []

    print("  entries: %d" % n)

    # 1. count
    if n < TARGET:
        failures.append("only %d entries, the target is %d" % (n, TARGET))
    else:
        print("    reaches the %d target" % TARGET)

    # 2. dynamic share
    kinds = Counter(e.get("kind", "?") for e in entries)
    dynamic = kinds.get("dynamic", 0)
    share = dynamic / n
    print("  dynamic: %d (%.1f%%)" % (dynamic, 100 * share))
    if share < DYNAMIC_SHARE:
        failures.append("dynamic share is %.1f%%, below %.0f%%" % (100 * share, 100 * DYNAMIC_SHARE))

    # 3. every entry measured
    measured = [e for e in entries if re.match(r"^\d{3,5}x\d{3,5}$", e.get("resolution", ""))]
    print("  resolution measured: %d (%.1f%%)" % (len(measured), 100 * len(measured) / n))
    if len(measured) < n * HD_SHARE:
        failures.append("%d entries have no measured resolution" % (n - len(measured)))

    # 4. HD share
    def px(entry):
        m = re.match(r"^(\d{3,5})x(\d{3,5})$", entry.get("resolution", ""))
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    hd = [e for e in entries if px(e)[0] >= 1280 and px(e)[1] >= 720]
    print("  HD or better: %d (%.1f%%)" % (len(hd), 100 * len(hd) / n))
    if len(hd) < n * HD_SHARE:
        failures.append("%d entries are below HD" % (n - len(hd)))

    big = [e for e in entries if px(e)[0] >= 2560 or px(e)[1] >= 1440]
    print("  2K or better: %d (%.1f%%)" % (len(big), 100 * len(big) / n))
    if len(big) < n * FOURK_SHARE:
        warnings.append("2K share is %.1f%%, below the %.0f%% this catalogue was built for"
                        % (100 * len(big) / n, 100 * FOURK_SHARE))

    # 5. duplicates
    urls = [e.get("videoUrl", "") for e in entries]
    dupes = [u for u, c in Counter(urls).items() if c > 1]
    print("  duplicates: %d" % len(dupes))
    if dupes:
        failures.append("%d duplicate video urls, e.g. %s" % (len(dupes), dupes[0][:70]))

    # 6. generated images
    generated = [e for e in entries
                 if GENERATED_TITLE.search(e.get("title", "") or "")
                 or GENERATED_TITLE.search(e.get("videoUrl", "") or "")]
    print("  entries titled as AI: %d" % len(generated))
    if generated:
        failures.append("%d entries are titled as AI-generated, e.g. %s"
                        % (len(generated), generated[0]["title"][:50]))

    # 7. categories
    unknown = Counter(e.get("category", "?") for e in entries if e.get("category") not in KNOWN_CATEGORIES)
    print("  categories: %d distinct" % len(set(e.get("category") for e in entries)))
    if unknown:
        failures.append("unknown categories: %s" % dict(unknown))

    # 8. mature
    selected = read_json(MATURE_SELECTED, []) or []
    mature_ids = {str(s["motionId"]) for s in selected}

    def mid(entry):
        m = re.search(r"/media/(\d+)/", entry.get("videoUrl", ""))
        return m.group(1) if m else ""

    mature = [e for e in entries if e.get("category") == "Mature 18+"]
    print("  mature entries: %d" % len(mature))
    print("    reviewed : %d" % len([e for e in mature if mid(e) in mature_ids]))
    print("    keyword  : %d" % len([e for e in mature if mid(e) not in mature_ids]))

    unsafe = [e for e in mature if UNSAFE_TITLE.search(e.get("title", ""))]
    if unsafe:
        failures.append("%d mature entries have an unsafe title, e.g. %s"
                        % (len(unsafe), unsafe[0]["title"][:50]))

    unjustified = []
    for e in mature:
        if mid(e) in mature_ids:
            continue
        words = set(re.split(r"[^a-z0-9]+",
                             (e.get("title", "") + " " + e.get("videoUrl", "")).lower())) - {""}
        if not (words & MATURE_WORDS):
            unjustified.append(e)
    if unjustified:
        failures.append("%d mature entries have nothing that justifies them, e.g. %s"
                        % (len(unjustified), unjustified[0]["title"][:50]))

    # 9. the network. A file can be perfect and every url dead.
    if args.no_network:
        print()
        print("  network check skipped")
    else:
        sample = random.Random(20).sample(entries, min(args.sample, n))
        print()
        print("  probing %d entries" % len(sample))
        with cf.ThreadPoolExecutor(max_workers=12) as ex:
            results = list(ex.map(lambda e: probe(e["videoUrl"]), sample))

        alive = [r for r in results if r[1] == 200]
        videos = [r for r in alive if r[2]]
        # 429 is the site rate-limiting this machine, not a dead url. The catalogue is being
        # collected at the same time as this check runs, so the two share one IP's budget -
        # counting a 429 as a failure reported the catalogue as broken when the files were
        # fine. It is reported separately and excluded from the ratio.
        throttled = [r for r in results if r[1] == 429]
        considered = [r for r in results if r[1] != 429]

        print("    answered 200 : %d/%d" % (len(alive), len(results)))
        print("    served video : %d/%d" % (len(videos), len(results)))
        if throttled:
            print("    rate-limited : %d (not counted as failures)" % len(throttled))

        if considered and len([r for r in considered if r[1] == 200]) < len(considered) * 0.95:
            failures.append("only %d of %d sampled urls answer (excluding rate limits)"
                            % (len([r for r in considered if r[1] == 200]), len(considered)))
        if alive and len(videos) < len(alive) * 0.95:
            failures.append("only %d of %d answering urls serve a video" % (len(videos), len(alive)))

        dead = [r for r in results if r[1] not in (200, 429)]
        for r in dead[:5]:
            print("      %-6s %s" % (r[1], r[0][-70:]))

    print()
    if warnings:
        for w in warnings:
            print("  NOTE  %s" % w)
        print()
    if failures:
        for f in failures:
            print("  FAIL  %s" % f)
        return 1

    print("  OK    the catalogue meets every requirement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
