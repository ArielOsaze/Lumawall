#!/usr/bin/env python3
"""Perbaiki judul entri Mature dari wallhaven supaya buktinya ikut terbawa.

KENAPA ALAT INI ADA:

Pemeriksa katalog menolak 391 entri Mature: "391 mature entries have nothing
that justifies them". 355 di antaranya dari wallhaven.

Sebabnya: pencarian per tag di wallhaven tidak mengembalikan tag gambarnya -
field "tags" tidak ada pada hasil pencarian. Jadi nama entri diambil dari kata
kunci yang DICARI, dan itu hanya menandai sebagian kecil gambar dengan benar:
gambar yang muncul pada pencarian "swimsuit" bisa saja judulnya tidak memuat
kata itu.

Pemeriksa mensyaratkan judulnya sendiri memuat kata yang membenarkan
kategorinya - dan itu benar, karena kalau tidak, tidak ada cara memeriksa
kategori itu setelah katalognya dibangun.

Jadi tag sebenarnya diambil dari halaman detail tiap gambar
(/wp-json... tidak berlaku di sini; wallhaven memakai /api/v1/w/{id}), lalu
judulnya disusun dari tag itu. Satu permintaan per entri, dengan jeda yang
diwajibkan wallhaven.

Hanya entri yang judulnya BELUM memuat kata pembenar yang diperbaiki - yang
sudah benar tidak perlu diambil ulang.
"""

import json
import re
import time
import urllib.request
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
JEDA = 1.5

# Kata yang membenarkan kategori Mature - sama dengan tools/check-catalog.py.
MATURE_WORDS = set("""nsfw ecchi hentai lewd sexy seductive sensual sultry provocative erotic
lingerie bikini swimsuit swimwear cleavage boudoir gravure pin-up pinup topless
undress busty voluptuous stripper nude naked milf panties nightgown negligee
corset garter thigh-high thigh-highs hot""".split())

# Tag wallhaven yang tidak menjelaskan apa pun, jadi tidak boleh dipakai
# sebagai satu-satunya pembenar.
TAG_LEMAH = {"anime", "anime girls", "1girl", "2girls", "girl", "girls",
             "female", "original", "artwork", "illustration"}

_terakhir = [0.0]


def get_json(url, timeout=60, percobaan=5):
    for i in range(percobaan):
        selang = time.time() - _terakhir[0]
        if selang < JEDA:
            time.sleep(JEDA - selang)
        try:
            r = urllib.request.Request(url, headers=UA)
            isi = urllib.request.urlopen(r, timeout=timeout).read().decode("utf-8", "replace")
            _terakhir[0] = time.time()
            return json.loads(isi)
        except Exception as e:
            _terakhir[0] = time.time()
            if "429" in str(e):
                time.sleep(20 + 15 * i)
                continue
            if i == percobaan - 1:
                raise
            time.sleep(3 * (i + 1))
    return None


def kata(teks):
    return set(re.split(r"[^a-z0-9]+", teks.lower())) - {""}


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MEMPERBAIKI JUDUL MATURE YANG TIDAK PUNYA DASAR")
print("  ══════════════════════════════════════════════════════════════════")
print()

katalog = json.load(open(CATALOG, encoding="utf-8"))
items = katalog if isinstance(katalog, list) else katalog.get("Items", [])
kunci = "Items" if isinstance(katalog, dict) and "Items" in katalog else None

mat = [e for e in items if e.get("category") == "Mature 18+"]
perlu = []
for e in mat:
    if not (kata(e.get("title", "") + " " + e.get("videoUrl", "")) & MATURE_WORDS):
        # Hanya yang dari wallhaven: yang dari moewalls tidak punya halaman
        # detail seperti ini.
        if "wallhaven" in (e.get("videoUrl", "") + e.get("license", "")).lower():
            perlu.append(e)

print("  mature seluruhnya : %d" % len(mat))
print("  perlu diperbaiki  : %d" % len(perlu))
print()

if not perlu:
    print("  tidak ada yang perlu diperbaiki")
    raise SystemExit(0)

berhasil = 0
gagal = 0
for i, e in enumerate(perlu):
    # id wallhaven ada di judul: "Tag - AB12CD".
    m = re.search(r"-\s*([A-Z0-9]{6})\s*$", e.get("title", ""))
    if not m:
        gagal += 1
        continue
    wid = m.group(1).lower()
    try:
        d = get_json("https://wallhaven.cc/api/v1/w/%s" % wid)
    except Exception:
        gagal += 1
        continue
    data = (d or {}).get("data") or {}
    tag = data.get("tags") or []
    if not tag:
        gagal += 1
        continue

    # Semua nama tag digabung, tag lemah dibuang. Judulnya harus memuat kata
    # pembenar, jadi tag yang menjelaskan (bikini, swimsuit, ...) harus ada.
    nama = [t.get("name", "").strip() for t in tag]
    nama = [n for n in nama if n and n.lower() not in TAG_LEMAH]
    if not nama:
        gagal += 1
        continue

    # Tiga tag pertama cukup untuk judul yang bisa dibaca, dan idnya
    # dipertahankan supaya entri ini tetap bisa ditelusuri.
    judul = "%s - %s" % (", ".join(nama[:3]).title(), wid.upper())

    # Hanya dipakai kalau judul barunya benar-benar punya dasar.
    if not (kata(judul) & MATURE_WORDS):
        # Kalau tidak, seluruh tag dipakai - salah satunya pasti menjelaskan.
        judul = "%s - %s" % (", ".join(nama).title(), wid.upper())
        if not (kata(judul) & MATURE_WORDS):
            gagal += 1
            continue

    e["title"] = judul
    berhasil += 1

    if i and i % 50 == 0:
        print("     %d / %d  (berhasil %d, gagal %d)" % (i, len(perlu), berhasil, gagal))

print()
print("  berhasil: %d" % berhasil)
print("  gagal   : %d" % gagal)
print()

if berhasil:
    if kunci:
        katalog[kunci] = items
        keluar = katalog
    else:
        keluar = items
    CATALOG.write_text(json.dumps(keluar, ensure_ascii=False, indent=1), encoding="utf-8")
    print("  ditulis: %s" % CATALOG)
    print()

# Periksa ulang
mat = [e for e in items if e.get("category") == "Mature 18+"]
sisa = [e for e in mat
        if not (kata(e.get("title", "") + " " + e.get("videoUrl", "")) & MATURE_WORDS)]
print("  Mature tanpa dasar sekarang: %d" % len(sisa))
for e in sisa[:10]:
    print("     %s" % e.get("title", "")[:68])
print()
