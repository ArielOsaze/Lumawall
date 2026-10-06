#!/usr/bin/env python3
"""Buktikan ffmpeg bisa diperoleh di PC yang tidak punya ffmpeg.

KENAPA ALAT INI ADA:

Bug yang diperbaiki: tiga fitur aplikasi memanggil ffmpeg, dan di PC pembeli
ffmpeg tidak ada di mana pun - sehingga fitur perkecil video (perbaikan decode
4.5.20.0), pembatas FPS, dan kenburns GAGAL DIAM-DIAM. Di mesin pengembang
semuanya tampak baik karena ffmpeg dipasang lewat WinGet dan ada di PATH.

Menguji "kodenya dikompilasi" tidak membuktikan apa pun di sini. Yang harus
dibuktikan:

  1. Alamat unduhannya masih hidup dan benar-benar mengembalikan arsip zip.
  2. ffmpeg.exe benar-benar bisa dikeluarkan dari arsip itu.
  3. Hasilnya bisa dijalankan dan melaporkan versinya.

Poin 2 diuji dengan membaca arsipnya memakai cara yang SAMA dengan Ffmpeg.cs -
pemindai zip yang membaca daftar isinya dari belakang, karena .NET Framework
4.8 di sini tidak memakai ZipArchive.

Kalau salah satu langkah gagal, fitur itu tidak akan bekerja di PC pembeli,
dan itu harus diketahui SEKARANG, bukan setelah dirilis.
"""

import io
import re
import struct
import sys
import urllib.request
import zipfile
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
SUMBER = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

UA = {"User-Agent": "LumaWall/1.0"}

print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MEMBUKTIKAN FFMPEG BISA DIPEROLEH DI PC TANPA FFMPEG")
print("  ══════════════════════════════════════════════════════════════════")
print()

# ── 1. Alamat unduhan masih hidup? ────────────────────────────────────────
print("  ── 1. alamat unduhan ──")
print("     %s" % SUMBER)
try:
    r = urllib.request.Request(SUMBER, headers=UA, method="HEAD")
    with urllib.request.urlopen(r, timeout=60) as f:
        ukuran = int(f.headers.get("Content-Length") or 0)
        tipe = f.headers.get("Content-Type") or "?"
        print("     status  : %d" % f.status)
        print("     ukuran  : %.1f MB" % (ukuran / 1048576))
        print("     tipe    : %s" % tipe)
        if f.status != 200:
            print("     ! TIDAK OK")
            sys.exit(1)
except Exception as e:
    print("     ! GAGAL: %s" % str(e)[:90])
    print("       Fitur kenburns dan perkecil video tidak akan bekerja di PC pembeli.")
    sys.exit(1)
print()

# ── 2. Unduh dan baca isinya ──────────────────────────────────────────────
print("  ── 2. mengunduh dan membaca isi arsip ──")
tujuan = W / "build" / "uji-ffmpeg.zip"
tujuan.parent.mkdir(parents=True, exist_ok=True)

if tujuan.exists() and tujuan.stat().st_size > 10_000_000:
    print("     sudah ada dari uji sebelumnya (%.1f MB)" % (tujuan.stat().st_size / 1048576))
else:
    print("     mengunduh… (bisa 1-3 menit)")
    try:
        r = urllib.request.Request(SUMBER, headers=UA)
        with urllib.request.urlopen(r, timeout=600) as f, open(tujuan, "wb") as keluar:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                keluar.write(b)
        print("     terunduh: %.1f MB" % (tujuan.stat().st_size / 1048576))
    except Exception as e:
        print("     ! GAGAL mengunduh: %s" % str(e)[:90])
        sys.exit(1)
print()

with zipfile.ZipFile(tujuan) as z:
    semua = z.namelist()
    ff = [n for n in semua if n.endswith("/ffmpeg.exe") or n == "ffmpeg.exe"]
    fp = [n for n in semua if n.endswith("/ffprobe.exe") or n == "ffprobe.exe"]

print("     isi arsip: %d berkas" % len(semua))
print("     ffmpeg.exe  : %s" % (ff[0] if ff else "TIDAK ADA"))
print("     ffprobe.exe : %s" % (fp[0] if fp else "TIDAK ADA"))
if not ff:
    print()
    print("     ! ffmpeg.exe tidak ada di dalam arsip.")
    print("       Ffmpeg.cs akan gagal mengeluarkannya.")
    sys.exit(1)
