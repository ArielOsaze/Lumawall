#!/usr/bin/env python3
"""Urutan yang benar untuk membangun ulang kategori Mature.

KENAPA BERKAS INI ADA:

Dua alat Mature menulis ke LumaWall/catalog.json, dan keduanya membaca berkas
itu saat dijalankan. Kalau dijalankan bersamaan, yang selesai terakhir menimpa
hasil yang lain:

    benahi-judul-mature.py    membaca katalog, 355 permintaan x 1,5 detik
    benahi-mature-moewalls.py membaca katalog yang SAMA, menulis 35 perubahan

Kalau yang pertama selesai terakhir, 35 perubahan itu hilang - dan itu pernah
terjadi. Urutannya karena itu harus berurutan, bukan bersamaan.

Alat ini menjalankannya berurutan dan memeriksa hasilnya di akhir.
"""

import subprocess
import sys
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")

LANGKAH = [
    ("tools/benahi-judul-mature.py",
     "355 judul wallhaven diambil tag aslinya (paling lama, ~9 menit)"),
    ("tools/benahi-mature-moewalls.py",
     "entri moewalls tanpa dasar dipindah ke Anime Girls"),
]

print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MEMBANGUN ULANG KATEGORI MATURE (BERURUTAN)")
print("  ══════════════════════════════════════════════════════════════════")
print()

for i, (alat, keterangan) in enumerate(LANGKAH, 1):
    print("  [%d/%d] %s" % (i, len(LANGKAH), alat))
    print("        %s" % keterangan)
    r = subprocess.run([sys.executable, str(W / alat)],
                       cwd=str(W), capture_output=True, text=True,
                       timeout=3600, errors="replace")
    # Hanya baris ringkasan yang ditampilkan.
    for baris in (r.stdout or "").splitlines():
        b = baris.strip()
        if any(k in b for k in ("berhasil:", "gagal", "dipindah", "dibenahi",
                                "Mature sekarang", "masih tanpa dasar",
                                "tanpa dasar", "ditulis")):
            print("        %s" % b)
    if r.returncode != 0:
        print("        ! gagal (kode %d)" % r.returncode)
        print("        %s" % (r.stderr or "")[-400:])
        sys.exit(1)
    print()

# Pemeriksaan akhir, dijalankan sebagai proses terpisah.
print("  [akhir] tools/check-catalog.py --no-network")
r = subprocess.run([sys.executable, str(W / "tools/check-catalog.py"), "--no-network"],
                   cwd=str(W), capture_output=True, text=True,
                   timeout=1800, errors="replace")
for baris in (r.stdout or "").splitlines():
    b = baris.strip()
    if any(k in b for k in ("entries:", "mature entries:", "reviewed", "keyword",
                            "dynamic:", "duplicates", "OK", "FAIL", "justifies")):
        print("        %s" % b)
print()
print("  selesai")
print()
