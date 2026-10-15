#!/usr/bin/env python3
"""Buktikan alat pemeriksa thumbnail bisa MENDETEKSI yang rusak.

KENAPA BERKAS INI ADA:

Alat pemeriksa yang selalu berkata "semua beres" lebih buruk daripada tidak ada
alat sama sekali - dan itu sudah terjadi di proyek ini: pemeriksa thumbnail yang
hanya melihat berkas katalog melaporkan "0 kosong" sementara pengguna masih
melihat banyak gambar rusak.

Jadi sebelum 26 ribu alamat diuji, alatnya harus dibuktikan bisa:
  1. Menyatakan gambar SEHAT sebagai sehat (tidak menuduh yang baik)
  2. Menyatakan gambar RUSAK sebagai rusak (tidak meloloskan yang buruk)

Kasus uji sengaja memakai alamat yang sudah diketahui jawabannya:
  * gambar yang pasti ada di situs LumaWall      -> harus OK
  * alamat yang pasti tidak ada (404)            -> harus HILANG/RUSAK
  * alamat yang bukan gambar (halaman HTML)      -> harus RUSAK
  * domain yang tidak ada                        -> harus GAGAL
  * alamat kosong                                -> harus KOSONG
"""

import importlib.util
import sys
from pathlib import Path

# Muat alat utama langsung dari berkasnya.
#
# import_module() tidak bisa dipakai di sini: nama berkasnya memakai tanda
# hubung ("periksa-semua-thumbnail.py"), dan tanda hubung bukan karakter yang
# sah untuk nama modul - Python menerjemahkannya menjadi "periksa_semua_thumbnail"
# lalu gagal menemukannya. Pemuat berbasis lokasi berkas tidak peduli pada nama.
_lokasi = Path(__file__).parent / "periksa-semua-thumbnail.py"
_spec = importlib.util.spec_from_file_location("periksa_thumb", _lokasi)
modul = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(modul)
periksa = modul.periksa

KASUS = [
    # (alamat, keadaan yang diharapkan, keterangan)
    ("https://lumawall.xinet.id/assets/thumbs/anime-girl-riding-motorcycle-in-the-desert-live-wallpape.jpg",
     "OK", "thumbnail asli yang sudah terbukti ada (HTTP 200, image/jpeg)"),

    ("https://lumawall.xinet.id/tidak-ada-gambar-ini-xyz.jpg",
     "HILANG", "alamat yang pasti tidak ada"),

    ("https://lumawall.xinet.id/",
     "RUSAK", "halaman HTML, bukan berkas gambar"),

    ("https://domain-yang-tidak-pernah-ada-xyz123.invalid/gambar.jpg",
     "GAGAL", "domain tidak ada"),

    ("", "KOSONG", "alamat kosong"),

    ("https://lumawall.xinet.id/assets/thumbs/",
     "RUSAK", "direktori, bukan berkas gambar"),
]

print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MEMBUKTIKAN ALAT PEMERIKSA THUMBNAIL BEKERJA")
print("  ══════════════════════════════════════════════════════════════════")
print()

benar = 0
for alamat, diharap, ket in KASUS:
    keadaan, keterangan, ukuran = periksa(alamat)
    # HILANG dan RUSAK sama-sama berarti "tidak akan tampil" - yang penting
    # alatnya tidak menyebutnya OK.
    if diharap in ("HILANG", "RUSAK"):
        lulus = keadaan in ("HILANG", "RUSAK", "GAGAL", "DITOLAK")
    else:
        lulus = keadaan == diharap

    print("  %s %-42s" % ("LULUS" if lulus else "GAGAL", ket))
    print("        alamat   : %s" % (alamat[:78] or "(kosong)"))
    print("        diharap  : %s" % diharap)
    print("        hasil    : %s (%s)" % (keadaan, keterangan))
    print()
    if lulus:
        benar += 1

print("  ══════════════════════════════════════════════════════════════════")
print("   %d dari %d kasus lulus" % (benar, len(KASUS)))
if benar == len(KASUS):
    print("   Alat ini terbukti bisa membedakan gambar sehat dan gambar rusak.")
    print("   Laporannya bisa dipercaya.")
else:
    print("   Alat ini BELUM bisa dipercaya - perbaiki dulu sebelum dipakai.")
print("  ══════════════════════════════════════════════════════════════════")
print()

sys.exit(0 if benar == len(KASUS) else 1)
