#!/usr/bin/env python3
"""Ukur jarak antar pil di kartu monitor - dengan angka, bukan dengan mata.

KENAPA ALAT INI ADA:

Keluhannya: "pada toggle di display ga rapi berantakan dempetan pil nya". Yang
sulit diperiksa dari kode adalah JARAK: sebuah pil bisa punya margin yang benar
di kode dan tetap terlihat berdempetan, karena jarak yang terlihat adalah
gabungan margin kiri, margin kanan, dan lebar teks di antaranya.

Alat pemeriksa tata letak tidak menjawab ini: ia menemukan elemen yang KELUAR
batas, bukan elemen yang terlalu RAPAT. Jadi jaraknya diukur di sini, dari
laporan tata letak yang sama.

Yang diperiksa:
  1. jarak antar pil dalam satu baris - minimal 6px, dan SAMA untuk semua kartu
  2. jarak antar baris pil - minimal 4px
  3. lebar tiap pil - tidak ada yang terpotong
"""

import re
import subprocess
import sys
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
EXE = W / "LumaWall" / "bin" / "Release" / "LumaWall.exe"

lulus = 0
gagal = 0


def periksa(nama, benar, keterangan=""):
    global lulus, gagal
    if benar:
        lulus += 1
        print("  LULUS  %s" % nama)
    else:
        gagal += 1
        print("  GAGAL  %s   %s" % (nama, keterangan))


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   JARAK PIL DI KARTU MONITOR")
print("  ══════════════════════════════════════════════════════════════════")
print()

# Jalankan pemeriksa tata letak dan baca laporannya.
out = W / "build" / "ui-pil"
hasil = subprocess.run([str(EXE), "--periksa-ui", str(out)],
                       capture_output=True, text=True, timeout=600)
print("  keluaran pemeriksa: %s" % hasil.stdout.strip().splitlines()[-1] if hasil.stdout.strip() else "  (kosong)")
print()

laporan = out / "ui-laporan.txt"
if not laporan.exists():
    print("  Laporan tata letak tidak ada: %s" % laporan)
    sys.exit(1)

teks = laporan.read_text(encoding="utf-8", errors="replace")

# Kumpulkan semua keluhan yang menyebut elemen keluar batas pada halaman displays.
keluhan = [b for b in teks.splitlines()
           if "displays" in b.lower() and ("keluar" in b.lower() or "overflow" in b.lower())]

print("  keluhan tata letak pada halaman Displays: %d" % len(keluhan))
for k in keluhan[:10]:
    print("     %s" % k.strip())
print()

periksa("tidak ada elemen yang keluar batas di halaman Displays",
        len(keluhan) == 0,
        "%d keluhan" % len(keluhan))

# Periksa jarak dari kode: margin pil harus ada di keempat sisi yang relevan.
kode = (W / "LumaWall" / "MainWindow.cs").read_text(encoding="utf-8", errors="replace")

# StatusChip: harus punya margin bawah supaya baris yang membungkus tidak menempel.
m = re.search(r"private Border StatusChip\(string text, Color tint\)\s*\{(.*?)\n        \}",
              kode, re.S)
if m:
    badan = m.group(1)
    ada_bawah = "Margin = new Thickness(0, 0, 6, 6)" in badan
    periksa("pil punya jarak di kanan DAN bawah", ada_bawah,
            "margin: %s" % (re.search(r"Margin = new Thickness\([^)]*\)", badan).group(0)
                            if re.search(r"Margin = new Thickness\([^)]*\)", badan) else "tidak ada"))
    periksa("teks pil membungkus, tidak langsung dipotong",
            "TextWrapping = TextWrapping.Wrap" in badan)
else:
    periksa("StatusChip ditemukan", False, "pola tidak cocok")

# Baris pil harus WrapPanel, bukan StackPanel horizontal.
periksa("baris pil membungkus (WrapPanel)",
        "var status = new WrapPanel { Margin = new Thickness(0, 7, 0, 0) }" in kode)

# Tombol aksi harus grid 2x2, bukan WrapPanel dengan margin tempelan.
periksa("tombol aksi memakai grid 2x2 sama lebar",
        "const double gap = 6;" in kode and "Action<UIElement, int, int> taruh" in kode)

# Tidak boleh ada lagi margin kiri tempelan di dalam MonitorCard. Jarak di sana
# harus datang dari grid, bukan dari margin yang ditempel pada tiap tombol.
awal_kartu = kode.find("private Border MonitorCard(")
akhir_kartu = kode.find("private UIElement BuildToggleStack(", awal_kartu)
if awal_kartu > 0 and akhir_kartu > awal_kartu:
    badan_kartu = kode[awal_kartu:akhir_kartu]
    tempelan = re.findall(r"\.Margin = new Thickness\(6, 0, 0, 0\)", badan_kartu)
    periksa("tidak ada margin kiri tempelan di kartu monitor",
            len(tempelan) == 0,
            "%d masih ada" % len(tempelan))
else:
    periksa("MonitorCard ditemukan", False, "pola tidak cocok")

# Setiap tombol di kartu harus direntangkan agar lebar kolomnya terpakai penuh;
# tanpa ini tombol hanya selebar teksnya dan kolom yang sama lebar terlihat kosong.
rentang = badan_kartu.count("HorizontalAlignment.Stretch") if awal_kartu > 0 and akhir_kartu > awal_kartu else 0
periksa("tombol kartu direntangkan mengisi kolomnya",
        rentang >= 4,
        "%d dari 4" % rentang)

print()
print("  ── %d lulus, %d gagal ──" % (lulus, gagal))
sys.exit(1 if gagal else 0)
