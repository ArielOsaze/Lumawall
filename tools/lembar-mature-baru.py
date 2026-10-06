#!/usr/bin/env python3
"""Buat lembar kontak dari entri Mature baru, supaya isinya bisa DILIHAT.

KENAPA ALAT INI ADA:

Pemeriksa katalog memeriksa judul, tag, dan URL - bukan gambarnya. Judul yang
benar tetap bisa menempel pada gambar yang salah kategori, dan permintaannya
eksplisit: "pastiin anime mature ya" dan "gapapa yg bnr bnr mature asal ga
nyasar katgori lainnya".

Satu-satunya cara memastikan isinya adalah melihatnya. Alat ini mengunduh
thumbnail sejumlah entri Mature, menyusunnya jadi satu lembar, dan menuliskan
judulnya di bawah tiap gambar - lalu lembar itu diperiksa dengan mata.

Thumbnail dipakai, bukan berkas penuh: yang diperiksa isinya, bukan
resolusinya, dan 40 gambar penuh akan memakan ratusan megabita.
"""

import io
import json
import random
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"
KELUAR = W / "build" / "lembar-mature-baru.jpg"

JUMLAH = 24
KOLOM = 6
LEBAR = 260
TINGGI = 146
BARIS_JUDUL = 22

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def unduh(e):
    try:
        r = urllib.request.Request(e["thumbnailUrl"], headers=UA)
        return e, urllib.request.urlopen(r, timeout=40).read()
    except Exception:
        return e, None


print()
print("  ══ lembar kontak Mature ══")
print()

d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])
mat = [e for e in items
       if e.get("category") == "Mature 18+"
       and "wallhaven" in (e.get("license", "") + e.get("videoUrl", "")).lower()]
print("  entri wallhaven di Mature: %d" % len(mat))

random.seed(11)
pilih = random.sample(mat, min(JUMLAH, len(mat)))
print("  diambil %d sampel acak" % len(pilih))
print()

with ThreadPoolExecutor(max_workers=8) as ex:
    hasil = list(ex.map(unduh, pilih))

berhasil = [(e, b) for e, b in hasil if b]
print("  thumbnail terunduh: %d / %d" % (len(berhasil), len(pilih)))
if not berhasil:
    print("  ! tidak ada yang terunduh")
    sys.exit(1)

from PIL import Image, ImageDraw

baris = (len(berhasil) + KOLOM - 1) // KOLOM
lebar_lembar = KOLOM * LEBAR
tinggi_lembar = baris * (TINGGI + BARIS_JUDUL)
lembar = Image.new("RGB", (lebar_lembar, tinggi_lembar), (16, 16, 20))
gambar = ImageDraw.Draw(lembar)

for i, (e, data) in enumerate(berhasil):
    kol = i % KOLOM
    bar = i // KOLOM
    x = kol * LEBAR
    y = bar * (TINGGI + BARIS_JUDUL)
    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
        # Dipotong tengah supaya semua sel sama besar.
        rasio = LEBAR / TINGGI
        w, h = im.size
        if w / h > rasio:
            baru = int(h * rasio)
            im = im.crop(((w - baru) // 2, 0, (w + baru) // 2, h))
        else:
            baru = int(w / rasio)
            im = im.crop((0, (h - baru) // 2, w, (h + baru) // 2))
        im = im.resize((LEBAR, TINGGI), Image.LANCZOS)
        lembar.paste(im, (x, y))
    except Exception:
        gambar.rectangle([x, y, x + LEBAR, y + TINGGI], fill=(40, 40, 48))
    judul = e.get("title", "")[:34]
    gambar.text((x + 4, y + TINGGI + 5), judul, fill=(210, 210, 220))

KELUAR.parent.mkdir(parents=True, exist_ok=True)
lembar.save(KELUAR, quality=88)
print()
print("  disimpan: %s  (%dx%d)" % (KELUAR, lebar_lembar, tinggi_lembar))
print()
