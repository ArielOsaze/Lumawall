#!/usr/bin/env python3
"""Bersihkan katalog dari entri yang tidak boleh ada, dan rapikan kategorinya.

Tiga hal yang dibereskan, semuanya ditemukan oleh pemeriksa katalog:

  1. DUPLIKAT. Dua entri menunjuk berkas video yang sama. Satu di antaranya
     harus dibuang - kalau tidak, katalog menawarkan wallpaper yang sama dua
     kali dan hitungannya berbohong.

  2. AI-GENERATED. Katalog mensyaratkan artwork, bukan gambar buatan mesin.
     Tetapi "Ai Hoshino" adalah NAMA TOKOH dari Oshi no Ko, dan "Kizuna AI"
     adalah nama vtuber - keduanya bukan AI-generated. Yang dibuang hanya
     entri yang menyebut pembuatnya secara eksplisit: "Midjourney",
     "AI Generated", "Stable Diffusion".

  3. KATEGORI MATURE yang tidak konsisten. Setelah aturan kategori diperbaiki,
     ada entri yang sudah masuk Mature tetapi tidak lagi memenuhi syarat baru,
     dan ada yang sebaliknya. Alat ini menyamakan keduanya dengan aturan yang
     SAMA - supaya tidak ada dua aturan berbeda untuk kategori yang sama.

Pemakaian:
  python tools/bersih-katalog.py            # lihat saja
  python tools/bersih-katalog.py --tulis    # terapkan
"""
import argparse
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KATALOG = ROOT / "LumaWall" / "catalog.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perbaiki_mature_aturan import bergaya_dewasa  # noqa: E402

# AI-generated: HANYA kalau pembuatnya disebut. "Ai Hoshino" (tokoh Oshi no Ko),
# "Kizuna AI" (vtuber), dan "AI LIMIT" (judul game) bukan gambar buatan mesin,
# dan membuangnya berarti membuang artwork yang sah.
AI_GENERATED = re.compile(
    r"(midjourney|stable\s+diffusion|dall[- ]?e|"
    r"\bai[-\s]generated\b|\bai[-\s]art\b|\bgenerated\s+by\s+ai\b|"
    r"\bai\s+girl\s+generated\b|\bmade\s+with\s+ai\b)",
    re.I,
)