print()

# ── 3. Uji pemindai zip Ffmpeg.cs ─────────────────────────────────────────
print("  ── 3. pemindai zip Ffmpeg.cs (bukan pustaka Python) ──")
#
# Ffmpeg.cs membaca daftar isi zip dari belakang, mencari tanda 0x06054b50
# (End of Central Directory), lalu menelusuri entri untuk menemukan nama yang
# dicocokkan di AKHIR nama - karena nama di arsip memuat folder versinya.
data = tujuan.read_bytes()

def cari_zip(data, nama):
    """Cara yang sama dengan Ffmpeg.BacaZip."""
    panjang = len(data)
    batas = max(0, panjang - 66000)
    eocd = -1
    for i in range(panjang - 22, batas - 1, -1):
        if data[i:i+4] == b"PK\x05\x06":
            eocd = i
            break
    if eocd < 0:
        return None, "tanda End of Central Directory tidak ditemukan"

    jumlah = struct.unpack_from("<H", data, eocd + 10)[0]
    mulai = struct.unpack_from("<I", data, eocd + 16)[0]
    if jumlah <= 0 or mulai <= 0 or mulai >= panjang:
        return None, "daftar isi tidak masuk akal"

    pos = mulai
    for _ in range(jumlah):
        if data[pos:pos+4] != b"PK\x01\x02":
            return None, "tanda entri daftar tidak ditemukan di %d" % pos
        ukuran_padat = struct.unpack_from("<I", data, pos + 20)[0]
        panjang_nama = struct.unpack_from("<H", data, pos + 28)[0]
        panjang_tambahan = struct.unpack_from("<H", data, pos + 30)[0]
        panjang_komentar = struct.unpack_from("<H", data, pos + 32)[0]
        offset_lokal = struct.unpack_from("<I", data, pos + 42)[0]
        nama_entri = data[pos+46:pos+46+panjang_nama].decode("utf-8", "replace")

        if nama_entri.endswith("/" + nama) or nama_entri == nama:
            # Header lokal, panjang nama dan tambahannya dibaca dari situ.
            if data[offset_lokal:offset_lokal+4] != b"PK\x03\x04":
                return None, "tanda header lokal tidak ditemukan"
            nl = struct.unpack_from("<H", data, offset_lokal + 26)[0]
            tl = struct.unpack_from("<H", data, offset_lokal + 28)[0]
            mulai_data = offset_lokal + 30 + nl + tl
            return data[mulai_data:mulai_data+ukuran_padat], nama_entri

        pos += 46 + panjang_nama + panjang_tambahan + panjang_komentar
    return None, "tidak ada entri yang cocok"

isi, keterangan = cari_zip(data, "ffmpeg.exe")
if isi is None:
    print("     ! GAGAL: %s" % keterangan)
    sys.exit(1)

print("     ditemukan : %s" % keterangan)
print("     ukuran    : %.1f MB" % (len(isi) / 1048576))

# Berkas exe harus mulai dengan tanda MZ.
if isi[:2] != b"MZ":
    print("     ! isinya bukan berkas exe (tidak diawali MZ)")
    sys.exit(1)
print("     tanda MZ  : ada (berkas exe sungguhan)")
print()

# ── 4. Jalankan hasilnya ──────────────────────────────────────────────────
print("  ── 4. menjalankan hasilnya ──")
keluar = W / "build" / "uji-ffmpeg" / "ffmpeg.exe"
keluar.parent.mkdir(parents=True, exist_ok=True)
keluar.write_bytes(isi)

import subprocess
r = subprocess.run([str(keluar), "-version"], capture_output=True, text=True, timeout=60, errors="replace")
baris = (r.stdout or r.stderr or "").splitlines()
print("     kode keluar: %d" % r.returncode)
for b in baris[:3]:
    print("     %s" % b[:80])

if r.returncode != 0:
    print()
    print("     ! ffmpeg hasil ekstraksi tidak bisa dijalankan")
    sys.exit(1)

print()
print("  ══ KESIMPULAN ══")
print("     ffmpeg bisa diunduh, dikeluarkan dari arsip, dan dijalankan.")
print("     Fitur perkecil video, pembatas FPS, dan kenburns akan bekerja")
print("     di PC yang sama sekali tidak punya ffmpeg.")
print()
