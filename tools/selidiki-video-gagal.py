#!/usr/bin/env python3
"""Selidiki kenapa sebagian video moewalls gagal diuji.

KENAPA BERKAS INI ADA:

Dari 253 entri moewalls, 78 video dilaporkan "tidak bisa dipakai" oleh uji
jaringan. Membuang 78 dari 253 berarti kehilangan 31% - jadi sebelum dibuang,
harus dipastikan bahwa videonya memang rusak, bukan cara mengujinya yang salah.

Itu sudah terjadi beberapa kali di proyek ini: alat yang salah membaca
melaporkan masalah yang tidak ada, dan kalau dipercaya, entri yang sehat akan
dibuang.

Yang diuji untuk setiap video yang dilaporkan gagal:
  1. GET biasa                  - cara uji yang dipakai
  2. HEAD                       - sebagian server hanya menjawab HEAD
  3. GET tanpa Referer          - Referer asing bisa ditolak
  4. GET dengan Referer moewalls - Referer yang benar
  5. GET dengan Rentang byte    - meminta 1 KB pertama saja
  6. GET tanpa User-Agent       - sebagian CDN menolak UA tertentu

Kalau salah satu cara berhasil, videonya sehat dan uji pertama yang salah.
"""

import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
DETAIL = W / "build" / "moewalls-detail.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def coba(nama, url, headers=None, method="GET", rentang=None):
    h = dict(headers or {})
    if rentang:
        h["Range"] = rentang
    try:
        req = Request(url, headers=h, method=method)
        with urlopen(req, timeout=25) as f:
            tipe = (f.headers.get("Content-Type") or "").lower()
            awal = f.read(256) if method == "GET" else b""
            panjang = f.headers.get("Content-Length")
            return True, "%s %s%s" % (f.status, tipe or "?", (" len=" + panjang) if panjang else "")
    except HTTPError as e:
        return False, "HTTP %d" % e.code
    except (URLError, OSError) as e:
        return False, str(e)[:45]


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   KENAPA SEBAGIAN VIDEO MOEWALLS GAGAL DIUJI")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    detail = json.loads(DETAIL.read_text(encoding="utf-8"))
    siap = {u: d for u, d in detail.items() if not d.get("gagal")}
    print("  entri siap: %d" % len(siap))
    print()

    # Ambil beberapa video untuk diuji dengan banyak cara.
    contoh = list(siap.items())[:8]
    print("  ── menguji %d video dengan 6 cara ──" % len(contoh))
    print()

    CARA = [
        ("GET biasa", {"User-Agent": UA}, "GET", None),
        ("HEAD", {"User-Agent": UA}, "HEAD", None),
        ("GET tanpa Referer", {"User-Agent": UA}, "GET", None),
        ("GET + Referer moewalls", {"User-Agent": UA, "Referer": "https://moewalls.com/"}, "GET", None),
        ("GET rentang 1KB", {"User-Agent": UA, "Range": "bytes=0-1023"}, "GET", None),
        ("GET tanpa UA", {}, "GET", None),
    ]

    ringkas = {nama: 0 for nama, _, _, _ in CARA}

    for url, d in contoh:
        v = d["videoUrl"]
        print("  %s" % d["title"][:64])
        print("     %s" % v[:96])
        for nama, h, metode, _ in CARA:
            ok, ket = coba(nama, v, h, metode)
            if ok:
                ringkas[nama] += 1
            print("        %-24s %s %s" % (nama, "OK  " if ok else "gagal", ket))
        print()

    print("  ══════════════════════════════════════════════════════════════════")
    print("   BERAPA YANG BERHASIL PER CARA (dari %d video)" % len(contoh))
    print("  ══════════════════════════════════════════════════════════════════")
    print()
    for nama, n in sorted(ringkas.items(), key=lambda x: -x[1]):
        print("     %-26s %d/%d" % (nama, n, len(contoh)))
    print()

    terbaik = max(ringkas.values())
    if terbaik == len(contoh):
        print("   Setidaknya satu cara berhasil untuk SEMUA video.")
        print("   Artinya video-video ini SEHAT, dan uji pertama yang salah.")
    elif terbaik > 0:
        print("   Sebagian video bisa dipakai dengan cara tertentu.")
        print("   Uji harus memakai cara itu sebelum membuang entri.")
    else:
        print("   Tidak ada cara yang berhasil. Videonya memang tidak bisa diambil")
        print("   langsung - kemungkinan perlu token sesi atau tautannya kedaluwarsa.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
