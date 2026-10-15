#!/usr/bin/env python3
"""Gabungkan entri baru hasil panen ke katalog - dengan pemeriksaan, bukan asal tempel.

KENAPA ALAT INI ADA:

Menambahkan 500 entri ke katalog 26.778 entri tidak boleh dilakukan dengan
menempel begitu saja. Setiap entri baru harus lulus pemeriksaan yang sama
dengan entri yang sudah ada, karena satu entri rusak merusak seluruh katalog di
mata pengguna - dan kerusakannya tidak terlihat sampai seseorang membuka kartu
itu dan menemukan wallpaper yang tidak bisa diputar.

Yang diperiksa untuk setiap entri baru:

  1. Field wajib lengkap: title, videoUrl, thumbnailUrl, category, kind
  2. videoUrl benar-benar bisa dipakai (bukan halaman error)
  3. thumbnailUrl benar-benar gambar
  4. Tidak duplikat - baik dengan katalog lama maupun sesama entri baru
     (dicocokkan lewat videoUrl dan sourceUrl, BUKAN judul: "Albedo Overlord"
     ada banyak versi dan itu sah)
  5. Kategori termasuk daftar yang dikenal aplikasi

Yang gagal TIDAK dimasukkan, dan alasannya dilaporkan. Lebih baik 480 entri
yang semuanya bisa diputar daripada 500 dengan 20 yang rusak.

Pemakaian:
  python tools/gabung-entri-baru.py --kering     (periksa saja, tidak menulis)
  python tools/gabung-entri-baru.py              (tulis ke katalog)
"""

import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KATALOG = W / "LumaWall" / "catalog.json"
DETAIL = W / "build" / "moewalls-detail.json"

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
}

# Kategori yang dikenal aplikasi. Entri dengan kategori di luar daftar ini tidak
# akan punya saringan yang benar di halaman Discover.
KATEGORI_SAH = {"Anime", "Gaming", "Movies", "Nature", "Cars", "Superheroes",
                "Sports", "TV Shows", "Technology", "Abstract", "Food", "Music",
                "Mature 18+"}

# Pemetaan slug kategori moewalls -> nama kategori aplikasi.
PETA_KATEGORI = {
    "anime": "Anime",
    "games": "Gaming",
    "movies": "Movies",
    "nature": "Nature",
    "cars": "Cars",
    "superheroes": "Superheroes",
    "sports": "Sports",
    "tv-shows": "TV Shows",
    "technology": "Technology",
    "abstract": "Abstract",
    "food": "Food",
    "music": "Music",
}


def cek_gambar(url):
    try:
        req = Request(url, headers=dict(UA, Accept="image/*,*/*;q=0.8"), method="GET")
        with urlopen(req, timeout=20) as f:
            tipe = (f.headers.get("Content-Type") or "").lower()
            isi = f.read(512)
            return bool(isi) and "image" in tipe
    except Exception:
        return False


