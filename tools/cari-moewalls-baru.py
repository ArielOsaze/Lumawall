#!/usr/bin/env python3
"""Cari entri moewalls yang BELUM ada di katalog.

KENAPA ALAT INI ADA:

Meminta "tambah 500 entri baru" berarti harus tahu lebih dulu mana yang baru.
Menebak dari halaman kategori tidak cukup: halaman pertama bisa saja seluruhnya
sudah ada di katalog, sehingga panen berjalan lama tanpa menambah apa pun.

Alat ini menjawab pertanyaan itu dengan bukti:
  1. Ambil daftar tautan wallpaper dari halaman kategori moewalls
  2. Bandingkan dengan sourceUrl yang sudah ada di katalog
  3. Laporkan berapa yang benar-benar baru, dan tunjukkan contohnya

Kalau hasilnya nol di halaman-halaman awal, berarti moewalls sudah tersedot
habis dan sumber lain diperlukan - dan itu lebih baik diketahui sekarang
daripada setelah satu jam memanen.
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KATALOG = W / "LumaWall" / "catalog.json"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Kategori moewalls yang terbuka (sitemap diblokir 403, halaman kategori tidak).
KATEGORI = ["anime", "games", "movies", "nature", "cars", "superheroes", "sports", "tv-shows"]

POLA_TAUTAN = re.compile(r'https://moewalls\.com/([a-z0-9\-]+)/([a-z0-9\-]+-live-wallpaper)/')


def get(url, timeout=30):
    req = Request(url, headers=UA)
    with urlopen(req, timeout=timeout) as f:
        return f.read().decode("utf-8", "replace")


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   ENTRI MOEWALLS YANG BELUM ADA DI KATALOG")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))
    ada = set()
    for it in items:
        s = (it.get("sourceUrl") or "").strip().rstrip("/").lower()
        if s:
            ada.add(s)

    mw = sum(1 for i in items if "moewalls.com" in (i.get("sourceUrl") or ""))
    print("  katalog       : %d entri" % len(items))
    print("  dari moewalls : %d entri" % mw)
    print()

    baru = {}
    diperiksa = 0

    for kat in KATEGORI:
        ketemu_kat = 0
        for hal in range(1, 9):
            url = "https://moewalls.com/%s/" % kat if hal == 1 else "https://moewalls.com/%s/page/%d/" % (kat, hal)
            try:
                html = get(url)
            except Exception:
                break
            tautan = set(m.group(0) for m in POLA_TAUTAN.finditer(html))
            if not tautan:
                break
            diperiksa += len(tautan)
            for t in tautan:
                if t.rstrip("/").lower() not in ada:
                    baru[t] = kat
                    ketemu_kat += 1
            print("     %-12s hal %-2d  %3d tautan  (%d baru)" % (kat, hal, len(tautan), ketemu_kat))
            time.sleep(0.6)
            if ketemu_kat >= 80:
                break

    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   tautan diperiksa : %d" % diperiksa)
    print("   tautan BARU      : %d" % len(baru))
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    if baru:
        print("  contoh yang baru:")
        for t, k in list(baru.items())[:12]:
            print("     [%s] %s" % (k, t))
        print()
        simpan = W / "build" / "moewalls-baru.json"
        simpan.parent.mkdir(parents=True, exist_ok=True)
        simpan.write_text(json.dumps(baru, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  disimpan: %s" % simpan)
    else:
        print("  TIDAK ADA tautan baru di halaman yang diperiksa.")
        print("  Artinya moewalls sudah tersedot untuk kategori ini; sumber lain")
        print("  (motionbgs / desktophut / wallhaven) diperlukan untuk 500 entri.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
