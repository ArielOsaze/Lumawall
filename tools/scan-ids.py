"""Find motionbgs media ids the sitemap does not list.

Why: the catalogue needs 15000 entries and the sitemap plus tag pages supply about 9700. The
download endpoint is addressable by id - /dl/hd/<id>/ - and probing shows live ids above the
highest one the sitemap mentions, so the site holds wallpapers its own index omits. Scanning
the id space finds them.

An id that answers is a wallpaper, but the metadata (title, tags, poster) lives on the detail
page, and the id alone does not give the slug. So this records the id and the file, and the
detail page is resolved separately by searching the site for the id.

Run: python tools/scan-ids.py --from 10120 --to 12000 [--workers 24]
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

OUT = ROOT / "build" / "catalog-scrape" / "id-scan.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def probe(mid):
    """True when the download endpoint serves a video for this id."""
    url = "https://motionbgs.com/dl/hd/%d/" % mid
    try:
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(req, timeout=12, context=CTX) as r:
            if r.status != 200:
                return None
            if "video" not in (r.headers.get("Content-Type") or "").lower():
                return None
            size = int(r.headers.get("Content-Length") or 0)
            if size < 100_000:
                return None
            return {"id": mid, "size": size, "download": url}
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", type=int, required=True)
    ap.add_argument("--to", dest="end", type=int, required=True)
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()

    state = read_json(OUT, {"checked": [], "live": []})
    checked = set(state.get("checked", []))
    live = {item["id"]: item for item in state.get("live", [])}

    ids = [i for i in range(args.start, args.end + 1) if i not in checked]
    print("  range      : %d..%d" % (args.start, args.end))
    print("  already    : %d checked, %d live" % (len(checked), len(live)))
    print("  this run   : %d ids" % len(ids))
    print()

    if not ids:
        print("  nothing to do")
        return 0

    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        # zip with the ids so a failed probe is still recorded as checked. Without that, a
        # resumed run asks the site about every dead id again - the first version of this
        # recorded 60 checked out of 481 and would have repeated 421 requests.
        for mid, result in zip(ids, ex.map(probe, ids)):
            done += 1
            checked.add(mid)
            if result:
                live[result["id"]] = result
            if done % 200 == 0:
                state = {"checked": sorted(checked),
                         "live": sorted(live.values(), key=lambda i: i["id"])}
                write_json(OUT, state)
                print("    %d/%d, %d live" % (done, len(ids), len(live)))

    state = {"checked": sorted(checked),
             "live": sorted(live.values(), key=lambda i: i["id"])}
    write_json(OUT, state)

    print()
    print("  checked: %d" % len(checked))
    print("  live   : %d" % len(live))
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
