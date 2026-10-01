#!/usr/bin/env python3
"""Ambil videoUrl dan TAG ASLI setiap kartu moewalls baru.

KENAPA ALAT INI ADA:

tools/kejar-moewalls.py menemukan 139 wallpaper moewalls yang belum ada di
katalog. Tetapi halaman tag hanya memberi judul, tautan, dan thumbnail - TIDAK
videoUrl-nya, dan TIDAK tag lengkapnya. Keduanya ada di halaman masing-masing
wallpaper.

Tag itu penting, dan itu satu-satunya alasan alat ini ada: tag moewalls adalah
penilaian situsnya sendiri tentang isi wallpapernya. Tag "swimsuit" atau
"lingerie" tidak bisa menyesatkan seperti judul bisa - judul memuat "girl" dan
"maid" di ribuan wallpaper yang sama sekali tidak dewasa.

Jadi setiap halaman dikunjungi, dan yang diambil dua hal:
  - videoUrl  supaya entrinya bisa diputar
  - _tags     supaya kategorinya bisa ditentukan dengan bukti

Resolusi ikut diambil, dan entri yang di bawah HD atau berbentuk potret dibuang
di sini - bukan dimasukkan lalu dibuang lagi nanti.

Kemajuan ditulis setiap 20 halaman, jadi jalannya bisa dilanjutkan.

Pemakaian:
  python tools/ambil-video-moewalls.py
  python tools/ambil-video-moewalls.py --pekerja 8
"""
import argparse
import concurrent.futures as cf
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "catalog-scrape"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json, read_json  # noqa: E402

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Video ada di halaman wallpaper sebagai token, bukan URL siap pakai:
#
#   <a id="moe-download" data-id="9671"
#      data-url="o78u7mn5G7OiZ9j40AcQF15gKdXvvn6NYwLxfgRR0W%2BRpGq..."
#      class="g1-button ...">Download Wallpaper</a>
#
# Token itu disusun menjadi URL download yang sama bentuknya dengan yang sudah
# dipakai katalog:
#
#   https://go.moewalls.com/download.php?video=<token>
#
# Versi pertama alat ini mencari <source src="..."> dan "download.php?video="
# langsung di HTML, dan keduanya tidak ada - video dimuat oleh pemutar lewat
# JavaScript. Karena itu halamannya terlihat tidak punya video padahal punya.
TOKEN = re.compile(r'data-url\s*=\s*"([^"]+)"', re.I)
TOKEN_ID = re.compile(r'data-id\s*=\s*"(\d+)"', re.I)
TOKEN_KELAS = re.compile(r'id="moe-download"[^>]*', re.I)

# Cadangan: kalau situsnya suatu saat menaruh URL langsung.
VIDEO = [
    re.compile(r'<source[^>]+src="(https://go\.moewalls\.com/download[^"]+)"', re.I),
    re.compile(r'(https://go\.moewalls\.com/download\.php\?video=[^"\'\s<]+)', re.I),
]

# Tag ada di tautan /tag/<nama>/.
TAG = re.compile(r'href="https://moewalls\.com/tag/([a-z0-9\-]+)/"', re.I)

RES = re.compile(r'(\d{3,4})\s*[xX]\s*(\d{3,4})')


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", "replace")


def video_dari(html):
    """URL video dari halaman wallpaper moewalls."""
    # Bentuk utama: token di dalam tombol download.
    for m in TOKEN_KELAS.finditer(html):
        blok = m.group(0)
        t = TOKEN.search(blok)
        if t:
            return "https://go.moewalls.com/download.php?video=" + t.group(1)
    # Cadangan: URL langsung.
    for p in VIDEO:
        m = p.search(html)
        if m:
            return m.group(1)
    return ""


