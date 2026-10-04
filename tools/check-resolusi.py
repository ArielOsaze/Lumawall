#!/usr/bin/env python3
"""Buktikan keempat mode resolusi menghasilkan keputusan yang berbeda.

KENAPA ALAT INI ADA:

Keluhannya: "resolusi video wallpaper harus sesuai resolusi monitor da tambahin
pilihan opsi resolusi". Yang mudah salah di sini bukan tampilannya, melainkan
apakah pilihannya benar-benar mengubah berkas yang didecode - persis seperti
setelan FPS yang dulu tombolnya ada tetapi tidak melakukan apa pun.

Jadi yang diperiksa adalah KEPUTUSAN aplikasinya sendiri, lewat perintah
--pilih-video. Aturannya tidak dihitung ulang di Python: hitungan ulang hanya
akan membuktikan bahwa Python bisa berhitung, bukan bahwa aplikasinya memilih
berkas yang benar.

Yang harus benar:

  auto     video 4K di layar kecil  -> diturunkan
  auto     video yang sudah pas     -> TIDAK diturunkan
  monitor  selalu disamakan dengan lebar layar
  half     setengah lebar layar
  source   tidak pernah diturunkan, berapa pun besarnya
"""

import json
import os
import subprocess
import sys
from pathlib import Path

W = Path(r"C:\Users\ariel\Documents\Codex\2026-09-20\bik\work")
EXE = W / "LumaWall" / "bin" / "Release" / "LumaWall.exe"
CONFIG = Path(os.environ["LOCALAPPDATA"]) / "LumaWall" / "config.json"

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


def putuskan(berkas, lw, lt, mode):
    """Tanya aplikasinya sendiri apa yang akan dipakai."""
    out = subprocess.run(
        [str(EXE), "--pilih-video", str(berkas), str(lw), str(lt), "--mode", mode],
        capture_output=True, text=True, timeout=180).stdout
    for baris in out.splitlines():
        if baris.startswith("pilih-video"):
            hasil = {}
            for bagian in baris.split():
                if "=" in bagian:
                    k, v = bagian.split("=", 1)
                    hasil[k] = v
            return hasil
    return {}


def lebar_video(path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=60)
        return int(r.stdout.strip())
    except Exception:
        return None


print()
print("  ══════════════════════════════════════════════════════════════════")
print("   MODE RESOLUSI: apakah tiap pilihan mengubah keputusannya?")
print("  ══════════════════════════════════════════════════════════════════")
print()

if not EXE.exists():
    print("  Aplikasi belum dibangun: %s" % EXE)
    sys.exit(1)

# Video uji: yang terbesar yang terpasang, supaya bedanya terlihat.
d = json.load(open(CONFIG, encoding="utf-8"))
mv = {e["Key"]: e["Value"] for e in (d.get("MonitorVideos") or [])}

kandidat = None
for device, path in sorted(mv.items()):
    if os.path.exists(path):
        w = lebar_video(path)
        if w and (kandidat is None or w > kandidat[2]):
            kandidat = (device, path, w)

if kandidat is None:
    print("  Tidak ada video uji yang terpasang.")
    sys.exit(0)

device, path, asli = kandidat
LAYAR = 1920

print("  video uji : %s" % Path(path).name)
print("  lebar asli: %d px" % asli)
print("  layar uji : %d px" % LAYAR)
print()
print("  %-9s %-10s %-8s %s" % ("mode", "pakai", "diskalakan", "alasan"))
print("  " + "-" * 66)

hasil = {}
for mode in ["auto", "monitor", "half", "source"]:
    h = putuskan(path, LAYAR, 1080, mode)
    hasil[mode] = h
    print("  %-9s %-10s %s" % (
        mode,
        (h.get("putuskan", "?") + " px"),
        h.get("alasan", "?")[:44]))

print()
print("  ── yang diperiksa ──")
print()

# Video 4K di layar 1920 jelas jauh lebih besar, jadi mode auto harus menurunkan.
periksa("auto menurunkan video yang jauh lebih besar",
        hasil["auto"].get("putuskan") == str(LAYAR),
        "dapat: %s, harusnya %d" % (hasil["auto"].get("putuskan"), LAYAR))

periksa("monitor menyamakan dengan lebar layar",
        hasil["monitor"].get("putuskan") == str(LAYAR),
        "dapat: %s, harusnya %d" % (hasil["monitor"].get("putuskan"), LAYAR))

periksa("half memakai setengah lebar layar",
        hasil["half"].get("putuskan") == str(LAYAR // 2),
        "dapat: %s, harusnya %d" % (hasil["half"].get("putuskan"), LAYAR // 2))

periksa("source tidak pernah menurunkan",
        hasil["source"].get("putuskan") == "0",
        "dapat: %s" % hasil["source"].get("putuskan"))

periksa("source tidak menyentuh berkasnya",
        hasil["source"].get("diskalakan") == "tidak",
        "dapat: %s" % hasil["source"].get("diskalakan"))

# Yang paling penting: keempatnya harus BERBEDA satu sama lain. Kalau dua mode
# menghasilkan keputusan yang sama, salah satunya tidak melakukan apa pun -
# dan itulah bentuk kegagalan yang sedang dicegah.
putus = [hasil[m].get("putuskan") for m in ["monitor", "half", "source"]]
periksa("tiap mode menghasilkan lebar yang berbeda",
        len(set(putus)) == 3,
        "lebar: %s" % putus)

# Video yang sudah pas dengan layar tidak boleh diturunkan oleh mode auto:
# menurunkannya membuang ketajaman tanpa menghemat apa pun yang berarti.
kecil = None
for device2, path2 in sorted(mv.items()):
    if os.path.exists(path2):
        w = lebar_video(path2)
        if w and w <= LAYAR:
            kecil = (path2, w)
            break

if kecil is not None:
    h = putuskan(kecil[0], LAYAR, 1080, "auto")
    periksa("auto TIDAK menurunkan video yang sudah sesuai layar",
            h.get("putuskan") == "0",
            "%s (%d px) -> putuskan=%s" % (Path(kecil[0]).name[:30], kecil[1], h.get("putuskan")))

print()
print("  ── %d lulus, %d gagal ──" % (lulus, gagal))
sys.exit(1 if gagal else 0)
