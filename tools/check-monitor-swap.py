#!/usr/bin/env python3
"""Buktikan setelan mengikuti MONITOR, bukan nomor DISPLAY.

KENAPA ALAT INI ADA:

Keluhannya: "kenapa suka ngebug ya saat pindah konektor hdmi di display utama
jadi kebalik dan ke crop". Wallpaper di layar utama terbalik dan terpotong
setelah kabel HDMI dipindah.

Sebabnya bukan kabelnya. Windows menomori layar menurut urutan ia menemukannya,
dan urutan itu tidak tetap: mencabut lalu memasang kembali kabel HDMI menukar
nomor antar dua monitor. Aplikasinya menyimpan setelan per NOMOR
("\\.\DISPLAY3"), jadi setelannya ikut nomor, bukan ikut layar. Yang terjadi
kemudian: satu monitor memakai setelan milik monitor lain.

Di mesin ini buktinya terekam: DISPLAY3 dulu 1366x768, sekarang 1920x1080 dan
menjadi layar utama - dan setelan tersimpan untuk DISPLAY3 adalah
FlipVertical=true dengan Fit="center", yang dibuat untuk layar 1366x768.
FlipVertical membuat gambar terbalik; "center" menggambar video seukuran
aslinya di tengah, sehingga layar yang lebih besar memotongnya.

Perbaikannya: setelan disimpan per identitas monitor dari EDID
("VSC423F#UID28932"), yang tidak ikut bertukar saat kabel dipindah.

CARA MEMBUKTIKANNYA TANPA MENYENTUH KABEL:

Alat ini menjalankan aplikasi dengan config buatan yang menyerupai keadaan
sesudah pertukaran, lalu memeriksa config yang ditulis kembali. Yang diperiksa
adalah hal yang membuat bug itu terlihat: apakah setelan sebuah monitor masih
menempel padanya ketika nomor DISPLAY-nya berubah.

Tidak ada kabel yang dicabut, dan display utama tidak diganggu.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
EXE = W / "LumaWall" / "bin" / "Release" / "LumaWall.exe"
CONFIG_DIR = Path(os.environ["LOCALAPPDATA"]) / "LumaWall"
CONFIG = CONFIG_DIR / "config.json"

lulus = 0
gagal = 0


def periksa(nama, benar, keterangan=""):
    global lulus, gagal
    if benar:
        lulus += 1
        print("  LULUS  %s" % nama)
    else:
        gagal += 1
        print("  GAGAL  %s  %s" % (nama, keterangan))


def baca_config():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def tulis_config(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(data, f)


def monitor_sekarang():
    """Nomor DISPLAY -> identitas monitor, lewat alat Probe."""
    probe = W / "build" / "probe-monitor" / "Probe.exe"
    if not probe.exists():
        return {}
    out = subprocess.run([str(probe)], capture_output=True, text=True, timeout=60).stdout
    hasil = {}
    for baris in out.splitlines():
        baris = baris.strip()
        if baris.startswith(r"\\.\DISPLAY") and "#" in baris:
            bagian = baris.split()
            nomor = bagian[0]
            for b in bagian[1:]:
                if b.startswith("\\\\?\\DISPLAY#"):
                    isi = b.split("#")
                    if len(isi) >= 3:
                        uid = isi[2]
                        i = uid.find("UID")
                        hasil[nomor] = isi[1] + "#" + (uid[i:] if i >= 0 else uid)
    return hasil


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   BUKTI: setelan mengikuti MONITOR, bukan nomor DISPLAY")
print("  ══════════════════════════════════════════════════════════════════")
print()

peta = monitor_sekarang()
print("  Monitor yang terpasang:")
for nomor, identitas in sorted(peta.items()):
    print("     %-14s %s" % (nomor, identitas))
print()

if len(peta) < 2:
    print("  Dilewati: butuh minimal dua monitor yang bisa dibaca identitasnya.")
    sys.exit(0)

# ── 1. config lama: setelan terpasang di nomor DISPLAY3 ────────────────────
asli = baca_config()
cadangan = CONFIG.read_bytes()

# nomor yang punya identitas, dan identitas yang dipakai
nomor_uji = sorted(peta.keys())[-1]
identitas_uji = peta[nomor_uji]
nomor_lain = sorted(peta.keys())[0]

print("  Uji dengan %s (monitor %s)" % (nomor_uji, identitas_uji))
print()

uji = dict(asli)
uji["Displays"] = [
    {
        "Key": nomor_uji,
        "Value": {
            "Brightness": 1.0, "Contrast": 1.0, "Saturation": 1.0, "Hue": 0.0,
            "Gamma": 1.0, "Filter": "none", "FlipHorizontal": False,
            "FlipVertical": True,          # <- yang membuat gambar terbalik
            "HdrToneMap": False, "HdrExposure": 0.0, "HdrHighlight": 0.7,
            "Fit": "center",               # <- yang membuat gambar terpotong
            "Zoom": 1.0, "OffsetX": 0.0, "OffsetY": 0.0,
            "PlaybackRate": 1.0, "PingPong": False,
        },
    }
]
uji["DisplaysByMonitor"] = []
uji["WallpapersByMonitor"] = []
uji["MonitorIdsAtLastRun"] = []
tulis_config(uji)

# ── 2. jalankan aplikasi supaya ia merekonsiliasi ─────────────────────────
subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Stop-Process -Name LumaWall -Force -EA SilentlyContinue; Start-Sleep 2"],
    capture_output=True, timeout=90)

proc = subprocess.Popen([str(EXE)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
import time
time.sleep(22)

sesudah = baca_config()
proc.terminate()
try:
    proc.wait(timeout=20)
except Exception:
    proc.kill()
time.sleep(2)

print("  ── hasil ──")
print()

# ── 3. yang diperiksa ─────────────────────────────────────────────────────
d_by_mon = {e["Key"]: e["Value"] for e in (sesudah.get("DisplaysByMonitor") or [])}
d_by_num = {e["Key"]: e["Value"] for e in (sesudah.get("Displays") or [])}
peta_tersimpan = {e["Key"]: e["Value"] for e in (sesudah.get("MonitorIdsAtLastRun") or [])}

periksa("identitas monitor tercatat",
        len(peta_tersimpan) >= 2,
        "tercatat: %d" % len(peta_tersimpan))

periksa("setelan tersimpan di bawah identitas monitor, bukan nomor",
        identitas_uji in d_by_mon,
        "kunci yang ada: %s" % list(d_by_mon.keys()))

# Inilah inti perbaikannya: setelan FlipVertical tidak boleh menempel pada
# nomor DISPLAY, karena nomor itu bisa berpindah ke monitor lain.
periksa("setelan tidak lagi disimpan di bawah nomor DISPLAY",
        nomor_uji not in d_by_num,
        "masih ada: %s" % list(d_by_num.keys()))

if identitas_uji in d_by_mon:
    v = d_by_mon[identitas_uji]
    # Setelah pensiun, monitor mulai dari netral - bukan mewarisi framing
    # monitor lain. Itu jawaban yang jujur: yang salah tidak bisa diketahui
    # asalnya, jadi netral adalah satu-satunya nilai yang tidak menipu.
    terbalik = v.get("FlipVertical") or v.get("FlipHorizontal")
    periksa("monitor tidak mewarisi framing terbalik",
            not terbalik,
            "FlipVertical=%s FlipHorizontal=%s" % (v.get("FlipVertical"), v.get("FlipHorizontal")))
    periksa("monitor tidak mewarisi pemotongan",
            v.get("Fit") == "cover",
            "Fit=%s" % v.get("Fit"))

print()
print("  Setelan per monitor sesudah rekonsiliasi:")
for k, v in sorted(d_by_mon.items()):
    menarik = {a: b for a, b in v.items()
               if b not in (1.0, 0.0, False, None, "none", "cover", 0.7)}
    print("     %-22s %s" % (k, menarik if menarik else "(netral)"))
print()

# ── 4. pulihkan config asli ───────────────────────────────────────────────
CONFIG.write_bytes(cadangan)
print("  config asli dipulihkan")
print()
print("  ── %d lulus, %d gagal ──" % (lulus, gagal))
sys.exit(1 if gagal else 0)
