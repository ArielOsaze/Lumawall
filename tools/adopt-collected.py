"""Adopt the subagent's collected entries, but measure every file instead of trusting it.

Why this is not a copy: the collection recorded `w` and `h` from what each page said. A
sample of 30 files showed only 1 claim out of 10 exact, and the differences were not
rounding - a file claiming 3840x2160 was really 1280x720, and several claiming 1920x1080 were
really 1280x720. A catalogue built on those numbers would be a catalogue of files that look
broken on a 1080p desktop, which is the "pecah" this whole exercise is against.

So every file is measured with ffprobe before it is adopted, and the entry keeps the measured
size. Anything that cannot be measured is dropped rather than assumed: an unmeasurable file
is one whose resolution is unknown, and unknown is not good enough.

Portrait files and stock footage are dropped here too, for the same reasons the collector
drops them.

Run: python tools/adopt-collected.py [--workers 12]
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
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from atomicjson import write_json

SOURCE = ROOT / "build" / "collect" / "desktophut.jsonl"
OUT = ROOT / "build" / "catalog-desktophut" / "adopted.json"
PROGRESS = ROOT / "build" / "catalog-desktophut" / "adopt-progress.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

FFPROBE = shutil.which("ffprobe") or shutil.which("ffprobe.exe")

STOCK = re.compile(
    r"stock-video|free-stock|stock-footage|video-stock|-stock-|footage|free-video"
    r"|stock-clip|royalty-free|business-people|office-worker", re.I)


def safe_url(url):
    """Percent-encode the path so urllib can send it.

    The site's files carry titles in Japanese and Chinese, so a url can contain characters
    that urllib refuses to encode: it raised UnicodeEncodeError on every such file, and a
    third of the collection was recorded as "unmeasurable" when the files were perfectly
    fine. Only the path is re-encoded - the query and fragment are left alone.
    """
    from urllib.parse import quote, urlsplit, urlunsplit

    parts = urlsplit(url)
    path = quote(parts.path, safe="/%:@&=+$,~()!'*-._")
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


def measure(url, attempts=4):
    """The video's real size, read from the file's own MP4 header.

    The header is at the start when the file was written for streaming and at the end
    otherwise, so both ends are tried.

    A 429 is retried with a growing pause. The site rate-limits by IP and a collection run
    asks for thousands of files, so a 429 means "ask again later" - treating it as a missing
    file threw away entries whose files are fine. The pauses are 2, 6 and 14 seconds.
    """
    if not FFPROBE:
        return None

    url = safe_url(url)
    tmp = Path(tempfile.gettempdir()) / ("ad-%d.mp4" % abs(hash(url)))

    for attempt in range(attempts):
        try:
            found = _measure_once(url, tmp)
            if found:
                return found
            # A read that produced no header is worth one more try only if the file was not
            # served at all; otherwise the file genuinely has no video stream.
            return None
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < attempts - 1:
                time.sleep(2 ** (attempt + 1) + 2)
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


def _measure_once(url, tmp):
    def size_of(path):
        result = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=45)
        for line in (result.stdout or "").strip().splitlines():
            if "," in line:
                w, h = line.split(",")[:2]
                try:
                    return int(w), int(h)
                except ValueError:
                    continue
        return None

    req = urllib.request.Request(url, headers={**UA, "Range": "bytes=0-1500000"})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        tmp.write_bytes(r.read())
    found = size_of(tmp)
    if found:
        return found

    total = 0
    try:
        probe = urllib.request.Request(url, method="HEAD", headers=UA)
        with urllib.request.urlopen(probe, timeout=20, context=CTX) as r:
            total = int(r.headers.get("Content-Length") or 0)
    except Exception:
        pass

    if total > 1500000:
        start = max(0, total - 1500000)
        req = urllib.request.Request(
            url, headers={**UA, "Range": "bytes=%d-%d" % (start, total - 1)})
        with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
            tmp.write_bytes(r.read())
        return size_of(tmp)

    return None


def load_source():
    items = []
    for line in SOURCE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            pass
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    if not SOURCE.exists():
        print("  %s is missing" % SOURCE)
        return 1
    if not FFPROBE:
        print("  ffprobe was not found, so nothing can be measured")
        return 1

    raw = load_source()
    print("  source entries: %d" % len(raw))

    # Filter before measuring, so the expensive step runs on candidates only.
    candidates = []
    stats = Counter()
    for item in raw:
        url = item.get("file") or ""
        if not url.endswith(".mp4"):
            stats["no-file"] += 1
            continue
        if STOCK.search(url) or STOCK.search(item.get("title", "")):
            stats["stock-footage"] += 1
            continue
        w, h = item.get("w") or 0, item.get("h") or 0
        # The claim is only used to skip obvious portrait entries; the real check is after
        # measuring.
        if w and h and w <= h:
            stats["portrait"] += 1
            continue
        candidates.append(item)

    print("  candidates    : %d" % len(candidates))
    for reason, n in stats.most_common():
        print("    skipped %-14s %d" % (reason, n))
    print()

    # Resume: skip files already measured on a previous run.
    done = {}
    if PROGRESS.exists():
        try:
            done = json.loads(PROGRESS.read_text(encoding="utf-8"))
            print("  resuming with %d already measured" % len(done))
        except Exception:
            done = {}

    todo = [c for c in candidates if c["file"] not in done]
    print("  to measure    : %d" % len(todo))
    print()

    processed = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(measure, c["file"]): c for c in todo}
        for future in cf.as_completed(futures):
            item = futures[future]
            try:
                size = future.result()
            except Exception:
                size = None
            done[item["file"]] = list(size) if size else None
            processed += 1
            if processed % 100 == 0:
                write_json(PROGRESS, done)
                measured = sum(1 for v in done.values() if v)
                print("    %d/%d measured, %d readable" % (processed, len(todo), measured))

    write_json(PROGRESS, done)

    # Build the adopted entries from the measurements.
    entries = []
    reasons = Counter()
    for item in candidates:
        size = done.get(item["file"])
        if not size:
            reasons["unmeasurable"] += 1
            continue
        w, h = size
        if w < 1280 or h < 720:
            reasons["below-hd"] += 1
            continue
        if w <= h:
            reasons["portrait"] += 1
            continue

        entries.append({
            "title": item.get("title", "").strip() or "Untitled",
            "videoUrl": item["file"],
            "thumbnailUrl": item.get("thumb", ""),
            "license": "DesktopHut · CC0",
            "sourceUrl": item.get("url", ""),
            "category": "",              # assigned by tools/recategorise.py
            "kind": "dynamic",
            "author": "DesktopHut community",
            "animation": "",
            "resolution": "%dx%d" % (w, h),
        })

    write_json(OUT, entries)

    print()
    print("  measured      : %d of %d" % (sum(1 for v in done.values() if v), len(done)))
    print("  adopted       : %d" % len(entries))
    for reason, n in reasons.most_common():
        print("    dropped %-14s %d" % (reason, n))
    print()

    res = Counter(e["resolution"] for e in entries)
    print("  resolution of the adopted entries:")
    for k, n in res.most_common(8):
        print("    %-12s %5d  %4.1f%%" % (k, n, 100 * n / len(entries)))
    big = sum(n for k, n in res.items() if int(k.split("x")[0]) >= 2560)
    print()
    print("  2K or better: %d (%.1f%%)" % (big, 100 * big / len(entries)))
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
