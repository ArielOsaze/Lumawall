#!/usr/bin/env python3
"""Buktikan apakah token video moewalls kedaluwarsa, atau ada sebab lain.

KENAPA BERKAS INI ADA:

Polanya mengejutkan dan tidak bisa dijelaskan oleh ciri token:
  anime   : 66 sehat,  0 gagal
  games   : 54 sehat, 42 gagal
  movies  : 26 sehat, 17 gagal
  abstract: 29 sehat, 19 gagal

Semua token diambil pada waktu yang sama, dengan cara yang sama, dari halaman
yang bentuknya sama. Kalau tokennya kedaluwarsa, anime seharusnya ikut gagal.

Dua penjelasan yang mungkin, dan keduanya bisa dibedakan:

  A. Token kedaluwarsa. Kalau begitu, mengambil token BARU dari halaman detail
     yang sama akan menghasilkan video yang bisa dipakai.

  B. Sumbernya membatasi jumlah unduhan per periode. Kalau begitu, token baru
     juga akan gagal untuk entri yang sama.

Alat ini mengambil token baru untuk beberapa entri yang gagal, lalu mengujinya
segera. Hasilnya menentukan mana dari dua penjelasan itu yang benar - dan itu
menentukan apakah 78 entri itu masih bisa diselamatkan.
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
DETAIL = W / "build" / "moewalls-detail.json"

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")}

POLA_KELAS_TOKEN = re.compile(r'id="moe-download"[^>]*', re.I)
POLA_TOKEN = re.compile(r'data-url\s*=\s*"([^"]+)"', re.I)


def ambil_token_baru(url_halaman):
    req = Request(url_halaman, headers=dict(UA, Accept="text/html,*/*;q=0.8"))
    with urlopen(req, timeout=30) as f:
        html = f.read().decode("utf-8", "replace")
    for kelas in POLA_KELAS_TOKEN.finditer(html):
        m = POLA_TOKEN.search(kelas.group(0))
        if m:
            return m.group(1)
    return None


def uji_video(url):
    try:
        h = dict(UA)
        h["Range"] = "bytes=0-1023"
        req = Request(url, headers=h, method="GET")
        with urlopen(req, timeout=25) as f:
            tipe = (f.headers.get("Content-Type") or "").lower()
            awal = f.read(1024)
            if "text/html" in tipe or awal.lstrip()[:1] == b"<":
                return False, "html"
            return True, tipe
    except HTTPError as e:
        return False, "http%d" % e.code
    except Exception as e:
        return False, str(e)[:30]


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   APAKAH TOKEN LAMA KEDALUWARSA - DIUJI DENGAN TOKEN BARU")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    detail = json.loads(DETAIL.read_text(encoding="utf-8"))
    siap = {u: d for u, d in detail.items() if not d.get("gagal")}

    # Cari entri yang videonya gagal, dari kategori selain anime.
    kandidat = []
    for u, d in siap.items():
        if d.get("category") == "anime":
            continue
        ok, ket = uji_video(d["videoUrl"])
        if not ok:
            kandidat.append((u, d, ket))
        if len(kandidat) >= 6:
            break

    print("  entri yang videonya gagal: %d ditemukan" % len(kandidat))
    print()

    diselamatkan = 0
    for u, d, sebab in kandidat:
        print("  %s" % d["title"][:60])
        print("     [%s] gagal dengan: %s" % (d["category"], sebab))

        try:
            token_baru = ambil_token_baru(u)
        except Exception as e:
            print("     tidak bisa mengambil token baru: %s" % str(e)[:50])
            print()
            continue

        if not token_baru:
            print("     token baru tidak ditemukan di halaman")
            print()
            continue

        sama = (token_baru == d["videoUrl"].split("video=", 1)[-1])
        print("     token baru %s token lama" % ("SAMA dengan" if sama else "BERBEDA dari"))

        url_baru = "https://go.moewalls.com/download.php?video=" + token_baru
        ok, ket = uji_video(url_baru)
        print("     token baru diuji: %s %s" % ("BISA DIPAKAI" if ok else "gagal", ket))
        if ok:
            diselamatkan += 1
        print()
        time.sleep(1.0)

    print("  ══════════════════════════════════════════════════════════════════")
    if diselamatkan:
        print("   %d dari %d entri BISA DISELAMATKAN dengan token baru." % (diselamatkan, len(kandidat)))
        print("   Artinya token memang kedaluwarsa - bukan sumbernya yang menolak.")
        print("   Perbaikannya: ambil token tepat sebelum entri dimasukkan.")
    else:
        print("   Tidak ada yang bisa diselamatkan dengan token baru.")
        print("   Artinya bukan token kedaluwarsa - sumbernya yang menolak entri")
        print("   ini. Entri yang gagal memang harus dibuang.")
    print("  ══════════════════════════════════════════════════════════════════")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
