#!/usr/bin/env python3
"""Periksa dengan MATA kandidat video Mature sebelum dimasukkan.

KENAPA ALAT INI ADA:

Judul tidak cukup untuk memutuskan. Dua kandidat yang lolos saringan kata
jelas salah begitu dibaca:

    sexy-bear-dance-live-walpaper   -> beruang, bukan manusia
    sexy-mbw-m4-hd-live-wallpaper   -> mobil BMW M4

Saringan kata tidak bisa menangkap itu: "sexy" ada di judulnya, dan "bear"
serta "m4" tidak ada di daftar penolak. Yang bisa memutuskan hanya gambarnya.

Alat ini mengunduh thumbnail tiap kandidat, menyusunnya jadi satu lembar
dengan nomor dan judulnya, lalu lembarnya diperiksa dengan mata. Yang lolos
saja yang dimasukkan ke katalog - permintaannya tegas: "gapapa yg bnr bnr
mature asal ga nyasar katgori lainnya".
"""

import io
import json
import urllib.request
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
SUMBER = W / "build" / "mature-video-baru.json"
KELUAR = W / "build" / "lembar-video-baru.jpg"

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

print()
print("  ══ lembar periksa kandidat video ══")
print()

kandidat = json.load(open(SUMBER, encoding="utf-8"))
print("  kandidat: %d" % len(kandidat))
print()

# Thumbnail: kalau tidak ada, coba dari halamannya.
def unduh(v):
    t = (v.get("thumbnailUrl") or "").strip()
    if not t:
        return None
    try:
        r = urllib.request.Request(t, headers=UA)
        return urllib.request.urlopen(r, timeout=40).read()
    except Exception:
        return None


from PIL import Image, ImageDraw

LEBAR, TINGGI = 300, 169
BARIS_JUDUL = 30
KOLOM = 3

items = list(kandidat.items())
gambar_ok = []
for i, (slug, v) in enumerate(items, 1):
    b = unduh(v)
    gambar_ok.append((i, slug, v, b))
    print("     %2d. %-52s %s" % (i, slug[:52], "ada" if b else "TIDAK ADA"))

baris = (len(gambar_ok) + KOLOM - 1) // KOLOM
lembar = Image.new("RGB", (KOLOM * LEBAR, baris * (TINGGI + BARIS_JUDUL)), (16, 16, 20))
g = ImageDraw.Draw(lembar)

for n, (i, slug, v, b) in enumerate(gambar_ok):
    kol = n % KOLOM
    bar = n // KOLOM
    x = kol * LEBAR
    y = bar * (TINGGI + BARIS_JUDUL)

    if b:
        try:
            im = Image.open(io.BytesIO(b)).convert("RGB")
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
            g.rectangle([x, y, x + LEBAR, y + TINGGI], fill=(40, 40, 48))
    else:
        g.rectangle([x, y, x + LEBAR, y + TINGGI], fill=(40, 40, 48))

    g.text((x + 5, y + TINGGI + 4), "%d. %s" % (i, v.get("title", "")[:40]), fill=(220, 220, 230))
    g.text((x + 5, y + TINGGI + 16), slug[:42], fill=(140, 140, 155))

KELUAR.parent.mkdir(parents=True, exist_ok=True)
lembar.save(KELUAR, quality=88)
print()
print("  disimpan: %s  (%dx%d)" % (KELUAR, lembar.width, lembar.height))
print()
print("  periksa lembarnya: mana yang benar-benar manusia/anime dalam pakaian")
print("  renang atau adegan sugestif, dan mana yang bukan.")
print()
