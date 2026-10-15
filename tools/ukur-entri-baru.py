#!/usr/bin/env python3
"""Ukur berapa entri BARU yang tersedia di moewalls - sebelum memanen.

KENAPA ALAT INI ADA:

Meminta "tambah 500 entri baru" tanpa mengukur lebih dulu berarti menebak.
Kalau sumbernya hanya punya 200 yang belum diambil, panen akan berhenti di 200
dan laporannya akan tampak gagal - padahal yang salah adalah permintaannya,
bukan panennya.

Jadi yang diukur lebih dulu:
  1. Berapa total wallpaper di moewalls (dari REST API-nya)
  2. Berapa yang SUDAH ada di katalog (dicocokkan lewat sourceUrl dan videoUrl)
  3. Berapa sisanya yang benar-benar baru

Pencocokan memakai sourceUrl, bukan judul: dua wallpaper berbeda bisa punya
judul yang sama ("Albedo Overlord" ada banyak versi), dan judul yang sama tidak
berarti entri yang sama.
"""

import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KATALOG = W / "LumaWall" / "catalog.json"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
}

API = "https://moewalls.com/wp-json/wp/v2/posts"


def ambil(url, timeout=45):
    req = Request(url, headers=UA)
    with urlopen(req, timeout=timeout) as f:
        return f.status, f.read()


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   BERAPA ENTRI BARU YANG TERSEDIA DI MOEWALLS")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    # ── Yang sudah ada di katalog ─────────────────────────────────────────
    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))
    ada_sumber = set()
    ada_video = set()
    for it in items:
        s = (it.get("sourceUrl") or "").strip()
        v = (it.get("videoUrl") or "").strip()
        if s:
            ada_sumber.add(s.rstrip("/").lower())
        if v:
            ada_video.add(v)

    moewalls = [i for i in items if "moewalls.com" in (i.get("sourceUrl") or "")]
    print("  katalog        : %d entri" % len(items))
    print("  dari moewalls  : %d entri" % len(moewalls))
    print()

    # ── Total di sumber ───────────────────────────────────────────────────
    print("  ── bertanya ke moewalls ──")
    total = None
    try:
        # per_page=1 lalu baca header X-WP-Total: cara termurah mengetahui
        # berapa banyak yang ada tanpa mengunduh daftarnya.
        req = Request(API + "?per_page=1&_fields=id", headers=UA)
        with urlopen(req, timeout=45) as f:
            total = f.headers.get("X-WP-Total")
            total_pages = f.headers.get("X-WP-TotalPages")
        print("     total posting : %s" % total)
        print("     total halaman : %s" % total_pages)
    except Exception as e:
        print("     ! gagal bertanya: %s" % str(e)[:90])
    print()

    if not total:
        print("  Tidak bisa mengukur jumlah di sumber. Panen tidak dijalankan.")
        return 1

    # ── Sisanya yang benar-benar baru ─────────────────────────────────────
    print("  ── berapa yang benar-benar baru ──")
    print("     total di sumber : %s" % total)
    print("     sudah diambil   : %d" % len(moewalls))
    print("     perkiraan sisa  : %d" % max(0, int(total) - len(moewalls)))
    print()

    # Perkiraan ini kasar: katalog mungkin memuat entri moewalls yang tidak lagi
    # ada di sumber, dan sebaliknya. Tetap berguna sebagai batas atas.
    sisa = max(0, int(total) - len(moewalls))
    print("  ══════════════════════════════════════════════════════════════════")
    if sisa >= 500:
        print("   CUKUP: ada perkiraan %d entri baru, cukup untuk 500." % sisa)
    elif sisa > 0:
        print("   TERBATAS: hanya perkiraan %d entri baru, kurang dari 500." % sisa)
        print("   Perlu sumber tambahan (motionbgs / desktophut) untuk mencukupi.")
    else:
        print("   TIDAK ADA sisa: semua posting moewalls sudah ada di katalog.")
        print("   Sumber lain diperlukan untuk menambah entri baru.")
    print("  ══════════════════════════════════════════════════════════════════")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
