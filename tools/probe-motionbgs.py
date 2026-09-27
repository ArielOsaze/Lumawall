"""Probe how motionbgs.com serves a wallpaper, and at what resolution.

Why: the catalogue has to be HD - a 960x540 file stretched to a 1920x1080 desktop is the
"pecah" the catalogue must not have. The detail page mentions 1920x1080 in its markup but
links a 960x540 file, so the HD variant has to be found rather than assumed.

Run: python tools/probe-motionbgs.py [slug]
"""

import re
import ssl
import sys
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get(url, method="GET"):
    req = urllib.request.Request(url, method=method, headers=UA)
    with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
        return r.read().decode("utf-8", "replace"), r.status, dict(r.headers)


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else "green-grass"
    url = "https://motionbgs.com/" + slug
    html, _, _ = get(url)
    print("  page: %s  (%d bytes)" % (url, len(html)))
    print()

    # Every media URL the page mentions.
    media = re.findall(r'https?://motionbgs\.com/media/[^"\'\s\\<>]+', html)
    print("  media URLs mentioned (%d unique):" % len(set(media)))
    for u in sorted(set(media)):
        print("    %s" % u[:120])
    print()

    # How the page names a resolution. The suffix on the file is the reliable one.
    suffixed = re.findall(r"\.(\d{3,4}x\d{3,4})\.(?:mp4|webm)", html)
    print("  resolution suffixes seen: %s" % (sorted(set(suffixed)) or "none"))
    print()

    # The JSON blob the player reads.
    for key in ("videoUrl", "video", "url", "src", "poster", "thumbnail"):
        for match in re.finditer(r'"%s"\s*:\s*"([^"]+)"' % key, html):
            value = match.group(1)
            print("  %-10s %s" % (key, value[:110]))
    print()

    # Does a higher-resolution variant exist for this slug?
    #
    # The base must come from the mp4 URL, not the poster jpg - the jpg is always 1920x1080
    # while the video may not be, and using the jpg as the stem made every probe 404.
    mp4 = re.search(r"https?://motionbgs\.com/media/\d+/[^\"'\s\\<>]+\.\d{3,4}x\d{3,4}\.mp4", html)
    if mp4:
        stem = re.sub(r"\.\d{3,4}x\d{3,4}\.mp4$", "", mp4.group(0))
        print("  base: %s" % stem)
        print()
        print("  probing variants:")
        for variant in ["1920x1080", "2560x1440", "3840x2160", "1280x720", "960x540"]:
            for ext in ("mp4", "webm"):
                candidate = "%s.%s.%s" % (stem, variant, ext)
                try:
                    _, status, headers = get(candidate, "HEAD")
                    size = int(headers.get("Content-Length") or 0)
                    print("    %-9s %-4s  %s  %.1f MB" % (variant, ext, status, size / 1048576))
                except Exception as e:
                    code = getattr(e, "code", type(e).__name__)
                    print("    %-9s %-4s  %s" % (variant, ext, code))
    else:
        print("  no resolution-suffixed mp4 URL found on the page")


if __name__ == "__main__":
    main()
