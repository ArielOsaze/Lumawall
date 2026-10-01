#!/usr/bin/env python3
"""Keluarkan entri Mature yang memakai karakter di bawah umur.

PEMERIKSA KATALOG MENANGKAP INI, dan penangkapannya benar.

Pemeriksa sudah punya penjaga UNSAFE_TITLE yang menolak judul memuat "loli",
"schoolgirl", "student", "teen", dan nama-nama karakter yang dikodekan sebagai
anak sekolah. Setelah kategori Mature diisi ulang dari tag moewalls, 12 entri
lolos ke sana dengan memakai nama karakter dari Blue Archive - game yang
seluruh pemainnya adalah murid sekolah.

Itu tepat sasaran penjaganya. Kategori dewasa tidak boleh memuat karakter yang
dikodekan sebagai anak sekolah, dan tidak ada alasan untuk melonggarkan
penjaganya demi menambah jumlah.

Entri-entrinya tidak dibuang dari katalog - hanya dikembalikan ke kategori
asalnya (Gaming, karena Blue Archive adalah game). Wallpapernya tetap ada dan
tetap bisa dipakai; yang dihentikan hanya penempatannya di kategori dewasa.

Pemakaian:
  python tools/saring-mature-aman.py            (periksa saja)
  python tools/saring-mature-aman.py --tulis    (terapkan)
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomicjson import write_json  # noqa: E402

KATALOG = ROOT / "LumaWall" / "catalog.json"

# Sama dengan UNSAFE_TITLE di tools/check-catalog.py. Kalau keduanya berbeda,
# pemeriksa akan terus melaporkan kegagalan yang sudah diperbaiki.
UNSAFE = re.compile(
    r"\b(loli|lolita|child|kid|little girl|baby|daughter|schoolgirl|school girl|student"
    r"|teen|anya|kanna|pokemon|nezuko|nahida|klee|qiqi|yaoyao|diona|ibuki|blue archive"
    r"|juvenile)\b", re.I)

# Nama seri yang berarti "sekolah" - dipakai untuk menentukan ke mana entri
# kembali. Blue Archive dan yang serupa adalah game, bukan anime.
GAME_SEKOLAH = re.compile(
    r"\b(blue archive|arknights|princess connect|umamusume|"
    r"girls' frontline|azur lane|kancolle|nikke)\b", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true")
    args = ap.parse_args()

    d = json.load(open(KATALOG, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("items", [])
    print()
    print("  == katalog: %d entri ==" % len(items))

    mat = [x for x in items if x.get("category") == "Mature 18+"]
    bad = [x for x in mat if UNSAFE.search(x.get("title") or "")]
    print("  Mature              : %d" % len(mat))
    print("  memakai karakter anak: %d" % len(bad))
    print()

    if not bad:
        print("  tidak ada yang perlu dikeluarkan")
        print()
        return 0

    print("  == yang dikeluarkan ==")
    for x in bad:
        j = x.get("title") or ""
        m = UNSAFE.search(j)
        tujuan = "Gaming" if GAME_SEKOLAH.search(j) else "Anime Girls"
        print("     %-52s [%s] -> %s" % (j[:52], m.group(0), tujuan))
    print()

    print("  == hasil ==")
    print("     Mature : %d -> %d" % (len(mat), len(mat) - len(bad)))
    print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis)")
        print()
        return 0

    shutil.copy2(KATALOG, str(KATALOG) + ".bak-aman")

    for x in bad:
        j = x.get("title") or ""
        x["category"] = "Gaming" if GAME_SEKOLAH.search(j) else "Anime Girls"

    write_json(KATALOG, items if isinstance(d, list) else d)

    daftar = []
    for x in items:
        if x.get("category") != "Mature 18+":
            continue
        mm = re.search(r"/media/(\d+)/", x.get("videoUrl") or "")
        daftar.append({
            "motionId": mm.group(1) if mm else "",
            "title": x.get("title") or "",
            "sourceUrl": x.get("sourceUrl") or "",
        })
    write_json(ROOT / "mature-audit" / "selected.json", daftar)

    print("  DITULIS")
    print("     Mature : %d" % len([x for x in items if x.get("category") == "Mature 18+"]))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
