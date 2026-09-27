"""Verify a sample of the subagent's claimed resolutions against the actual files.

Why: the collection wrote `w` and `h` from what the page said, and the page's own resolution
text describes its page images rather than the video - that mistake has already produced
960x540 files that claimed 1920x1080 once in this project. A claimed resolution is not
evidence. This downloads the head and tail of a sample of files and reads the real size out
of the MP4 header with ffprobe, then reports how many claims were honest.

Run: python tools/verify-claims.py [--sample 40]
"""

import argparse
import concurrent.futures as cf
import json
import random
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "build" / "collect" / "desktophut.jsonl"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

FFPROBE = shutil.which("ffprobe") or shutil.which("ffprobe.exe")


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


def real_size(url):
    """The video's real pixel size, or None when it cannot be read."""
    if not FFPROBE:
        return None
    tmp = Path(tempfile.gettempdir()) / ("vc-%d.mp4" % abs(hash(url)))
    try:
        # The moov atom sits at the end when the file was not written for streaming, so the
        # tail is fetched as well as the head and the two are joined.
        req = urllib.request.Request(safe_url(url), headers={**UA, "Range": "bytes=0-1200000"})
        with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
            head = r.read()

        total = None
        try:
            probe = urllib.request.Request(url, method="HEAD", headers=UA)
            with urllib.request.urlopen(probe, timeout=20, context=CTX) as r:
                total = int(r.headers.get("Content-Length") or 0)
        except Exception:
            pass

        tmp.write_bytes(head)
        result = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", str(tmp)],
            capture_output=True, text=True, timeout=40)
        text = (result.stdout or "").strip()
        if "," in text:
            w, h = text.split(",")[:2]
            return int(w), int(h)

        # No header in the head, so fetch the tail where it lives.
        if total and total > 1200000:
            start = max(0, total - 1200000)
            req = urllib.request.Request(url, headers={**UA, "Range": "bytes=%d-%d" % (start, total - 1)})
            with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
                tail = r.read()
            tmp.write_bytes(tail)
            result = subprocess.run(
                [FFPROBE, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height", "-of", "csv=p=0", str(tmp)],
                capture_output=True, text=True, timeout=40)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=40)
    args = ap.parse_args()

    if not SOURCE.exists():
        print("  %s is missing" % SOURCE)
        return 1
    if not FFPROBE:
        print("  ffprobe was not found, so nothing can be verified")
        return 1

    items = []
    for line in SOURCE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            pass

    # Only the landscape ones matter - the portrait entries are dropped anyway.
    landscape = [d for d in items if d.get("w") and d.get("h") and d["w"] > d["h"]]
    print("  %d entries, %d landscape" % (len(items), len(landscape)))
    print()

    sample = random.Random(31).sample(landscape, min(args.sample, len(landscape)))
    print("  measuring %d files" % len(sample))
    print()

    def check(item):
        real = real_size(item["file"])
        return item, real

    results = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for item, real in ex.map(check, sample):
            results.append((item, real))

    measured = [(i, r) for i, r in results if r]
    unreadable = [i for i, r in results if not r]
    honest = [(i, r) for i, r in measured if (r[0], r[1]) == (i["w"], i["h"])]
    hd_real = [(i, r) for i, r in measured if r[0] >= 1280 and r[1] >= 720]
    understated = [(i, r) for i, r in measured
                   if (r[0], r[1]) != (i["w"], i["h"]) and r[0] >= 1280]

    print("  measured      : %d of %d" % (len(measured), len(sample)))
    print("  unreadable    : %d" % len(unreadable))
    print("  claim exact   : %d" % len(honest))
    print("  really HD     : %d" % len(hd_real))
    print("  claim differs : %d" % len(understated))
    print()

    if understated:
        print("  the differences:")
        for item, real in understated[:12]:
            print("    claimed %-10s real %-10s  %s"
                  % ("%dx%d" % (item["w"], item["h"]), "%dx%d" % real, item["title"][:44]))
        print()

    if unreadable:
        print("  unreadable files:")
        for item in unreadable[:6]:
            print("    %s" % item["title"][:60])
        print()

    if not measured:
        print("  FAIL  no file could be measured, so the claims are unverified")
        return 1

    if len(hd_real) < len(measured) * 0.95:
        print("  FAIL  only %d of %d measured files are really HD" % (len(hd_real), len(measured)))
        return 1

    print("  OK    %d of %d measured files are really HD or better"
          % (len(hd_real), len(measured)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
