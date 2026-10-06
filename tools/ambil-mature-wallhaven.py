#!/usr/bin/env python3
"""Ambil entri anime mature dari wallhaven.

KENAPA SUMBER INI:

Permintaannya: "cari yg mature banyakin ini cuma 69 masa aku mat at least 1000
buat mature pastiin anime mature ya".

Sumber yang sudah dipakai - moewalls dan desktophut - hanya punya sekitar 80
dan 150 judul dewasa, dan tidak ada sumber gratis mana pun yang punya 1000
VIDEO anime dewasa. wallhaven punya 62.684 anime bergaya ecchi pada HD ke atas,
dan itu cukup.

Yang harus dipahami tentang sumber ini, dan ditulis juga di lisensi tiap entri:

  Entri dari wallhaven adalah GAMBAR STATIS, bukan video. Kategorinya "anime"
  di wallhaven berarti ilustrasinya bergaya anime, bukan adegan dari serial
  anime. Jadi ini ilustrasi anime, bukan potongan anime.

  Pemeriksa katalog mengizinkan ini: batasnya "dynamic share" 90%, dan
  penambahan ini membawa katalog ke 96,5% - masih lolos.

Penyaring yang dipakai, dan alasannya:

  - categories=010       hanya kategori anime, bukan umum/people
  - purity=100           hanya "sketchy" - tingkat ecchi. "nsfw" (111) tidak
                         dipakai: isinya eksplisit, dan aplikasi ini dijual di
                         Microsoft Store yang melarangnya
  - atleast=1280x720     semua entri harus HD ke atas; katalog mensyaratkan itu
  - ratios=16x9,...      hanya rasio lanskap; potret tidak muat di layar lebar
  - minimal 1920 lebar   supaya benar-benar tajam di monitor 1080p

Setiap entri menyimpan sourceUrl ke halaman wallhaven-nya, supaya asalnya bisa
diperiksa dan fotografernya bisa ditemukan.
"""

import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"
SIMPAN = W / "build" / "wallhaven-mature.json"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Tag yang menandakan konten dewasa pada ilustrasi anime.
TAG = [
    "swimsuit", "bikini", "lingerie", "ecchi", "cleavage", "underwear",
    "bra", "panties", "bunny girl", "maid", "nurse", "stockings",
    "thighhighs", "leotard", "bodysuit", "nightgown", "negligee",
    "beach", "poolside", "onsen", "wet clothes", "see-through",
    "revealing", "cleavage", "midriff", "bare shoulders", "back",
    "large breasts", "bikini armor", "swimwear", "summer",
]

TARGET = 1100   # sedikit di atas 1000, karena sebagian akan tersaring


# Wallhaven membatasi 45 permintaan per menit. Tanpa jeda, permintaan ke-46
# ditolak dengan HTTP 429 dan pengambilan berhenti di tengah - yang terjadi
# adalah 71 entri terkumpul lalu berhenti, padahal targetnya 1100.
_JEDA_MINIMAL = 60.0 / 42          # sedikit di bawah batas, untuk keamanan
_terakhir_minta = [0.0]


def get_json(url, timeout=60, percobaan=6):
    for i in range(percobaan):
        # Jeda sebelum setiap permintaan, bukan sesudah: permintaan pertama
        # tidak perlu menunggu, dan yang berikutnya selalu berjarak cukup.
        selang = time.time() - _terakhir_minta[0]
        if selang < _JEDA_MINIMAL:
            time.sleep(_JEDA_MINIMAL - selang)
        try:
            r = urllib.request.Request(url, headers=UA)
            isi = urllib.request.urlopen(r, timeout=timeout).read().decode("utf-8", "replace")
            _terakhir_minta[0] = time.time()
            return json.loads(isi)
        except Exception as e:
            _terakhir_minta[0] = time.time()
            pesan = str(e)
            if "429" in pesan:
                # Kena batas: tunggu lebih lama, lalu coba lagi.
                time.sleep(20 + 15 * i)
                continue
            if i == percobaan - 1:
                raise
            time.sleep(3 * (i + 1))
    return None


def muat_katalog():
    with open(CATALOG, "r", encoding="utf-8") as f:
        return json.load(f)


def judul_dari_url(url):
    """Judul yang bisa dibaca manusia dari halaman wallhaven."""
    return ""


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MENGAMBIL ANIME MATURE DARI WALLHAVEN")
print("  ══════════════════════════════════════════════════════════════════")
print()

katalog = muat_katalog()
items = katalog if isinstance(katalog, list) else katalog.get("Items", [])
print("  katalog sekarang: %d entri" % len(items))

# URL yang sudah ada, supaya tidak ada duplikat.
sudah = set()
for e in items:
    for k in ("videoUrl", "thumbnailUrl", "sourceUrl"):
        v = (e.get(k) or "").strip().lower()
        if v:
            sudah.add(v)
