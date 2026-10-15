#!/usr/bin/env python3
"""Uji: apakah host membatasi kalau banyak gambar diminta sekaligus?

KENAPA ALAT INI ADA:

Katalog bersih (0 thumbnail kosong), cache bersih, hotlink bukan masalah,
Referer bukan masalah - tetapi pengguna masih melihat gambar yang tidak muncul.

Yang belum diuji: CARA aplikasi meminta gambarnya. Grid katalog memuat puluhan
kartu sekaligus, dan setiap kartu memulai Task.Run sendiri untuk mengunduh
thumbnail-nya. Artinya satu layar penuh bisa menembakkan 20-40 permintaan ke
host yang SAMA dalam satu detik.

Host yang melindungi diri akan mulai menolak permintaan setelah beberapa
permintaan cepat dari alamat IP yang sama - biasanya dengan 429 (Too Many
Requests) atau 403. Aplikasi menelan kegagalan itu tanpa jejak (`catch { }`),
jadi kartu hanya tetap kosong dan tidak ada yang tahu kenapa.

Alat ini menguji berapa banyak permintaan cepat yang bisa diterima setiap host
sebelum mulai menolak, dan pada permintaan keberapa penolakan itu mulai.
"""

import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KATALOG = W / "LumaWall" / "catalog.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Seberapa banyak permintaan sekaligus - meniru satu layar penuh kartu.
SEKALIGUS = 24


def ambil(url, referer):
    h = {"User-Agent": UA, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
    if referer:
        h["Referer"] = referer
    mulai = time.time()
    try:
        req = Request(url, headers=h, method="GET")
        with urlopen(req, timeout=25) as f:
            isi = f.read(2048)
            tipe = (f.headers.get("Content-Type") or "").lower()
            return f.status, "image" in tipe and bool(isi), time.time() - mulai
    except HTTPError as e:
        return e.code, False, time.time() - mulai
    except (URLError, OSError):
        return 0, False, time.time() - mulai


def main():
    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   APAKAH HOST MEMBATASI PERMINTAAN GAMBAR YANG BANYAK SEKALIGUS")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))

    per_host = defaultdict(list)
    for it in items:
        u = (it.get("thumbnailUrl") or "").strip()
        if u:
            per_host[urlparse(u).netloc].append(u)

    # Referer yang dipakai aplikasi sekarang.
    REFERER = "https://motionbgs.com/"

    ringkas = {}

    for host, daftar in sorted(per_host.items(), key=lambda x: -len(x[1])):
        contoh = daftar[:SEKALIGUS]
        if len(contoh) < 4:
            continue

        print("  ── %s (%d entri) ──" % (host, len(daftar)))
        print("     meminta %d gambar sekaligus..." % len(contoh))

        hasil = []
        with ThreadPoolExecutor(max_workers=len(contoh)) as pool:
            tugas = [pool.submit(ambil, u, REFERER) for u in contoh]
            for t in tugas:
                hasil.append(t.result())

        kode = Counter(k for k, _, _ in hasil)
        berhasil = sum(1 for _, ok, _ in hasil if ok)
        lambat = max((d for _, _, d in hasil), default=0)

        print("     berhasil : %d dari %d" % (berhasil, len(hasil)))
        print("     jawaban  : %s" % dict(kode))
        print("     terlama  : %.1f detik" % lambat)
        print()

        ringkas[host] = {"entri": len(daftar), "diminta": len(contoh),
                         "berhasil": berhasil, "kode": dict(kode)}

        # Jeda sopan sebelum host berikutnya.
        time.sleep(2)

    print("  ══════════════════════════════════════════════════════════════════")
    print("   KESIMPULAN")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    gagal = [(h, r) for h, r in ringkas.items() if r["berhasil"] < r["diminta"]]
    if gagal:
        print("   HOST YANG MENOLAK SEBAGIAN PERMINTAAN SERENTAK:")
        for host, r in sorted(gagal, key=lambda x: x[1]["berhasil"] / max(1, x[1]["diminta"])):
            print("     %-30s %d/%d berhasil   %s" % (
                host, r["berhasil"], r["diminta"], r["kode"]))
        print()
        print("   Inilah sebabnya sebagian gambar tidak muncul saat katalog")
        print("   dimuat: permintaan yang ditolak tidak dicoba ulang, dan")
        print("   kegagalannya ditelan tanpa log.")
    else:
        print("   Semua host melayani %d permintaan serentak dengan baik." % SEKALIGUS)
        print("   Rate limit BUKAN penyebabnya.")
    print()

    (W / "build" / "uji-rate-limit.json").write_text(
        json.dumps(ringkas, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
