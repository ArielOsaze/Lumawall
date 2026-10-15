#!/usr/bin/env python3
"""Gabungkan entri baru dari beberapa berkas hasil panen ke katalog.

KENAPA ALAT INI ADA:

Setiap sumber punya alat panennya sendiri, dan masing-masing menulis berkasnya
sendiri. Menggabungkan satu per satu dengan alat yang berbeda berarti katalog
ditulis berkali-kali, dan setiap penulisan berisiko kehilangan entri dari
sumber sebelumnya kalau urutannya salah.

Alat ini membaca SEMUA berkas hasil panen yang ada, memeriksa setiap entri
dengan aturan yang sama, lalu menulis katalog sekali.

Aturan pemeriksaannya sama dengan sebelumnya:
  1. Field wajib lengkap
  2. videoUrl tidak duplikat - baik dengan katalog maupun antar sumber
  3. sourceUrl tidak duplikat
  4. Kategori dikenal aplikasi

Pemakaian:
  python tools/gabung-semua-baru.py --kering
  python tools/gabung-semua-baru.py
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
KATALOG = W / "LumaWall" / "catalog.json"

# Berkas hasil panen yang digabungkan, berurutan.
SUMBER = [
    ("wallpaperwaifu-baru.json", "daftar entri siap"),
    ("wallhaven-baru.json", "daftar entri siap"),
]

KATEGORI_SAH = {"Anime", "Gaming", "Movies", "Nature", "Cars", "Superheroes",
                "Sports", "TV Shows", "Technology", "Abstract", "Food", "Music",
                "Mature 18+"}


def baca(path):
    if not path.exists():
        return []
    d = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(d, list):
        return d
    # Berkas panen moewalls memakai bentuk {url: {...}}.
    return [v for v in d.values() if isinstance(v, dict)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kering", action="store_true")
    args = p.parse_args()

    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   MENGGABUNGKAN SEMUA ENTRI BARU")
    print("  ══════════════════════════════════════════════════════════════════")
    print()

    data = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("Items", data.get("items", []))
    sebelum = len(items)
    print("  katalog sekarang: %d" % sebelum)

    ada_video = set()
    ada_sumber = set()
    for it in items:
        v = (it.get("videoUrl") or "").strip()
        s = (it.get("sourceUrl") or "").strip().rstrip("/").lower()
        if v:
            ada_video.add(v)
        if s:
            ada_sumber.add(s)
    print()

    siap = []
    ditolak = Counter()

    for nama, keterangan in SUMBER:
        berkas = W / "build" / nama
        kandidat = baca(berkas)
        print("  ── %s ──" % nama)
        print("     %d entri" % len(kandidat))
        masuk = 0
        for d in kandidat:
            if d.get("gagal"):
                ditolak["panen gagal"] += 1
                continue
            judul = (d.get("title") or "").strip()
            video = (d.get("videoUrl") or "").strip()
            thumb = (d.get("thumbnailUrl") or "").strip()
            kat = (d.get("category") or "").strip()
            sumber = (d.get("sourceUrl") or "").strip().rstrip("/").lower()

            if not judul or not video or not thumb or not kat:
                ditolak["field tidak lengkap"] += 1
                continue
            if kat not in KATEGORI_SAH:
                ditolak["kategori tidak dikenal: " + kat[:24]] += 1
                continue
            if video in ada_video:
                ditolak["videoUrl sudah ada"] += 1
                continue
            if sumber and sumber in ada_sumber:
                ditolak["sourceUrl sudah ada"] += 1
                continue

            ada_video.add(video)
            if sumber:
                ada_sumber.add(sumber)

            # Dilengkapi supaya bentuknya sama dengan entri katalog lain.
            entri = {
                "title": judul,
                "videoUrl": video,
                "thumbnailUrl": thumb,
                "license": d.get("license") or "Free for personal use",
                "sourceUrl": d.get("sourceUrl") or "",
                "category": kat,
                "kind": d.get("kind") or "dynamic",
                "author": d.get("author") or "",
                "animation": d.get("animation") or "",
                "resolution": d.get("resolution") or "1920x1080",
            }
            siap.append(entri)
            masuk += 1
        print("     masuk: %d" % masuk)
        print()

    print("  ── ringkasan ──")
    print("     siap dimasukkan : %d" % len(siap))
    for sebab, n in ditolak.most_common(8):
        print("     ditolak %-32s %5d" % (sebab[:32], n))
    print()

    if siap:
        print("  ── sebaran kategori entri baru ──")
        for k, n in Counter(x["category"] for x in siap).most_common():
            print("     %-16s %5d" % (k, n))
        print()

    if args.kering or not siap:
        print("  (mode kering atau tidak ada yang siap - katalog TIDAK diubah)")
        print()
        return 0

    items.extend(siap)
    KATALOG.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")

    print("  ══════════════════════════════════════════════════════════════════")
    print("   katalog sebelum : %d" % sebelum)
    print("   ditambahkan     : %d" % len(siap))
    print("   katalog sekarang: %d" % len(items))
    print("  ══════════════════════════════════════════════════════════════════")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