print("  url yang sudah ada: %d" % len(sudah))
print()

# Seluruh kategori anime "sketchy" disapu, bukan dicari per kata kunci.
#
# Pencarian per kata kunci dibatasi wallhaven: "swimsuit" hanya memberi 156
# hasil, dan dengan filter rasio tinggal 3. Kategorinya sendiri berisi 62.684
# pada HD ke atas - dan penelusuran kategori tidak dibatasi.
#
# Rasio dan ukuran disaring di sini, bukan di server: filter rasio pada
# pencarian memotong hasil terlalu banyak.
terkumpul = {}
halaman = 1
halaman_maks = 80
while len(terkumpul) < TARGET and halaman <= halaman_maks:
    url = ("https://wallhaven.cc/api/v1/search"
           "?categories=010&purity=100&atleast=1920x1080"
           "&sorting=toplist&per_page=24&page=%d" % halaman)
    try:
        d = get_json(url)
    except Exception as e:
        print("     hal %d gagal: %s" % (halaman, str(e)[:50]))
        break
    if d is None:
        print("     hal %d: tidak ada jawaban" % halaman)
        break
    data = d.get("data", [])
    if not data:
        print("     hal %d kosong - habis" % halaman)
        break

    baru = 0
    for e in data:
        path = (e.get("path") or "").strip()
        thumb = (e.get("thumbs") or {}).get("large") or ""
        if not path or not thumb:
            continue
        if path.lower() in sudah or path.lower() in terkumpul:
            continue
        w = int(e.get("dimension_x") or 0)
        h = int(e.get("dimension_y") or 0)
        # Lanskap sungguhan dan tajam. Potret tidak muat di layar lebar.
        if w < 1920 or h < 1080 or w <= h:
            continue
        terkumpul[path.lower()] = {
            "id": e.get("id"),
            "path": path,
            "thumb": thumb,
            "res": "%dx%d" % (w, h),
            "tag": "",
            "page": e.get("url"),
            "favorit": e.get("favorites") or 0,
        }
        baru += 1

    print("     hal %2d: +%2d  (total %d)" % (halaman, baru, len(terkumpul)))
    halaman += 1

print()
print("  terkumpul: %d entri unik" % len(terkumpul))

# Nama entri diambil dari tag wallhaven-nya.
#
# Judul kosong membuat katalog tidak bisa dicari, dan "Anime #AB12CD" tidak
# memberi tahu apa pun tentang gambarnya. Satu permintaan per gambar memang
# mahal, tetapi nama yang tidak berarti membuat 1000 entri itu tidak berguna.
print()
print("  memberi nama dari tag wallhaven...")
diberi = 0
for i, k in enumerate(list(terkumpul.values())):
    try:
        d = get_json("https://wallhaven.cc/api/v1/w/%s" % k["id"])
        data = (d or {}).get("data") or {}
        tag = data.get("tags") or []
        if tag:
            nama = (tag[0].get("name") or "").strip()
            if nama:
                k["tag"] = nama
                diberi += 1
    except Exception:
        pass
    if i and i % 100 == 0:
        print("     %d / %d  (diberi nama: %d)" % (i, len(terkumpul), diberi))

print("     selesai: %d dari %d punya nama" % (diberi, len(terkumpul)))

print()
print("  terkumpul: %d entri unik" % len(terkumpul))

# Simpan hasil mentah, supaya penggabungan bisa diulang tanpa mengambil ulang.
SIMPAN.parent.mkdir(parents=True, exist_ok=True)
with open(SIMPAN, "w", encoding="utf-8") as f:
    json.dump(list(terkumpul.values()), f, ensure_ascii=False, indent=1)
print("  disimpan: %s" % SIMPAN)
print()

# ── susun entri katalog ───────────────────────────────────────────────────
entri = []
for k in terkumpul.values():
    # Judul dari tag dan id: wallhaven tidak memberi judul, dan judul kosong
    # membuat katalog tidak bisa dicari.
    nama = k["tag"].replace("-", " ").title()
    entri.append({
        "title": "%s #%s" % (nama, (k["id"] or "?").upper()),
        "videoUrl": k["path"],
        "thumbnailUrl": k["thumb"],
        "license": "Wallhaven · ilustrasi anime (gambar statis)",
        "sourceUrl": k["page"],
        "category": "Mature 18+",
        "kind": "static",
        "author": "Wallhaven community",
        "animation": "",
        "resolution": k["res"],
    })

print("  %d entri siap ditambahkan" % len(entri))
print()
print("  contoh:")
for e in entri[:3]:
    print("     %-34s %s" % (e["title"][:34], e["resolution"]))
print()