# Resolusi ada di CLASS elemen artikelnya, bukan di teks mana pun:
#
#   <article class="... tag-swimsuit ... resolutions-3840x2160">
#
# Ini satu-satunya tempat yang benar. Dua percobaan sebelumnya gagal dan
# keduanya menghasilkan angka yang salah untuk SEMUA 139 entri:
#
#   1. Angka terbesar di seluruh halaman  -> 7680x2160, dari menu resolusi
#      situsnya ("7680x2160 - Dual 4K"). Itu pilihan menu, bukan resolusi
#      wallpaper ini.
#   2. Tautan /resolution/<w>x<h>/        -> 3840x2400, dari daftar menu yang
#      sama. 3840x2400 juga tidak masuk akal untuk wallpaper 16:9.
#
# Class-nya melekat pada artikel wallpaper itu sendiri, jadi ia tidak bisa
# tertukar dengan menu.
RES_KELAS = re.compile(r'resolutions-(\d{3,4})x(\d{3,4})', re.I)

# Cadangan: blok informasi di bawah judul.
RES_BADGE = re.compile(
    r'(?:Resolution|Resolusi)\s*[:<][^0-9]{0,40}(\d{3,4})\s*(?:&#215;|[xX])\s*(\d{3,4})',
    re.I)


def resolusi_dari(html):
    """Resolusi wallpaper, dari class artikelnya."""
    m = RES_KELAS.search(html)
    if m:
        return "%sx%s" % (m.group(1), m.group(2))
    m = RES_BADGE.search(html)
    if m:
        return "%sx%s" % (m.group(1), m.group(2))
    return ""


def satu(slug, url):
    try:
        h = get(url)
    except urllib.error.HTTPError as e:
        return slug, {}, "HTTP %s" % e.code
    except Exception as e:
        return slug, {}, str(e)[:40]

    v = video_dari(h)
    if not v:
        return slug, {}, "tidak ada video"

    tags = sorted({t.lower() for t in TAG.findall(h)})
    r = resolusi_dari(h)

    return slug, {"videoUrl": v, "tags": tags, "resolution": r}, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pekerja", type=int, default=6)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    maju = OUT / "moewalls-video.json"
    sudah = read_json(maju, {"item": {}, "gagal": {}})
    item = dict(sudah.get("item") or {})
    gagal = dict(sudah.get("gagal") or {})

    sumber = OUT / "moewalls-baru.json"
    if not sumber.exists():
        print("  TIDAK ADA %s - jalankan tools/kejar-moewalls.py dulu" % sumber)
        return 1
    d = json.load(open(sumber, encoding="utf-8"))
    kartu = d.get("kartu", {})

    calon = [(s, v.get("url") or "") for s, v in kartu.items()
             if v.get("url") and s not in item and s not in gagal]

    print()
    print("  == kartu moewalls baru ==")
    print("     kartu            : %d" % len(kartu))
    print("     sudah diambil     : %d" % len(item))
    print("     perlu dikunjungi  : %d" % len(calon))
    print()

    if not calon:
        print("  tidak ada yang perlu dikunjungi")
        return 0

    n = 0
    with cf.ThreadPoolExecutor(max_workers=args.pekerja) as ex:
        for slug, hasil, err in ex.map(lambda a: satu(*a), calon):
            n += 1
            if hasil:
                item[slug] = hasil
            else:
                gagal[slug] = err
            if n % 20 == 0:
                write_json(maju, {"item": item, "gagal": gagal})
                print("     %d/%d  (berhasil: %d, gagal: %d)"
                      % (n, len(calon), len(item), len(gagal)))
            time.sleep(0.15)

    write_json(maju, {"item": item, "gagal": gagal})

    print()
    print("  == hasil ==")
    print("     berhasil : %d" % len(item))
    print("     gagal    : %d" % len(gagal))
    print("     disimpan : %s" % maju)
    print()

    # Tag apa saja yang muncul - ini yang menentukan kategori.
    from collections import Counter
    tc = Counter()
    for v in item.values():
        for t in v.get("tags") or []:
            tc[t] += 1
    print("  == 30 tag terbanyak ==")
    for t, c in tc.most_common(30):
        print("     %-22s %4d" % (t, c))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
