#!/usr/bin/env python3
"""Bersihkan kategori Mature dari judul yang tidak aman dan tanpa dasar.

KENAPA ALAT INI ADA:

Setelah 332 judul Mature dibenahi dari tag asli wallhaven, pemeriksa katalog
menemukan dua masalah baru:

  1. 71 judul tidak aman, contoh "Blue Archive, Sunglasses, Ajitani Hifumi".

     Judul itu dibentuk dari tag wallhaven, dan salah satu tagnya adalah nama
     serial yang tokohnya dikodekan sebagai anak sekolah. UNSAFE_TITLE menolak
     "blue archive" - dan penolakan itu benar: seri itu tidak boleh ada di
     kategori Mature, apa pun gambarnya.

  2. 23 judul tanpa dasar, contoh "beach - OGJO3M".

     Tag asli gambar itu hanya "beach", yang tidak termasuk kata pembenar
     Mature. Artinya gambar itu memang bukan konten dewasa - hanya pantai.

Keduanya TIDAK diperbaiki dengan menambah kata, tetapi dengan mengeluarkan
entri itu dari kategori Mature. Entri yang aman dipindahkan ke Anime Girls;
entri yang judulnya menyebut tokoh di bawah umur dibuang dari katalog sama
sekali, karena katalognya bisa dibuka siapa saja.

Alat ini idempoten: menjalankannya dua kali tidak mengubah apa pun pada
jalannya yang kedua.
"""

import json
import re
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"

MATURE_WORDS = set("""nsfw ecchi hentai lewd sexy seductive sensual sultry provocative erotic
lingerie bikini swimsuit swimwear cleavage boudoir gravure pin-up pinup topless
undress busty voluptuous stripper nude naked milf panties nightgown negligee
corset garter thigh-high thigh-highs hot""".split())

# Sama dengan UNSAFE_TITLE di tools/check-catalog.py.
UNSAFE_TITLE = re.compile(
    r"\b(loli|lolita|child|kid|little girl|baby|daughter|schoolgirl|school girl|student"
    r"|teen|anya|kanna|pokemon|nezuko|nahida|klee|qiqi|yaoyao|diona|ibuki|blue archive"
    r"|juvenile)\b", re.I)


def kata(teks):
    return set(re.split(r"[^a-z0-9]+", teks.lower())) - {""}


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MEMBERSIHKAN KATEGORI MATURE")
print("  ══════════════════════════════════════════════════════════════════")
print()

katalog = json.load(open(CATALOG, encoding="utf-8"))
items = katalog if isinstance(katalog, list) else katalog.get("Items", [])
kunci = "Items" if isinstance(katalog, dict) and "Items" in katalog else None

sebelum = sum(1 for e in items if e.get("category") == "Mature 18+")
print("  Mature sebelum: %d" % sebelum)
print()

keluar = []
dibuang = []
dipindah = []
for e in items:
    if e.get("category") != "Mature 18+":
        keluar.append(e)
        continue

    judul = e.get("title", "")

    # 1. tokoh di bawah umur: dibuang dari katalog sama sekali.
    if UNSAFE_TITLE.search(judul):
        dibuang.append(e)
        continue

    # 2. tanpa dasar: dipindahkan ke Anime Girls.
    if not (kata(judul + " " + e.get("videoUrl", "")) & MATURE_WORDS):
        e["category"] = "Anime Girls"
        dipindah.append(e)
        keluar.append(e)
        continue

    keluar.append(e)

print("  dibuang dari katalog (judul tidak aman) : %d" % len(dibuang))
for e in dibuang[:8]:
    print("     %s" % e.get("title", "")[:66])
print()
print("  dipindah ke Anime Girls (tanpa dasar)   : %d" % len(dipindah))
for e in dipindah[:8]:
    print("     %s" % e.get("title", "")[:66])
print()

sesudah = sum(1 for e in keluar if e.get("category") == "Mature 18+")
print("  Mature sesudah: %d" % sesudah)
print("  katalog        : %d entri" % len(keluar))
print()

if len(keluar) != len(items):
    if kunci:
        katalog[kunci] = keluar
        out = katalog
    else:
        out = keluar
    CATALOG.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("  ditulis: %s" % CATALOG)
else:
    print("  tidak ada perubahan")

# Periksa ulang
mat = [e for e in keluar if e.get("category") == "Mature 18+"]
aman_salah = [e for e in mat if UNSAFE_TITLE.search(e.get("title", ""))]
tanpa = [e for e in mat if not (kata(e.get("title", "") + " " + e.get("videoUrl", "")) & MATURE_WORDS)]
print()
print("  judul tidak aman tersisa : %d" % len(aman_salah))
print("  tanpa dasar tersisa       : %d" % len(tanpa))
print()
