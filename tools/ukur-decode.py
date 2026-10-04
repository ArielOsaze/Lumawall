#!/usr/bin/env python3
"""Ukur biaya decode tiap video, satu per satu, tanpa mengganggu wallpaper.

KENAPA ALAT INI ADA:

Keluhannya: "decode videonya kok naik ya biasanya 3 monitor di 22% mentok ini
bisa ngespike 30 lebih". Decode video naik dari 22% ke 30%+.

Yang perlu diketahui lebih dulu: berapa biaya decode MASING-MASING stream, dan
apakah salinan hasil perkecil benar-benar lebih murah daripada berkas aslinya.
Tanpa angka itu, setiap perubahan hanya tebakan.

CARA KERJANYA:

Beban GPU diukur tiga kali dengan cara yang sama:
  1. hanya wallpaper yang sedang jalan  -> garis dasar
  2. ditambah decode berkas ASLI 4K, pada kecepatan putar asli (-re)
  3. ditambah decode SALINAN hasil perkecil, pada kecepatan putar asli

Selisihnya adalah biaya stream itu sendiri. Karena pengukurannya memakai
selisih, beban wallpaper yang sedang jalan tidak perlu dihentikan - dan tidak
ada wallpaper yang diganggu.

Semua proses ffmpeg dimatikan di akhir, termasuk kalau ada yang menggantung.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
CACHE = Path(os.environ["LOCALAPPDATA"]) / "LumaWall" / "VideoCache"

PS_COUNTER = r"\GPU Engine(*engtype_VideoDecode*)\Utilization Percentage"


def ukur(detik=6, jeda=0.5):
    """Rata-rata dan puncak beban decode GPU selama `detik` detik."""
    script = (
        "$v=@();"
        "for ($i=0; $i -lt %d; $i++) {"
        "  $c = Get-Counter '%s' -EA SilentlyContinue;"
        "  $t = ($c.CounterSamples | Measure-Object -Property CookedValue -Sum).Sum;"
        "  $v += [math]::Round($t,2);"
        "  Start-Sleep -Milliseconds %d"
        "};"
        "$v -join ' '"
    ) % (int(detik / jeda), PS_COUNTER, int(jeda * 1000))
    out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                         capture_output=True, text=True, timeout=180).stdout.strip()
    nilai = [float(x) for x in out.split() if x.replace(".", "", 1).isdigit()]
    if not nilai:
        return 0.0, 0.0, []
    return sum(nilai) / len(nilai), max(nilai), nilai


def ffmpeg_path():
    for kandidat in [
        W / "tools" / "ffmpeg.exe",
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
    ]:
        if kandidat.exists():
            return str(kandidat)
    # yang dipakai aplikasi
    sys.path.insert(0, str(W / "tools"))
    return "ffmpeg"


def decode_basah(ff, berkas, detik=7):
    """Jalankan ffmpeg decode berkas ini pada kecepatan putar asli."""
    return subprocess.Popen(
        [ff, "-nostdin", "-loglevel", "error", "-hwaccel", "cuda",
         "-re", "-i", str(berkas), "-f", "null", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def matikan(p):
    try:
        p.terminate()
        p.wait(timeout=10)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   BIAYA DECODE TIAP STREAM  (ffmpeg + NVDEC, kecepatan putar asli)")
print("  ══════════════════════════════════════════════════════════════════")
print()

ff = ffmpeg_path()
print("  ffmpeg: %s" % ff)
print()

# Berkas yang diuji: berkas asli yang dipakai, dan salinan hasil perkecilnya.
d = json.load(open(Path(os.environ["LOCALAPPDATA"]) / "LumaWall" / "config.json", encoding="utf-8"))
mv = {e["Key"]: e["Value"] for e in (d.get("MonitorVideos") or [])}

uji = []
for device, asli in sorted(mv.items()):
    if not os.path.exists(asli):
        continue
    nama = Path(asli).stem
    salinan = None
    for f in CACHE.glob(nama + "-*p-*.mp4"):
        salinan = f
        break
    uji.append((device, Path(asli), salinan))

print("  Garis dasar (hanya wallpaper yang sedang jalan)...")
dasar_avg, dasar_maks, _ = ukur()
print("     rata-rata %.1f%%   puncak %.1f%%" % (dasar_avg, dasar_maks))
print()

hasil = []
for device, asli, salinan in uji:
    print("  ── %s ──" % device)
    print("     %s" % asli.name)

    for label, berkas in [("asli  ", asli), ("salinan", salinan)]:
        if berkas is None or not Path(berkas).exists():
            print("     %s : (tidak ada)" % label)
            continue
        p = decode_basah(ff, berkas)
        time.sleep(1.5)                      # biarkan decoder menyalakan dulu
        avg, maks, _ = ukur(detik=6)
        matikan(p)
        time.sleep(1.5)
        print("     %s : rata-rata %5.1f%%  puncak %5.1f%%  (naik %+.1f dari dasar)"
              % (label, avg, maks, avg - dasar_avg))
        hasil.append((device, label.strip(), avg - dasar_avg))

    print()

print("  ══════════════════════════════════════════════════════════════════")
print("   KESIMPULAN")
print("  ══════════════════════════════════════════════════════════════════")
print()
print("     garis dasar (3 wallpaper jalan) : %.1f%%" % dasar_avg)
print()
for device, label, delta in hasil:
    print("     %-14s %-8s +%.1f%%" % (device, label, delta))
print()
print("  Kalau 'salinan' jauh lebih murah daripada 'asli', maka perkecil itu")
print("  memang bekerja dan sisanya adalah biaya tiga stream yang wajar.")
print("  Kalau keduanya sama mahal, salinannya tidak dipakai.")
print()
