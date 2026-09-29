#!/usr/bin/env python3
"""Pasang pemasangan rute jembatan LumaWall ke server.js di server NexShop.

Dijalankan DI SERVER, bukan dari mesin lokal. Skrip ini menambahkan dua baris
yang belum ada, dan menolak berjalan kalau polanya tidak ditemukan - lebih baik
berhenti daripada menulis ke berkas yang salah tempat.

Kenapa tidak memakai sed atau regex yang rumit: baris yang dicari punya
komentar di ujungnya, dan regex yang "kira-kira cocok" adalah cara paling cepat
merusak berkas konfigurasi server yang sedang melayani pengunjung.

Pemakaian (di server):
  python3 /tmp/pasang-rute.py /var/www/NEXSHOP_ALL/nexshop-backend/server.js
"""
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("  GAGAL: berikan path server.js")
    sys.exit(1)

p = Path(sys.argv[1])
if not p.exists():
    print("  GAGAL: berkas tidak ada:", p)
    sys.exit(1)

t = p.read_text(encoding="utf-8")
asli = t

BARIS_REQUIRE_ACUAN = 'const akuntuntasRoutes = require("./routes/akuntuntasRoutes");'
BARIS_REQUIRE_BARU = 'const lumawallRoutes = require("./routes/lumawallRoutes"); // jembatan pembayaran LumaWall'

BARIS_USE_ACUAN = 'app.use("/api/akuntuntas", akuntuntasRoutes);'
BARIS_USE_BARU = 'app.use("/api/lumawall", lumawallRoutes); // jembatan pembayaran LumaWall'

# ── 1. require ──────────────────────────────────────────────────────────────
if "lumawallRoutes" in t:
    print("  require sudah ada")
else:
    baris = t.split("\n")
    ketemu = False
    for i, b in enumerate(baris):
        if b.strip().startswith(BARIS_REQUIRE_ACUAN):
            baris.insert(i + 1, BARIS_REQUIRE_BARU)
            ketemu = True
            break
    if not ketemu:
        print("  GAGAL: baris require akuntuntasRoutes tidak ditemukan")
        sys.exit(1)
    t = "\n".join(baris)
    print("  require ditambahkan")

# ── 2. pemasangan rute ──────────────────────────────────────────────────────
if 'app.use("/api/lumawall"' in t:
    print("  rute sudah ada")
else:
    baris = t.split("\n")
    ketemu = False
    for i, b in enumerate(baris):
        if b.strip().startswith(BARIS_USE_ACUAN):
            baris.insert(i + 1, BARIS_USE_BARU)
            ketemu = True
            break
    if not ketemu:
        print("  GAGAL: baris app.use akuntuntas tidak ditemukan")
        sys.exit(1)
    t = "\n".join(baris)
    print("  rute ditambahkan")

if t != asli:
    # Salinan cadangan sebelum menulis. Kalau ada yang salah, berkas lama masih
    # ada dan pemulihannya satu perintah.
    cadangan = p.with_suffix(".js.bak-lumawall")
    cadangan.write_text(asli, encoding="utf-8")
    p.write_text(t, encoding="utf-8")
    print("  server.js diperbarui (cadangan: %s)" % cadangan.name)
else:
    print("  server.js tidak berubah")
