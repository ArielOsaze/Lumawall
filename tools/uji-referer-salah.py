#!/usr/bin/env python3
"""Uji: apakah Referer yang SALAH DOMAIN membuat host menolak gambarnya?

KENAPA ALAT INI ADA:

Kode aplikasi (MainWindow.cs, LoadRemoteThumbnail) mengirim Referer yang
di-hardcode untuk SEMUA thumbnail:

    request.Referer = "https://motionbgs.com/";

Padahal thumbnail katalog datang dari lima host berbeda. Artinya gambar dari
moewalls, desktophut, wallhaven, dan wallpaperwaifu diminta dengan Referer
milik motionbgs.

Uji hotlink sebelumnya tidak menemukan masalah karena ia hanya mencoba tiga
Referer: tanpa Referer, Referer situs LumaWall, dan Referer situs asalnya.
Ketiganya diterima. Yang TIDAK diuji adalah Referer milik situs LAIN - dan
itulah yang sebenarnya dikirim aplikasi.

Banyak host memakai perlindungan hotlink yang menolak permintaan dengan
Referer asing, sementara menerima permintaan tanpa Referer sama sekali. Jadi
gejalanya persis seperti yang dilaporkan: pemeriksa bilang gambar sehat,
pengguna melihat gambar rusak.

Alat ini menguji alamat yang sama dengan Referer yang berbeda-beda, termasuk
Referer motionbgs yang dipakai aplikasi sekarang.
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

# Referer yang diuji. "motionbgs" adalah yang dipakai aplikasi sekarang.
REFERER = {
    "motionbgs (dipakai app)": "https://motionbgs.com/",
    "tanpa referer": None,
    "asal (domain sendiri)": "ASAL",
}


def coba(url, referer):
    h = {"User-Agent": UA, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
    if referer == "ASAL":
        h["Referer"] = "https://" + urlparse(url).netloc + "/"
    elif referer:
        h["Referer"] = referer
    try:
        req = Request(url, headers=h, method="GET")
        with urlopen(req, timeout=25) as f:
            tipe = (f.headers.get("Content-Type") or "").lower()
            isi = f.read(512)
            if "image" in tipe and isi:
                return 200, "gambar"
            return 200, tipe or "?"
    except HTTPError as e:
        return e.code, "HTTP %d" % e.code
    except (URLError, OSError) as e:
        return 0, str(e)[:40]


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   APAKAH REFERER YANG SALAH DOMAIN MEMBUAT GAMBAR DITOLAK")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))

    per_host = {}
    for it in items:
        u = (it.get("thumbnailUrl") or "").strip()
        if u:
            per_host.setdefault(urlparse(u).netloc, []).append(u)

    print("  menguji %d host" % len(per_host))
    print()

    hasil = {}
    for host, daftar in sorted(per_host.items(), key=lambda x: -len(x[1])):
        baris = {}
        for nama, ref in REFERER.items():
            kode, ket = coba(daftar[0], ref)
            baris[nama] = (kode, ket)

        hasil[host] = {"jumlah_entri": len(daftar), "contoh": daftar[0], "uji": baris}

        print("  %s  (%d entri)" % (host, len(daftar)))
        print("     %s" % daftar[0][:92])
        for nama in REFERER:
            kode, ket = baris[nama]
            tanda = "OK  " if (kode == 200 and "gambar" in ket) else "GAGAL"
            print("        %s %-24s %s %s" % (tanda, nama, kode, ket))
        print()

    # ── Kesimpulan ────────────────────────────────────────────────────────
    print("  ══════════════════════════════════════════════════════════════════")
    print("   KESIMPULAN")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    rusak = []
    for host, h in hasil.items():
        app = h["uji"]["motionbgs (dipakai app)"]
        asal = h["uji"]["asal (domain sendiri)"]
        app_ok = app[0] == 200 and "gambar" in app[1]
        asal_ok = asal[0] == 200 and "gambar" in asal[1]
        if asal_ok and not app_ok:
            rusak.append((host, h["jumlah_entri"], app))

    if rusak:
        total = sum(n for _, n, _ in rusak)
        print("   HOST YANG GAMBARNYA GAGAL DI APLIKASI TAPI SEHAT DI SITUS ASAL:")
        for host, n, app in sorted(rusak, key=lambda x: -x[1]):
            print("     %-30s %6d entri   (%s %s)" % (host, n, app[0], app[1]))
        print()
        print("   Total entri terdampak: %d" % total)
        print()
        print("   Penyebabnya: kode aplikasi mengirim Referer motionbgs.com untuk")
        print("   semua thumbnail, termasuk yang bukan dari motionbgs.")
    else:
        print("   Tidak ada host yang menolak karena Referer salah.")
        print("   Referer bukan penyebabnya.")
    print()

    (W / "build" / "uji-referer.json").write_text(
        json.dumps(hasil, ensure_ascii=False, indent=1), encoding="utf-8")
    print("  hasil: build/uji-referer.json")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
