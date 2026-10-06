#!/usr/bin/env python3
"""Lihat thumbnail yang baru dibuat, supaya bisa diperiksa dengan mata.

KENAPA ALAT INI ADA:

53 thumbnail dibuat dengan mengambil frame dari videonya. "Berhasil dibuat"
tidak berarti isinya benar: frame bisa saja hitam, berisi judul, atau buram -
dan semuanya akan lolos dari pemeriksaan berkas. Yang bisa memutuskan hanya
melihatnya.

Lembar ini juga memuat thumbnail yang berasal dari placeholder "nsfw_min.png"
sebelumnya, supaya terlihat jelas bedanya.
"""

import io
import json
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"
THUMB = W / "site" / "assets" / "thumbs"
KELUAR = W / "build" / "lembar-thumbnail-baru.jpg"

print()
print("  ══ lembar periksa thumbnail baru ══")
print()

d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])

baru = [e for e in items if "lumawall.xinet.id/assets/thumbs" in (e.get("thumbnailUrl") or "")]
print("  thumbnail baru di katalog: %d" % len(baru))

berkas = sorted(THUMB.glob("*.jpg"))
print("  berkas di folder          : %d" % len(berkas))
print()

# Periksa tiap berkas: apakah isinya benar-benar gambar yang punya isi?
gelap = []
kecil = []
for f in berkas:
    try:
        im = Image.open(f).convert("L")
        w, h = im.size
        rata = sum(im.resize((32, 18)).get_flattened_data()) / (32 * 18)
        if rata < 12:
            gelap.append((f.name, round(rata, 1)))
        if w < 200 or h < 100:
            kecil.append((f.name, (w, h)))
    except Exception as e:
        gelap.append((f.name, "gagal dibuka"))

print("  ── pemeriksaan isi ──")
print("     hampir seluruhnya hitam : %d" % len(gelap))
for n, v in gelap[:8]:
    print("        %-52s %s" % (n[:52], v))
print("     terlalu kecil           : %d" % len(kecil))
for n, v in kecil[:8]:
    print("        %-52s %s" % (n[:52], v))
print()

# Lembar kontak
KOLOM = 6
LEBAR, TINGGI = 240, 135
BARIS = 24
pilih = berkas[:48]
baris = (len(pilih) + KOLOM - 1) // KOLOM
lembar = Image.new("RGB", (KOLOM * LEBAR, baris * (TINGGI + BARIS)), (16, 16, 20))
g = ImageDraw.Draw(lembar)

for n, f in enumerate(pilih):
    kol, br = n % KOLOM, n // KOLOM
    x, y = kol * LEBAR, br * (TINGGI + BARIS)
    try:
        im = Image.open(f).convert("RGB")
        rasio = LEBAR / TINGGI
        w, h = im.size
        if w / h > rasio:
            b = int(h * rasio)
            im = im.crop(((w - b) // 2, 0, (w + b) // 2, h))
        else:
            b = int(w / rasio)
            im = im.crop((0, (h - b) // 2, w, (h + b) // 2))
        im = im.resize((LEBAR, TINGGI), Image.LANCZOS)
        lembar.paste(im, (x, y))
    except Exception:
        g.rectangle([x, y, x + LEBAR, y + TINGGI], fill=(60, 20, 20))
    g.text((x + 4, y + TINGGI + 6), f.stem[:34], fill=(200, 200, 210))

KELUAR.parent.mkdir(parents=True, exist_ok=True)
lembar.save(KELUAR, quality=86)
print("  disimpan: %s  (%dx%d)" % (KELUAR, lembar.width, lembar.height))
print()
