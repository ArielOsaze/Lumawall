"""Upgrade catalogue entries to the highest real resolution the source offers.

Why: the detail page links a 960x540 file and the site's own poster is 3840x2160, so the
resolution a page advertises says nothing about the file it links. Probing shows the same
path also serves 1920x1080 and, for many items, 3840x2160. An entry that keeps the linked
file is an SD file stretched across a desktop - the "pecah" the catalogue must not have -
so every entry is offered the better variants and keeps the best one that exists.

Each entry records the resolution it ended up with, so the catalogue can be checked instead
of trusted.

Run: python tools/upgrade-resolution.py [--workers N] [--limit N]
"""

import argparse
import concurrent.futures as cf
import json
import re
import ssl
import sys
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json, read_json

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "build" / "catalog-scrape" / "done.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Best first. 2560x1440 is included because the site serves it for some items, and a
# catalogue that skipped it would downgrade those to 1080p.
LADDER = ["3840x2160", "2560x1440", "1920x1080"]


def head_size(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
            if r.status != 200:
                return 0
            if "video" not in (r.headers.get("Content-Type") or "").lower():
                return 0
            return int(r.headers.get("Content-Length") or 0)
    except Exception:
        return 0


def variants(url):
    """The same file at each rung of the ladder, best first."""
    m = re.match(r"^(https?://[^/]+/media/\d+/[^/]+?)\.\d{3,4}x\d{3,4}\.(mp4|webm)$", url)
    if not m:
        return []
    stem, ext = m.group(1), m.group(2)
    return ["%s.%s.%s" % (stem, res, ext) for res in LADDER]


def upgrade(item):
    url = item.get("videoUrl", "")
    if not url.startswith("http"):
        item["resolution"] = "local"
        return item

    for candidate in variants(url):
        size = head_size(candidate)
        if size >= 100_000:
            item["videoUrl"] = candidate
            item["resolution"] = re.search(r"\.(\d{3,4}x\d{3,4})\.", candidate).group(1)
            item["_bytes"] = size
            return item

    # Nothing on the ladder answered, so keep what was there and say so rather than
    # claiming a resolution that was never confirmed.
    m = re.search(r"\.(\d{3,4}x\d{3,4})\.", url)
    item["resolution"] = m.group(1) if m else "unknown"
    return item


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if not STATE.exists():
        print("  %s is missing - run tools/collect-motionbgs.py first" % STATE)
        return 1

    state = json.loads(STATE.read_text(encoding="utf-8"))
    items = state["items"]
    if args.limit:
        items = items[:args.limit]

    # Only entries that have not been measured yet. The first run of this script measured
    # all 9704 entries and then lost every result, because it wrote once at the end and the
    # process was cut off before that. Resuming is the difference between losing a few
    # minutes and losing the whole run, so the progress is kept in the file itself.
    todo = [i for i in items if not i.get("resolution")]
    print("  %d entries, %d already measured, %d to measure"
          % (len(items), len(items) - len(todo), len(todo)))
    print()

    if not todo:
        report(items)
        return 0

    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(upgrade, item): item for item in todo}
        for future in cf.as_completed(futures):
            future.result()
            done += 1
            if done % 200 == 0:
                print("    %d/%d" % (done, len(todo)))
                if args.limit:
                    state["items"][:args.limit] = items
                else:
                    state["items"] = items
                write_json(STATE, state)

    if args.limit:
        state["items"][:args.limit] = items
    else:
        state["items"] = items
    write_json(STATE, state)

    print()
    report(items)
    return 0


def report(items):
    counts = Counter(i.get("resolution", "?") for i in items)
    print("  resolution of the catalogue:")
    for res, n in counts.most_common():
        print("    %-12s %5d  %5.1f%%" % (res, n, 100 * n / len(items)))

    hd = sum(n for res, n in counts.items() if res in ("1920x1080", "2560x1440", "3840x2160"))
    print()
    print("  HD or better: %d of %d (%.1f%%)" % (hd, len(items), 100 * hd / len(items)))


if __name__ == "__main__":
    sys.exit(main())
