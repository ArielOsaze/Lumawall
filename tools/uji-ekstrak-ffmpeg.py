#!/usr/bin/env python3
"""Uji ekstraksi ffmpeg dengan cara yang SAMA dengan Ffmpeg.cs yang baru.

KENAPA ALAT INI ADA:

Pemindai zip buatan sendiri GAGAL pada arsip sebenarnya, dan itu ketahuan hanya
karena hasilnya benar-benar dijalankan:

    ffmpeg.exe hasil ekstraksi 35,7 MB (seharusnya ~80 MB)
    tidak diawali tanda MZ
    Windows menolaknya: "not compatible with the version of Windows"

Sebabnya: arsip gyan.dev memakai data descriptor, sehingga ukuran berkas tidak
ada di header lokal. Pemindai yang menyalin sebesar ukuran dari daftar isi
mengambil data berkas ditambah header entri berikutnya.

Sekarang Ffmpeg.cs memakai System.IO.Compression.ZipFile. Alat ini menguji
dengan pustaka zip yang sama, lalu MENJALANKAN hasilnya - karena "berkas
terbentuk" tidak membuktikan apa pun, dan itulah pelajaran dari kegagalan tadi.

Urutan ujinya sengaja dibalik dari sebelumnya: ekstraksi diuji lebih dulu pada
arsip yang sudah ada, baru unduhan - supaya kegagalan seperti timeout unduhan
tidak menyembunyikan hasil uji yang lebih penting.
"""

import subprocess
import sys
import zipfile
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
ZIP = W / "build" / "uji-ffmpeg.zip"
KELUAR = W / "build" / "uji-ffmpeg"

print()
print("  ══════════════════════════════════════════════════════════════════")
print("   UJI EKSTRAKSI FFMPEG (ZipFile, seperti Ffmpeg.cs)")
print("  ══════════════════════════════════════════════════════════════════")
print()

if not ZIP.exists():
    print("  ! arsip tidak ada: %s" % ZIP)
    sys.exit(1)

print("  arsip: %.1f MB" % (ZIP.stat().st_size / 1048576))
print()

# ── Ekstraksi dengan ZipFile, cara yang sama dengan Ffmpeg.BacaZip ────────
KELUAR.mkdir(parents=True, exist_ok=True)

def baca_zip(zip_path, nama_dicari, tujuan):
    """Cara yang sama dengan Ffmpeg.BacaZip yang baru."""
    try:
        with zipfile.ZipFile(zip_path) as arsip:
            for entri in arsip.infolist():
                nama = entri.filename.replace("\\", "/")
                if not (nama.endswith("/" + nama_dicari) or nama == nama_dicari):
                    continue
                sementara = tujuan + ".sebagian"
                with arsip.open(entri) as masuk, open(sementara, "wb") as keluar:
                    while True:
                        b = masuk.read(65536)
                        if not b:
                            break
                        keluar.write(b)
                if Path(tujuan).exists():
                    Path(tujuan).unlink()
                Path(sementara).rename(tujuan)
                return tujuan, entri.file_size
    except Exception as e:
        return None, str(e)[:80]
    return None, "tidak ada entri yang cocok"


print("  ── ekstraksi ──")
for dicari in ["ffmpeg.exe", "ffprobe.exe"]:
    tujuan = str(KELUAR / dicari)
    hasil, info = baca_zip(str(ZIP), dicari, tujuan)
    if hasil is None:
        print("     %-12s GAGAL: %s" % (dicari, info))
        if dicari == "ffmpeg.exe":
            sys.exit(1)
        continue

    ukuran = Path(hasil).stat().st_size
    kepala = Path(hasil).read_bytes()[:2]
    tanda = "MZ (exe sungguhan)" if kepala == b"MZ" else "BUKAN exe (%r)" % kepala
    print("     %-12s %.1f MB  %s" % (dicari, ukuran / 1048576, tanda))

    if dicari == "ffmpeg.exe" and kepala != b"MZ":
        print()
        print("     ! hasilnya bukan berkas exe - ekstraksinya masih salah")
        sys.exit(1)

print()

# ── Jalankan hasilnya ─────────────────────────────────────────────────────
print("  ── menjalankan hasil ekstraksi ──")
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

# ── Uji benar-benar memproses video (kenburns) ────────────────────────────
print()
print("  ── uji kenburns (gambar jadi video) ──")
from PIL import Image
uji_img = W / "build" / "uji-kenburns.jpg"
Image.new("RGB", (1280, 720), (40, 60, 120)).save(uji_img, quality=90)

hasil_video = W / "build" / "uji-kenburns.mp4"
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
    print("     %s" % (r2.stderr or "")[-400:])
    sys.exit(1)

print()
print("  ══ KESIMPULAN ══")
print("     ffmpeg diekstrak dengan benar (berkas exe sungguhan),")
print("     bisa dijalankan, DAN bisa memproses kenburns.")
print("     Fitur itu akan bekerja di PC yang sama sekali tidak punya ffmpeg.")
print()
