#!/usr/bin/env python3
"""Gabungkan entri anime mature dari wallhaven ke katalog.

KENAPA ALAT INI ADA:

Permintaannya: "cari yg mature banyakin ini cuma 69 masa aku mat at least 1000
buat mature pastiin anime mature ya".

Alat ini memasukkan hasil tools/ambil-mature-wallhaven.py ke LumaWall/catalog.json,
lalu memeriksa hasilnya sebelum menulis - bukan sesudah.

APA YANG DIPERIKSA, DAN KENAPA:

  1. Duplikat. Katalog memakai videoUrl sebagai kunci. Menambahkan entri yang
     sudah ada akan membuat dua kartu untuk gambar yang sama.

  2. Judul aman. UNSAFE_TITLE di tools/check-catalog.py menolak tokoh yang
     dikodekan di bawah umur. Gambar dari sumber komunitas bisa saja memakai
     nama seperti itu, dan itu tidak boleh masuk kategori Mature.

  3. Rasio lanskap dan resolusi. Entri potret tidak muat di layar lebar, dan
     di bawah 1920 tidak tajam di monitor 1080p.

  4. Bagian dinamis katalog. Pemeriksa mensyaratkan minimal 90% entri
     dinamis. Menambahkan 1000 gambar statis menggeser bagian itu, dan
     pergeserannya dihitung lebih dulu.

Hasilnya ditulis hanya kalau semuanya lolos.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"
SUMBER = W / "build" / "wallhaven-mature.json"
CADANGAN = W / "build" / "catalog-sebelum-mature.json"

# Sama dengan yang dipakai tools/check-catalog.py.
UNSAFE_TITLE = re.compile(
    r"\b(loli|lolita|child|kid|little girl|baby|daughter|schoolgirl|school girl|student"
    r"|teen|anya|kanna|pokemon|nezuko|nahida|klee|qiqi|yaoyao|diona|ibuki|blue archive"
    r"|juvenile)\b", re.I)

DYNAMIC_SHARE = 0.90


def main():
    if not SUMBER.exists():
        print("  ! %s belum ada - jalankan tools/ambil-mature-wallhaven.py dulu" % SUMBER)
        return 1

    katalog = json.load(open(CATALOG, encoding="utf-8"))
    items = katalog if isinstance(katalog, list) else katalog.get("Items", [])
    kunci = "Items" if isinstance(katalog, dict) and "Items" in katalog else None

    mentah = json.load(open(SUMBER, encoding="utf-8"))

    print()
    print("  ══════════════════════════════════════════════════════════════════")
    print("   MENGGABUNGKAN ANIME MATURE KE KATALOG")
    print("  ══════════════════════════════════════════════════════════════════")
    print()
    print("  katalog sekarang : %d entri" % len(items))
    print("  dari wallhaven   : %d entri" % len(mentah))
    print()

    # 1. duplikat
    sudah = set()
    for e in items:
        for k in ("videoUrl", "thumbnailUrl", "sourceUrl"):
            v = (e.get(k) or "").strip().lower()
            if v:
                sudah.add(v)

    # 2. saring
    dipakai = []
    alasan = Counter()
    for k in mentah:
        path = (k.get("path") or "").strip()
        thumb = (k.get("thumb") or "").strip()
        if not path or not thumb:
            alasan["tidak ada url"] += 1
            continue
        if path.lower() in sudah:
            alasan["duplikat"] += 1
            continue

        # Judul dibuat lebih dulu, karena judulnya yang diperiksa keamanannya.
        nama = (k.get("tag") or "Anime Illustration").strip()
        judul = "%s - %s" % (nama, (k.get("id") or "?").upper())
        if UNSAFE_TITLE.search(judul):
            alasan["judul tidak aman"] += 1
            continue

        res = k.get("res") or ""
        m = re.match(r"^(\d+)x(\d+)$", res)
        if not m:
            alasan["resolusi tidak terbaca"] += 1
            continue
        w, h = int(m.group(1)), int(m.group(2))
        if w <= h:
            alasan["potret"] += 1
            continue
        if w < 1920 or h < 1080:
            alasan["di bawah HD"] += 1
            continue

        sudah.add(path.lower())
        dipakai.append({
            "title": judul,
            "videoUrl": path,
            "thumbnailUrl": thumb,
            "license": "Wallhaven - ilustrasi anime (gambar statis)",
            "sourceUrl": k.get("page") or "",
            "category": "Mature 18+",
            "kind": "static",
            "author": "Wallhaven community",
            "animation": "",
            "resolution": res,
        })

    print("  disaring: %d dipakai" % len(dipakai))
    for nama, n in alasan.most_common():
        print("     dibuang: %-24s %d" % (nama, n))
    print()

    if not dipakai:
        print("  ! tidak ada yang bisa ditambahkan")
        return 1

    # 4. bagian dinamis setelah penambahan
    n_lama = len(items)
    n_baru = n_lama + len(dipakai)
    dinamis_lama = sum(1 for e in items if (e.get("kind") or "").lower() in ("dynamic", "video"))
    bagian = dinamis_lama / n_baru
    print("  katalog setelah  : %d entri" % n_baru)
    print("  dinamis          : %d (%.1f%%)" % (dinamis_lama, 100 * bagian))
    print("  batas            : %.0f%%" % (100 * DYNAMIC_SHARE))
    if bagian < DYNAMIC_SHARE:
        print("  ! TIDAK LOLOS - bagian dinamis akan jatuh di bawah batas")
        return 1
    print("  -> LOLOS")
    print()

    # 3. cadangkan, lalu tulis
    CADANGAN.write_text(json.dumps(katalog, ensure_ascii=False, indent=1), encoding="utf-8")
    print("  cadangan: %s" % CADANGAN)

    semua = items + dipakai
    if kunci:
        katalog[kunci] = semua
        keluar = katalog
    else:
        keluar = semua
    CATALOG.write_text(json.dumps(keluar, ensure_ascii=False, indent=1), encoding="utf-8")

    # Ringkasan
    kategori = Counter(e.get("category") or "?" for e in semua)
    print("  ditulis : %s" % CATALOG)
    print()
    print("  kategori sekarang:")
    for nama, n in kategori.most_common():
        print("     %-16s %d" % (nama, n))
    print()
    print("  Mature 18+ : %d  (sebelumnya %d)"
          % (kategori.get("Mature 18+", 0),
             sum(1 for e in items if e.get("category") == "Mature 18+")))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
