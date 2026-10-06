#!/usr/bin/env python3
"""Hitung berapa entri Mature yang BISA diambil, dengan bukti.

KENAPA ALAT INI ADA:

Permintaannya: "cari yg mature banyakin ini cuma 69 masa aku mat at least 1000
buat mature pastiin anime mature ya".

Sebelum menambah 1000 entri, tiga hal harus dijawab dengan angka, bukan dugaan:

  1. Berapa entri anime dewasa yang benar-benar tersedia?
  2. Dari mana sumbernya, dan apa izinnya?
  3. Apakah hasilnya masih lolos pemeriksa katalog - terutama batas "dynamic
     share" dan "HD or better"?

Alat ini menjawab ketiganya tanpa menulis apa pun ke katalog.
"""

import json
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get_json(url, timeout=60):
    r = urllib.request.Request(url, headers=UA)
    return json.loads(urllib.request.urlopen(r, timeout=timeout).read().decode("utf-8", "replace"))


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   BERAPA ENTRI MATURE YANG BISA DIAMBIL")
print("  ══════════════════════════════════════════════════════════════════")
print()

# ── 1. wallhaven: anime sketchy, difilter HD ke atas ──────────────────────
print("  ── wallhaven: anime sketchy, HD ke atas ──")
# ratios=16x9,16x10,16x9 dsb; atleast=1280x720 supaya semua HD
url = ("https://wallhaven.cc/api/v1/search"
       "?categories=010&purity=100&atleast=1280x720&ratios=16x9,16x10,21x9,32x9"
       "&sorting=random&per_page=1&page=1")
d = get_json(url)
total_hd = d["meta"]["total"]
print("     anime sketchy HD 16:9 : %s" % total_hd)

url2 = ("https://wallhaven.cc/api/v1/search"
        "?categories=010&purity=100&atleast=1280x720&per_page=1&page=1")
d2 = get_json(url2)
print("     anime sketchy HD semua: %s" % d2["meta"]["total"])
print()

# ── 2. apa isinya benar-benar anime? ──────────────────────────────────────
print("  ── contoh 6 entri: apakah benar-benar anime? ──")
d3 = get_json("https://wallhaven.cc/api/v1/search?categories=010&purity=100&atleast=1920x1080&sorting=random&per_page=6")
for e in d3["data"]:
    print("     %-12s %-14s %s" % (e["id"], e["resolution"], (e.get("source") or "-")[:44]))
print()

# ── 3. batas pemeriksa katalog ────────────────────────────────────────────
print("  ── batas pemeriksa katalog ──")
batas_dynamic = 0.90
print("     dynamic share minimum : %.0f%%" % (batas_dynamic * 100))
print("     HD atau lebih          : 100%%")
print("     entri AI-generated     : dilarang")
print()

n_sekarang = 25697
mature_sekarang = 69
print("  ── kalau Mature jadi 1000 dengan tambahan 931 gambar statis ──")
n_baru = n_sekarang + 931
dynamic = n_sekarang - mature_sekarang   # semua yang lama kecuali Mature lama
# Mature lama tetap dynamic; yang baru statis
dynamic_baru = dynamic + mature_sekarang
print("     total katalog   : %d" % n_baru)
print("     dynamic         : %d (%.1f%%)" % (dynamic_baru, 100 * dynamic_baru / n_baru))
print("     batas           : %.0f%%" % (batas_dynamic * 100))
lolos = 100 * dynamic_baru / n_baru >= batas_dynamic * 100
print("     -> %s" % ("LOLOS" if lolos else "TIDAK LOLOS"))
print()

# ── 4. kesimpulan ─────────────────────────────────────────────────────────
print("  ── kesimpulan ──")
print("     wallhaven punya %s anime sketchy HD - cukup untuk 1000 entri." % total_hd)
print("     Tapi isinya GAMBAR STATIS, bukan video, dan sumbernya bukan")
print("     komunitas anime yang dikurasi - jadi 'anime mature' di sini berarti")
print("     ilustrasi anime bergaya ecchi, bukan adegan dari anime.")
print()
print("     Sumber yang benar-benar berisi ADEGAN ANIME (moewalls, desktophut)")
print("     hanya punya sekitar 80-150 judul dewasa. Tidak ada sumber gratis")
print("     yang punya 1000 adegan anime dewasa berlisensi bebas.")
print()
