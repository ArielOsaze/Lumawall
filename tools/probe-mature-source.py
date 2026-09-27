"""Probe a candidate site for mature (18+) wallpapers with real HD videos.

Why: the catalogue must carry more 18+ entries and their categories must be right, and
motionbgs has no adult section at all - its tag list has no nsfw, ecchi or adult tag. So the
adult part of the catalogue needs a different source, and that source has to be checked for
three things before anything is taken from it: an adult section that actually exists, HD
video files, and a licence that permits free personal use.

Run: python tools/probe-mature-source.py <host>
"""

import re
import ssl
import sys
import urllib.error
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get(url, method="GET", timeout=25):
    req = urllib.request.Request(url, method=method, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        body = r.read()
        try:
            text = body.decode("utf-8", "replace")
        except Exception:
            text = ""
        return text, r.status, dict(r.headers), len(body)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "desktophut.com"
    base = "https://" + host

    print("  host: %s" % host)
    print()

    # 1. robots.txt - what is the site's own policy on crawling?
    try:
        text, _, _, _ = get(base + "/robots.txt")
        print("  robots.txt:")
        for line in text.splitlines()[:20]:
            if line.strip():
                print("    %s" % line.strip()[:110])
    except Exception as e:
        print("  robots.txt: %s" % getattr(e, "code", type(e).__name__))
    print()

    # 2. The adult section.
    candidates = [
        "/search/Adult", "/adult", "/nsfw", "/18", "/category/adult",
        "/search/adult", "/tag/nsfw", "/mature",
    ]
    found = []
    for path in candidates:
        try:
            text, status, _, size = get(base + path)
            videos = re.findall(r'https?://[^"\'\s<>]+\.(?:mp4|webm)', text)
            hd = [v for v in videos if re.search(r"(1080|2160|1440|4k)", v, re.I)]
            print("  %-20s %s  %6d bytes  %3d video (%d HD)"
                  % (path, status, size, len(videos), len(hd)))
            if videos:
                found.append((path, text, videos, hd))
        except Exception as e:
            print("  %-20s %s" % (path, getattr(e, "code", type(e).__name__)))
    print()

    if not found:
        print("  no video URLs on any candidate path")
        return 1

    # 3. How does a detail page expose its video, and is there an HD variant?
    path, text, videos, hd = found[0]
    print("  detail pages linked from %s:" % path)
    links = sorted(set(re.findall(r'href="(/(?:wallpaper|video|live-wallpaper|download)/[^"?#]+)"', text)))
    if not links:
        links = sorted(set(re.findall(r'href="(/[a-z0-9\-]+/[a-z0-9\-]+/?)"', text)))
    for link in links[:6]:
        print("    %s" % link[:100])
    print()

    if links:
        detail = base + links[0]
        try:
            html, status, _, size = get(detail)
            print("  sample detail: %s (%d bytes)" % (detail, size))
            patterns = {
                "mp4/webm": r'https?://[^"\'\s<>]+\.(?:mp4|webm)',
                "og:video": r'property="og:video[^"]*"\s+content="([^"]+)"',
                "1080/4k": r'(\d{3,4}x\d{3,4}|1080p|2160p|4K)',
                "license": r"(CC0|CC-BY|Creative Commons|royalty[- ]free|personal use)",
            }
            for name, pat in patterns.items():
                hits = re.findall(pat, html, re.I)
                if hits:
                    print("    %-10s %d: %s" % (name, len(hits), ", ".join(str(h) for h in hits[:4])[:110]))
        except Exception as e:
            print("    detail failed: %s" % getattr(e, "code", type(e).__name__))

    return 0


if __name__ == "__main__":
    sys.exit(main())