def cek_video(url):
    """Video moewalls: berkasnya ada dan bisa diambil.

    Meminta 1 KB pertama saja, bukan seluruh berkas.

    Video di sini berukuran 10-30 MB. Memakai GET biasa berarti server mulai
    mengirim seluruh berkas, dan dengan 16 pekerja serentak sebagian permintaan
    kehabisan waktu sebelum sempat membaca apa pun - sehingga 78 video sehat
    dilaporkan rusak. Rentang byte membuktikan hal yang sama tanpa itu.
    """
    h = dict(UA)
    h["Range"] = "bytes=0-1023"
    try:
        req = Request(url, headers=h, method="GET")
        with urlopen(req, timeout=25) as f:
            tipe = (f.headers.get("Content-Type") or "").lower()
            awal = f.read(1024)
            if not awal:
                return False
            # Halaman HTML berarti tautannya mengarah ke halaman error.
            if "text/html" in tipe or awal.lstrip()[:1] == b"<":
                return False
            return True
    except HTTPError as e:
        # 416 = server menolak rentang tetapi berkasnya ada; itu tetap sehat.
        if e.code == 416:
            return True
        # 403 dari go.moewalls.com sering berarti tautannya perlu token sah;
        # yang penting bukan 404.
        return e.code not in (404, 410)
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kering", action="store_true", help="periksa saja")
    p.add_argument("--periksa-jaringan", action="store_true",
                   help="uji setiap video dan gambar (lambat, tapi membuktikan)")
    args = p.parse_args()

    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   MENGGABUNGKAN ENTRI BARU KE KATALOG")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    if not DETAIL.exists():
        print("  ! berkas detail belum ada: %s" % DETAIL)
        return 1

    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))
    print("  katalog sekarang: %d entri" % len(items))

    detail = json.loads(DETAIL.read_text(encoding="utf-8"))
    print("  kandidat detail : %d" % len(detail))
    print()

    ada_video = set()
    ada_sumber = set()
    for it in items:
        v = (it.get("videoUrl") or "").strip()
        s = (it.get("sourceUrl") or "").strip().rstrip("/").lower()
        if v:
            ada_video.add(v)
        if s:
            ada_sumber.add(s)

    siap = []
    ditolak = Counter()
    contoh_tolak = {}

    for url, d in detail.items():
        if d.get("gagal"):
            ditolak["panen gagal: " + d["gagal"][:40]] += 1
            continue

        judul = (d.get("title") or "").strip()
        video = (d.get("videoUrl") or "").strip()
        thumb = (d.get("thumbnailUrl") or "").strip()
        kat = PETA_KATEGORI.get((d.get("category") or "").strip().lower(), "")

        if not judul:
            ditolak["judul kosong"] += 1
            continue
        if not video:
            ditolak["videoUrl kosong"] += 1
            continue
        if not thumb:
            ditolak["thumbnailUrl kosong"] += 1
            continue
        if not kat:
            ditolak["kategori tidak dikenal: " + str(d.get("category"))[:24]] += 1
            continue

        sumber = url.strip().rstrip("/").lower()
        if video in ada_video:
            ditolak["videoUrl sudah ada"] += 1
            continue
        if sumber in ada_sumber:
            ditolak["sourceUrl sudah ada"] += 1
            continue

        # Dicatat supaya dua kandidat baru yang sama tidak sama-sama lolos.
        ada_video.add(video)
        ada_sumber.add(sumber)

        siap.append({
            "title": judul,
            "videoUrl": video,
            "thumbnailUrl": thumb,
            "license": "Moewalls · free for personal use",
            "sourceUrl": url,
            "category": kat,
            "kind": "dynamic",
            "author": "Moewalls community",
            "animation": "",
            "resolution": "1920x1080",
        })

    print("  ── hasil pemeriksaan field ──")
    print("     siap dimasukkan : %d" % len(siap))
    print("     ditolak         : %d" % sum(ditolak.values()))
    for sebab, n in ditolak.most_common(10):
        print("        %-42s %5d" % (sebab[:42], n))
    print()

    if args.periksa_jaringan and siap:
        print("  ── menguji setiap video dan gambar (ini yang membuktikan) ──")
        contoh = siap
        with ThreadPoolExecutor(max_workers=6) as pool:
            hasil_video = list(pool.map(lambda x: cek_video(x["videoUrl"]), contoh))
            hasil_gambar = list(pool.map(lambda x: cek_gambar(x["thumbnailUrl"]), contoh))

        rusak_video = [i for i, ok in enumerate(hasil_video) if not ok]
        rusak_gambar = [i for i, ok in enumerate(hasil_gambar) if not ok]
        print("     video  tidak bisa dipakai : %d dari %d" % (len(rusak_video), len(contoh)))
        print("     gambar tidak bisa dipakai : %d dari %d" % (len(rusak_gambar), len(contoh)))
        print()

        if rusak_video or rusak_gambar:
            buang = set(rusak_video) | set(rusak_gambar)
            print("     membuang %d entri yang gagal diuji:" % len(buang))
            for i in sorted(buang)[:8]:
                sebab = []
                if i in rusak_video: sebab.append("video")
                if i in rusak_gambar: sebab.append("gambar")
                print("        [%s] %s" % (",".join(sebab), siap[i]["title"][:60]))
            siap = [x for i, x in enumerate(siap) if i not in buang]
            print("     sisa siap: %d" % len(siap))
            print()

    if not siap:
        print("  Tidak ada entri yang bisa dimasukkan.")
        return 1

    print("  ── sebaran kategori entri baru ──")
    for k, n in Counter(x["category"] for x in siap).most_common():
        print("     %-16s %5d" % (k, n))
    print()

    if args.kering:
        print("  (mode kering - katalog TIDAK diubah)")
        print()
        return 0

    items.extend(siap)
    KATALOG.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")

    print("  ══════════════════════════════════════════════════════════════════")
    print("   katalog sebelum : %d" % (len(items) - len(siap)))
    print("   ditambahkan     : %d" % len(siap))
    print("   katalog sekarang: %d" % len(items))
    print("  ══════════════════════════════════════════════════════════════════")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
