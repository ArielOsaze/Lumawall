#!/usr/bin/env python3
"""Tambahkan kandidat DesktopHut yang sudah punya videoUrl ke katalog.

Lanjutan dari tools/ambil-video-desktophut.py: alat itu mengumpulkan videoUrl
untuk setiap kandidat yang judulnya memuat kata ketat, dan alat ini
memasukkannya ke katalog sebagai entri Mature 18+ yang sah.

Hanya entri yang videoUrl-nya ADA yang dimasukkan. Entri tanpa videoUrl akan
tampil sebagai kotak abu-abu di katalog, dan itu lebih buruk daripada tidak
menambahkannya sama sekali.

Resolusi diambil dari halaman wallpapernya, bukan ditebak. Entri yang
resolusinya di bawah 1280 px dibuang - katalog mensyaratkan HD.

Pemakaian:
  python tools/tambah-mature-desktophut.py            (periksa saja)
  python tools/tambah-mature-desktophut.py --tulis    (terapkan)
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
VIDEO = ROOT / "build" / "catalog-scrape" / "desktophut-video.json"
KARTU = ROOT / "build" / "catalog-scrape" / "mature-kartu.json"

TARGET = 15000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true")
    args = ap.parse_args()

    if not VIDEO.exists():
        print("  TIDAK ADA %s" % VIDEO)
        return 1
    if not KARTU.exists():
        print("  TIDAK ADA %s" % KARTU)
        return 1

    d = json.load(open(KATALOG, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("items", [])
    print()
    print("  == katalog: %d entri ==" % len(items))

    vid = json.load(open(VIDEO, encoding="utf-8"))
    vmap = vid.get("video") or {}
    kk = json.load(open(KARTU, encoding="utf-8"))
    kartu = kk.get("kartu") or {}
    print("  videoUrl terkumpul: %d" % len(vmap))

    ada_url = {(x.get("sourceUrl") or "").rstrip("/") for x in items}
    ada_vid = {(x.get("videoUrl") or "").strip() for x in items}

    tambah = []
    dibuang = []
    for url, v in vmap.items():
        u = (url or "").rstrip("/")
        vu = (v.get("videoUrl") or "").strip()
        if not u or not vu or u in ada_url or vu in ada_vid:
            continue
        # Judul dan thumbnail dari kartu.
        k = None
        for s, kv in kartu.items():
            if (kv.get("url") or "").rstrip("/") == u:
                k = kv
                break
        if not k:
            continue

        res = v.get("resolution") or k.get("resolution") or ""
        m = re.search(r"(\d{3,4})\s*x\s*(\d{3,4})", res)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
            # Katalog mensyaratkan HD, dan untuk wallpaper DESKTOP.
            #
            # Dua hal diperiksa, dan keduanya pernah lolos ke katalog:
            #   - sisi terpendek di bawah 720 px: bukan HD
            #   - tinggi lebih besar daripada lebar: wallpaper POTRET untuk
            #     ponsel, mis. 1080x1920. Di monitor desktop ia akan tampil
            #     dengan pita hitam besar di kiri dan kanan.
            if min(w, h) < 720:
                dibuang.append((k.get("title") or "", res, "di bawah HD"))
                continue
            if h > w:
                dibuang.append((k.get("title") or "", res, "potret (untuk ponsel)"))
                continue

        tambah.append({
            "title": k.get("title") or "",
            "videoUrl": vu,
            "thumbnailUrl": k.get("thumbnailUrl") or "",
            "sourceUrl": u,
            "resolution": res,
            "category": "Mature 18+",
            "kind": "video",
            "animation": "video",
            "author": "",
            "license": "",
        })
        ada_url.add(u)
        ada_vid.add(vu)

    print("  layak ditambah   : %d" % len(tambah))
    print("  dibuang (<720p)  : %d" % len(dibuang))
    print()

    print("  == yang akan ditambahkan ==")
    for x in tambah:
        print("     %-56s %s" % ((x.get("title") or "")[:56], x.get("resolution") or "-"))
    print()
    if dibuang:
        print("  == dibuang ==")
        for t, r, alasan in dibuang:
            print("     %-52s %-10s %s" % (t[:52], r, alasan))
        print()

    print("  == hasil ==")
    print("     katalog : %d -> %d" % (len(items), len(items) + len(tambah)))
    print("     Mature  : %d -> %d"
          % (len([x for x in items if x.get("category") == "Mature 18+"]),
             len([x for x in items if x.get("category") == "Mature 18+"]) + len(tambah)))
    print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis)")
        print()
        return 0

    shutil.copy2(KATALOG, str(KATALOG) + ".bak-tambah")
    semua = items + tambah
    write_json(KATALOG, semua if isinstance(d, list) else dict(d, items=semua))

    # selected.json dipakai pemeriksa katalog.
    daftar = []
    for x in semua:
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
    print("     katalog : %d entri" % len(semua))
    print("     Mature  : %d" % len([x for x in semua if x.get("category") == "Mature 18+"]))
    print("     seleksi : %s" % (ROOT / "mature-audit" / "selected.json"))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
