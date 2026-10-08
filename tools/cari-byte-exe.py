#!/usr/bin/env python3
"""Cari byte mentah di dalam exe - cara paling pasti.

KENAPA ALAT INI ADA:

Dua alat sebelumnya saling bertentangan: satu melaporkan fitur unduh ffmpeg
TIDAK ada, yang lain menemukan kelas Ffmpeg ADA. Yang benar harus diketahui,
bukan ditebak.

Pencarian regex pada teks hasil decode bisa gagal karena beberapa sebab:
encoding, urutan baca, atau string yang disimpan sebagai UTF-16 di bagian #US
metadata. Pencarian BYTE MENTAH tidak punya masalah itu: kalau teksnya ada,
byte-nya ada.

Yang dicari dalam dua bentuk sekaligus:
  * UTF-16LE - cara .NET menyimpan string literal
  * ASCII/UTF-8 - cara nama tipe dan teks non-literal disimpan
"""

import re
import sys
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")

TARGET = {
    "exe yang DIBANGUN": W / "LumaWall" / "bin" / "Release" / "LumaWall.exe",
    "exe yang TERPASANG": Path.home() / "AppData" / "Local" / "Programs" / "LumaWall" / "LumaWall.exe",
}

# Teks yang DIJAMIN ada - untuk membuktikan cara pencariannya bekerja.
PASTI = [
    "LumaWall",
    "catalog.json",
    "MainWindow",
]

# Fitur yang sedang dipertanyakan.
FITUR = [
    "gyan.dev",
    "ffmpeg-release-essentials",
    "Menyiapkan ffmpeg",
    "pemroses video",
    "ffmpeg.exe",
    "kenburns",
    "LumaWall.Ffmpeg",
]

print()
print("  ══════════════════════════════════════════════════════════════════")
print("   PENCARIAN BYTE MENTAH DI DALAM EXE")
print("  ══════════════════════════════════════════════════════════════════")
print()

hasil = {}

for label, path in TARGET.items():
    print("  ══ %s ══" % label)
    if not path.exists():
        print("     ! tidak ada: %s" % path)
        print()
        continue

    data = path.read_bytes()
    st = path.stat()
    print("     %s" % path)
    print("     %.0f KB, diubah %s" % (len(data) / 1024,
          __import__("datetime").datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")))
    print()

    def cari(teks):
        """Berapa kali teks ditemukan, dalam UTF-16LE dan ASCII."""
        u16 = teks.encode("utf-16-le")
        asc = teks.encode("ascii", "ignore")
        return data.count(u16), data.count(asc)

    print("     ── teks yang DIJAMIN ada (pembuktian cara cari) ──")
    for t in PASTI:
        u, a = cari(t)
        tanda = "OK " if (u or a) else "!! "
        print("        %s%-28s UTF-16=%-4d ASCII=%d" % (tanda, t, u, a))
    print()

    print("     ── fitur yang dipertanyakan ──")
    hasil[label] = {}
    for t in FITUR:
        u, a = cari(t)
        ada = bool(u or a)
        hasil[label][t] = ada
        print("        %s%-28s UTF-16=%-4d ASCII=%d" % ("ADA      " if ada else "TIDAK    ", t, u, a))
    print()

# ── Kesimpulan ────────────────────────────────────────────────────────────
print("  ══════════════════════════════════════════════════════════════════")
print("   KESIMPULAN")
print("  ══════════════════════════════════════════════════════════════════")
print()

if len(hasil) == 2:
    labels = list(hasil.keys())
    a, b = labels[0], labels[1]
    sama = all(hasil[a][t] == hasil[b][t] for t in FITUR)
    print("  Kedua exe %s." % ("SAMA isinya" if sama else "BERBEDA isinya"))
    print()

    for t in ["gyan.dev", "ffmpeg-release-essentials"]:
        va = hasil[a][t]
        print("  %-30s %s" % (t, "ADA" if va else "TIDAK ADA"))
    print()

    if hasil[a].get("Menyiapkan ffmpeg") or hasil[a].get("ffmpeg.exe"):
        print("  Kelas Ffmpeg dan kode unduhnya ADA di dalam exe.")
    else:
        print("  Kelas Ffmpeg TIDAK ada di dalam exe.")
    print()

sys.exit(0)