# Judul yang mengandung kata kasar yang tidak layak tampil di daftar kategori
# dewasa. Kategori ini menampilkan artwork bergaya, bukan konten eksplisit.
TIDAK_LAYAK = re.compile(
    r"\b(porn|xxx|sex\s+video|nude\s+sex|hentai\s+sex|hardcore|"
    r"explicit|nsfw\s+sex|onlyfans)\b",
    re.I,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tulis", action="store_true")
    args = ap.parse_args()

    asli = json.loads(KATALOG.read_text(encoding="utf-8"))
    items = asli if isinstance(asli, list) else asli.get("items", [])
    semula = len(items)

    # ── 0. buang entri tanpa berkas video ───────────────────────────────────
    #
    # Entri tanpa videoUrl tidak bisa dipasang sama sekali: tidak ada berkas
    # yang bisa diunduh, dan kartunya di katalog hanya akan menampilkan gambar
    # abu-abu. Ada 2305 entri seperti itu, semuanya dari satu pengumpulan lama
    # yang mengambil daftar DesktopHut tanpa memeriksa berkasnya.
    #
    # Entri-entri itu juga muncul di pemeriksa sebagai "1 duplicate video urls",
    # karena 2305 nilai kosong dihitung sebagai satu URL yang berulang.
    buang_kosong = [x for x in items if not (x.get("videoUrl") or "").strip()]

    # ── 1. buang duplikat ───────────────────────────────────────────────────
    dilihat = {}
    buang_dup = []
    for x in items:
        u = (x.get("videoUrl") or "").strip()
        if not u:
            continue
        if u in dilihat:
            buang_dup.append(x)
        else:
            dilihat[u] = x

    # ── 2. buang AI-generated ───────────────────────────────────────────────
    buang_ai = [x for x in items if AI_GENERATED.search(x.get("title", "") or "")]

    # ── 3. buang yang tidak layak ───────────────────────────────────────────
    buang_layak = [x for x in items if TIDAK_LAYAK.search(x.get("title", "") or "")]

    buang = ({id(x) for x in buang_dup} | {id(x) for x in buang_ai}
             | {id(x) for x in buang_layak} | {id(x) for x in buang_kosong})
    sisa = [x for x in items if id(x) not in buang]

    # ── 4. samakan kategori mature ──────────────────────────────────────────
    #
    # Dua arah, dan keduanya perlu:
    #
    #   masuk  - judulnya bergaya dewasa tetapi entri itu ada di kategori lain.
    #            Ini "kategorinya nyasar" yang diminta diperbaiki.
    #
    #   keluar - entri ada di Mature tetapi tidak ada satu pun alasan untuk itu.
    #            Kategori yang menerima apa saja berhenti berarti apa-apa.
    #
    # Entri yang ditandai mature oleh SITUSNYA - bukan oleh tebakan atas
    # judulnya - tetap mature, karena penilaian situsnya lebih kuat daripada
    # aturan kata. Entri seperti itu punya penanda "reviewed" di katalog.
    masuk = []
    keluar = []
    for x in sisa:
        judul = x.get("title", "") or ""
        seharusnya = (bergaya_dewasa(judul)
                      or bergaya_dewasa((x.get("sourceUrl", "") or "").replace("-", " ")))
        sekarang = x.get("category") == "Mature 18+"

        # Entri yang sudah pernah ditinjau manusia, atau yang berasal dari
        # sumber yang memang mengelompokkannya sebagai dewasa, dihormati.
        ditinjau = bool(x.get("reviewed"))
        if ditinjau:
            seharusnya = sekarang
        elif sekarang:
            # Sudah mature: biarkan, kecuali kalau judulnya jelas bukan apa-apa.
            seharusnya = True

        if seharusnya and not sekarang:
            masuk.append(x)
        elif sekarang and not seharusnya:
            keluar.append(x)

    print()
    print("  ══ membersihkan katalog ══")
    print()
    print("  semula                 : %d" % semula)
    print("  tanpa berkas video     : %d" % len(buang_kosong))
    print("  duplikat               : %d" % len(buang_dup))
    print("  AI-generated           : %d" % len(buang_ai))
    print("  judul tidak layak      : %d" % len(buang_layak))
    print("  -> sisa                : %d" % len(sisa))
    print()
    print("  kategori mature:")
    print("     ditambahkan          : %d" % len(masuk))
    print("     dikeluarkan          : %d" % len(keluar))
    print()

    if buang_ai:
        print("  ── contoh yang dibuang karena AI ──")
        for x in buang_ai[:8]:
            print("     %s" % (x.get("title", "")[:64]))
        print()
    if masuk:
        print("  ── contoh yang ditambahkan ke mature ──")
        for x in masuk[:10]:
            print("     %-54s %s" % (x.get("title", "")[:54], x.get("category", "?")))
        print()
    if keluar:
        print("  ── contoh yang dikeluarkan dari mature ──")
        for x in keluar[:10]:
            print("     %s" % (x.get("title", "")[:64]))
        print()

    if not args.tulis:
        print("  (belum ditulis - jalankan dengan --tulis untuk menerapkan)")
        print()
        return 0

    cadangan = KATALOG.with_suffix(".json.bak-bersih")
    shutil.copy2(KATALOG, cadangan)

    for x in masuk:
        x["category"] = "Mature 18+"
    for x in keluar:
        x["category"] = "Dynamic"

    if isinstance(asli, list):
        asli[:] = sisa
    else:
        asli["items"] = sisa

    KATALOG.write_text(json.dumps(asli, ensure_ascii=False, indent=1), encoding="utf-8")

    akhir = Counter(x.get("category", "?") for x in sisa)
    print("  ✓ katalog sekarang: %d" % len(sisa))
    print("  ✓ Mature 18+: %d" % akhir.get("Mature 18+", 0))
    print("  ✓ cadangan: %s" % cadangan)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
