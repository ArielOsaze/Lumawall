#!/usr/bin/env python3
"""Uji apakah thumbnail bisa dimuat TANPA Referer - seperti yang dilakukan aplikasi.

KENAPA ALAT INI ADA:

Pemeriksa thumbnail melaporkan 4000 dari 4000 alamat "OK" sementara pengguna
masih melihat banyak gambar tidak muncul. Dua hal itu tidak bisa sama-sama
benar, jadi salah satu pengukurannya tidak mewakili kenyataan.

Dugaannya: pemeriksa memakai Referer "https://lumawall.xinet.id/" dan header
Accept gambar. Sebagian host memakai perlindungan hotlink - gambar hanya
dilayani kalau permintaannya datang dari halaman mereka sendiri, dan ditolak
kalau datang dari tempat lain. Kalau host memblokir berdasarkan Referer,
pemeriksa yang mengirim Referer situs sendiri akan melihat gambar sehat
sementara APLIKASI, yang memuat gambar lewat WebView2 tanpa Referer itu,
mendapat penolakan.

Itu akan menjelaskan persis gejalanya: "alat bilang sehat, pengguna bilang
rusak".

Jadi alat ini meminta alamat yang sama dengan TIGA cara, dan membandingkan:
  1. tanpa Referer sama sekali   - cara aplikasi memuatnya
  2. dengan Referer situs LumaWall - cara pemeriksa tadi memuatnya
  3. dengan Referer situs sumber    - cara halaman aslinya memuatnya

Kalau (1) gagal sementara (2) berhasil, penyebabnya hotlink protection - dan
itulah yang harus diperbaiki, bukan alamat gambarnya.
"""

import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KATALOG = W / "LumaWall" / "catalog.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def coba(url, referer=None):
    """Kembalikan (kode, keterangan)."""
    h = {"User-Agent": UA, "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"}
    if referer:
        h["Referer"] = referer
    try:
        req = Request(url, headers=h, method="GET")
        with urlopen(req, timeout=25) as f:
            tipe = (f.headers.get("Content-Type") or "").lower()
            isi = f.read(1024)
            if not isi:
                return 0, "kosong"
            if "image" in tipe:
                return 200, tipe
            if "text/html" in tipe:
                return 200, "HTML (bukan gambar)"
            return 200, tipe or "?"
    except HTTPError as e:
        return e.code, "HTTP %d" % e.code
    except (URLError, OSError) as e:
        return 0, str(e)[:50]


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   UJI HOTLINK: apakah gambar bisa dimuat TANPA Referer")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))

    # Ambil contoh dari setiap host - masalah hotlink biasanya milik host,
    # bukan milik satu gambar.
    per_host = {}
    for it in items:
        u = (it.get("thumbnailUrl") or "").strip()
        if not u:
            continue
        host = urlparse(u).netloc
        per_host.setdefault(host, []).append(u)

    print("  host yang dipakai: %d" % len(per_host))
    print()

    ringkas = Counter()
    rincian = []

    for host, daftar in sorted(per_host.items(), key=lambda x: -len(x[1])):
        contoh = daftar[:3]
        for u in contoh:
            k1, t1 = coba(u, None)
            k2, t2 = coba(u, "https://lumawall.xinet.id/")
            k3, t3 = coba(u, "https://" + host + "/")

            gambar1 = k1 == 200 and "image" in t1
            gambar2 = k2 == 200 and "image" in t2
            gambar3 = k3 == 200 and "image" in t3

            tanda = "AMAN  " if gambar1 else "DIBLOKIR"
            if not gambar1:
                ringkas[host] += 1

            rincian.append((host, u, gambar1, gambar2, gambar3, t1, t2, t3))

            print("  %s %s" % (tanda, host))
            print("        %s" % u[:92])
            print("        tanpa Referer : %s %s" % (k1, t1))
            print("        Referer kita  : %s %s" % (k2, t2))
            print("        Referer asal  : %s %s" % (k3, t3))
            print()

    print("  ══════════════════════════════════════════════════════════════════")
    if ringkas:
        print("   HOST YANG MEMBLOKIR TANPA REFERER:")
        for host, n in ringkas.most_common():
            jumlah = len(per_host[host])
            print("     %-32s %d contoh gagal dari %d entri" % (host, n, jumlah))
        print()
        print("   Inilah sebabnya pemeriksa melaporkan 'OK' sementara pengguna")
        print("   melihat gambar rusak: pemeriksa memakai Referer, aplikasi tidak.")
    else:
        print("   Semua host melayani gambar tanpa Referer.")
        print("   Jadi gambar rusak yang dilihat pengguna BUKAN disebabkan hotlink.")
        print("   Penyebab lain harus dicari - cara aplikasi memuat gambar,")
        print("   atau alamat yang memang tidak bisa dijangkau dari PC pengguna.")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    (W / "build" / "uji-hotlink.json").write_text(
        json.dumps([{"host": h, "url": u, "tanpa_referer": a, "referer_kita": b,
                     "referer_asal": c, "tipe1": t1, "tipe2": t2, "tipe3": t3}
                    for h, u, a, b, c, t1, t2, t3 in rincian], ensure_ascii=False, indent=1),
        encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
