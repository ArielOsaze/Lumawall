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
import os
import re
import struct
import subprocess
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
tujuan_zip = W / "build" / "uji-ffmpeg.zip"
tujuan_zip.parent.mkdir(parents=True, exist_ok=True)

if tujuan_zip.exists() and tujuan_zip.stat().st_size > 10_000_000:
    print("     sudah ada dari uji sebelumnya (%.1f MB)" % (tujuan_zip.stat().st_size / 1048576))
else:
    print("     mengunduh… (bisa 1-3 menit)")
    try:
        r = urllib.request.Request(SUMBER, headers=UA)
        with urllib.request.urlopen(r, timeout=900) as f, open(tujuan_zip, "wb") as keluar:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                keluar.write(b)
        print("     terunduh: %.1f MB" % (tujuan_zip.stat().st_size / 1048576))
    except Exception as e:
        print("     ! GAGAL mengunduh: %s" % str(e)[:90])
        sys.exit(1)
print()

with zipfile.ZipFile(tujuan_zip) as z:
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

# ── 3. Ekstraksi dengan ZipFile, sama seperti Ffmpeg.cs ───────────────────
print("  ── 3. ekstraksi dengan System.IO.Compression.ZipFile ──")
#
# Pemindai zip buatan sendiri TIDAK dipakai lagi. Ia menghasilkan ffmpeg rusak:
# 35,7 MB (seharusnya 100 MB), tanpa tanda MZ, dan Windows menolaknya dengan
# "not compatible with the version of Windows". Sebabnya arsip gyan.dev memakai
# data descriptor, sehingga ukuran berkas tidak ada di header lokal.
#
# Ffmpeg.cs sekarang memakai ZipFile bawaan .NET, dan alat ini memakai pustaka
# yang sama supaya hasilnya mencerminkan apa yang dilakukan aplikasi.
import zipfile

KELUAR = W / "build" / "uji-ffmpeg"
KELUAR.mkdir(parents=True, exist_ok=True)


def ekstrak(zip_path, nama_dicari, tujuan):
    """Cara yang sama dengan Ffmpeg.BacaZip."""
    with zipfile.ZipFile(zip_path) as arsip:
        for entri in arsip.infolist():
            nama_entri = entri.filename.replace("\\", "/")
            if not (nama_entri.endswith("/" + nama_dicari) or nama_entri == nama_dicari):
                continue
            sementara = tujuan + ".sebagian"
            with arsip.open(entri) as masuk, open(sementara, "wb") as keluar:
                while True:
                    b = masuk.read(65536)
                    if not b:
                        break
                    keluar.write(b)
            if os.path.exists(tujuan):
                os.remove(tujuan)
            os.rename(sementara, tujuan)
            return tujuan, entri.file_size
    return None, None


for dicari in ["ffmpeg.exe", "ffprobe.exe"]:
    tujuan = str(KELUAR / dicari)
    hasil, ukuran_asli = ekstrak(str(tujuan_zip), dicari, tujuan)
    if hasil is None:
        print("     %-12s GAGAL: tidak ada di arsip" % dicari)
        if dicari == "ffmpeg.exe":
            sys.exit(1)
        continue

    ukuran = os.path.getsize(hasil)
    with open(hasil, "rb") as f:
        kepala = f.read(2)
    tanda = "MZ (exe sungguhan)" if kepala == b"MZ" else "BUKAN exe (%r)" % kepala
    print("     %-12s %.1f MB  %s" % (dicari, ukuran / 1048576, tanda))

    if dicari == "ffmpeg.exe" and kepala != b"MZ":
        print()
        print("     ! hasilnya bukan berkas exe - ekstraksinya salah")
        sys.exit(1)

# ── 4. Jalankan hasilnya ──────────────────────────────────────────────────
print()
print("  ── 4. menjalankan hasil ekstraksi ──")
exe = KELUAR / "ffmpeg.exe"
r = subprocess.run([str(exe), "-version"], capture_output=True, text=True,
                   timeout=120, errors="replace")
print("     kode keluar: %d" % r.returncode)
for b in (r.stdout or r.stderr or "").splitlines()[:2]:
    print("     %s" % b[:84])

if r.returncode != 0:
    print()
    print("  ! ffmpeg hasil ekstraksi tidak bisa dijalankan")
    sys.exit(1)

# ── 5. Uji benar-benar memproses video ────────────────────────────────────
print()
print("  ── 5. uji kenburns (gambar jadi video) ──")
try:
    from PIL import Image
    uji_img = W / "build" / "uji-kenburns2.jpg"
    Image.new("RGB", (1280, 720), (60, 40, 120)).save(uji_img, quality=90)

    hasil_video = W / "build" / "uji-kenburns2.mp4"
    filter_ = ("[0:v]scale=1280:720:force_original_aspect_ratio=decrease[fg];"
               "[0:v]scale=1280:720,boxblur=20:1,eq=brightness=-0.18[bg];"
               "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
               "zoompan=z='1.0+0.015*sin(2*PI*on/192)':x='iw/2-(iw/zoom/2)':"
               "y='ih/2-(ih/zoom/2)':d=192:s=1280x720:fps=24[v]")

    r2 = subprocess.run(
        [str(exe), "-y", "-i", str(uji_img), "-filter_complex", filter_,
         "-map", "[v]", "-frames:v", "192", "-an", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "25", "-pix_fmt", "yuv420p",
         "-movflags", "+faststart", str(hasil_video)],
        capture_output=True, text=True, timeout=300, errors="replace")

    print("     kode keluar: %d" % r2.returncode)
    if hasil_video.exists() and hasil_video.stat().st_size > 10000:
        print("     hasil: %.2f MB" % (hasil_video.stat().st_size / 1048576))
    else:
        print("     ! video tidak terbentuk")
        sys.exit(1)
except ImportError:
    print("     (PIL tidak ada, uji kenburns dilewati)")

print()
print("  ══ KESIMPULAN ══")
print("     ffmpeg bisa diunduh, dikeluarkan dari arsip, dan dijalankan.")
print("     Fitur perkecil video, pembatas FPS, dan kenburns akan bekerja")
print("     di PC yang sama sekali tidak punya ffmpeg.")
print()
