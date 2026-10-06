#!/usr/bin/env python3
"""Isi thumbnail yang kosong dengan frame dari videonya, disimpan di repo.

KENAPA ALAT INI ADA:

53 entri tidak punya thumbnailUrl. Sebelumnya mereka memakai placeholder
"nsfw_min.png" dari DesktopHut - situsnya memang tidak menyediakan pratinjau -
dan itu tampil sebagai kotak abu-abu di katalog. Setelah placeholder itu
dibuang, thumbnailUrl-nya kosong, dan kosong berarti kotak HITAM.

Yang tidak boleh dilakukan: menyimpan thumbnail di folder data mesin ini dan
merujuknya dengan file:// - katalognya ikut dipaketkan ke installer, jadi jalur
itu menunjuk berkas yang tidak ada di PC pembeli.

Yang dilakukan: frame video diambil, disimpan di dalam REPO (site/assets/thumbs),
lalu dirujuk dengan alamat publik situs. Dengan begitu thumbnail-nya ikut
terkirim ke semua orang, sama seperti thumbnail dari sumber lain.

Videonya dari DesktopHut, dan frame-nya diambil dari situ. Kalau unduhannya
gagal, entri itu tetap tanpa thumbnail dan dilaporkan - bukan diberi gambar
yang tidak berhubungan.
"""

import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CATALOG = W / "LumaWall" / "catalog.json"
SIMPAN = W / "site" / "assets" / "thumbs"
PUBLIK = "https://lumawall.xinet.id/assets/thumbs/"

FFMPEG = shutil.which("ffmpeg")
if not FFMPEG:
    for c in [W / "build" / "uji-ffmpeg" / "ffmpeg.exe"]:
        if c.exists():
            FFMPEG = str(c)
            break

print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MENGISI THUMBNAIL KOSONG DENGAN FRAME VIDEO")
print("  ══════════════════════════════════════════════════════════════════")
print()

if not FFMPEG:
    print("  ! ffmpeg tidak ditemukan")
    sys.exit(1)
print("  ffmpeg : %s" % FFMPEG)
print("  tujuan : %s" % SIMPAN)
print()

d = json.load(open(CATALOG, encoding="utf-8"))
items = d if isinstance(d, list) else d.get("Items", [])
kunci = "Items" if isinstance(d, dict) and "Items" in d else None

kosong = [i for i, e in enumerate(items) if not (e.get("thumbnailUrl") or "").strip()]
print("  entri tanpa thumbnail: %d" % len(kosong))
print()

SIMPAN.mkdir(parents=True, exist_ok=True)
berhasil = 0
gagal = []

for n, i in enumerate(kosong, 1):
    e = items[i]
    video = e.get("videoUrl") or ""
    if not video:
        gagal.append((i, "tidak ada videoUrl"))
        continue

    nama = re.sub(r"[^a-z0-9]+", "-", (e.get("title") or "wallpaper").lower()).strip("-")[:56]
    if not nama:
        nama = "wallpaper-%d" % i
    keluar = SIMPAN / (nama + ".jpg")

    if not (keluar.exists() and keluar.stat().st_size > 2000):
        # Frame pada detik ke-2; kalau videonya lebih pendek, ffmpeg tetap
        # mengeluarkan frame terdekat yang ada.
        # -update 1 wajib: tanpa itu ffmpeg mengeluh bahwa namanya bukan pola
        # urutan gambar, dan pada sebagian versi berkasnya tidak ditulis.
        #
        # Frame pertama dicoba lebih dulu, baru detik ke-2. Sebaliknya akan
        # gagal pada video DesktopHut yang sangat pendek (ada yang 27 KB).
        berhasil_ff = False
        pesan = ""
        for detik in [None, "2"]:
            arg = [FFMPEG, "-y"]
            if detik:
                arg += ["-ss", detik]

            # Header dikirim untuk semua sumber: moewalls menolak permintaan
            # tanpa Referer, dan DesktopHut kadang menolak tanpa User-Agent.
            # Tanpa ini, tiga entri moewalls gagal dengan pesan yang tidak
            # menyebut sebabnya.
            sumber = (e.get("sourceUrl") or "").strip()
            if not sumber:
                sumber = video.split("/download.php")[0] + "/"
            arg += ["-headers",
                    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n"
                    "Referer: " + sumber + "\r\n"]

            arg += ["-i", video, "-frames:v", "1", "-update", "1",
                    "-vf", "scale=640:-2", "-q:v", "4", str(keluar)]
            r = subprocess.run(arg, capture_output=True, timeout=180,
                               errors="replace")
            if r.returncode == 0 and keluar.exists() and keluar.stat().st_size > 2000:
                berhasil_ff = True
                break
            pesan = (r.stderr or "")[-160:]

        if not berhasil_ff:
            gagal.append((i, "ffmpeg: " + pesan.replace("\n", " ")[:90]))
            continue

    e["thumbnailUrl"] = PUBLIK + keluar.name
    berhasil += 1

    if n % 10 == 0:
        print("     %d / %d  (berhasil %d, gagal %d)" % (n, len(kosong), berhasil, len(gagal)))

print()
print("  berhasil: %d" % berhasil)
print("  gagal   : %d" % len(gagal))
for i, sebab in gagal[:10]:
    print("     [%d] %-46s %s" % (i, items[i].get("title", "")[:46], sebab))
print()

if kunci:
    d[kunci] = items
    keluar_json = d
else:
    keluar_json = items
CATALOG.write_text(json.dumps(keluar_json, ensure_ascii=False, indent=1), encoding="utf-8")
print("  ditulis: %s" % CATALOG)
print("  berkas thumbnail: %d di %s" % (len(list(SIMPAN.glob("*.jpg"))), SIMPAN))
print()

sisa = sum(1 for e in items if not (e.get("thumbnailUrl") or "").strip())
print("  thumbnail kosong sekarang: %d" % sisa)
print()
