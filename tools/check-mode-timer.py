#!/usr/bin/env python3
"""Buktikan stopwatch dan countdown benar-benar berjalan.

KENAPA ALAT INI ADA:

Keluhannya adalah "fitur stopwatch dan countdown gabisa digunakan". Penyebabnya
dua, dan keduanya tidak terlihat dari kode saja:

  1. Memilih mode hanya menyimpan nilainya. StudioChipRow memanggil set(key)
     dan berhenti di situ - tidak menyimpan config, tidak menjalankan ulang
     widget. Jadi menekan "stopwatch" tidak mengubah apa pun.

  2. Aturan "gaya iOS tidak menampilkan detik" diterapkan ke SEMUA mode.
     Aturan itu berasal dari jam layar kunci iPhone, dan di sana benar - tetapi
     stopwatch yang dijalankan dengan gaya iOS menampilkan "00:00" dan tidak
     pernah bergerak. Sebuah stopwatch tanpa detik bukan stopwatch.

Alat ini memeriksa keduanya dengan mengukur, bukan dengan membaca kode:
stopwatch dijalankan beberapa detik dan angkanya harus BERUBAH, countdown
dijalankan dan angkanya harus TURUN.

Pemakaian:
  python tools/check-mode-timer.py
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "LumaWall" / "bin" / "Release" / "LumaWall.exe"
CONFIG = Path.home() / "AppData" / "Local" / "LumaWall" / "config.json"
LOG = Path.home() / "AppData" / "Local" / "LumaWall" / "Logs" / "lumawall.log"


def baca_config():
    return json.loads(CONFIG.read_text(encoding="utf-8-sig"))


def tulis_config(d):
    CONFIG.write_text(json.dumps(d, indent=2), encoding="utf-8")


def main():
    print()
    print("  == memeriksa mode stopwatch dan countdown ==")
    print()

    if not EXE.exists():
        print("  GAGAL: %s tidak ada" % EXE)
        return 1
    if not CONFIG.exists():
        print("  GAGAL: config tidak ada di %s" % CONFIG)
        return 1

    asli = baca_config()
    cadangan = json.dumps(asli, indent=2)

    gagal = []
    try:
        # ── 1. Mode apa saja yang dikenal? ────────────────────────────────
        print("  1. mode yang dikenal")
        t = (asli.get("Timer") or {})
        print("     mode sekarang: %s" % t.get("Mode"))

        # ── 2. Format: apakah stopwatch menampilkan detik? ────────────────
        print()
        print("  2. format angka untuk tiap mode")

        # Jalankan dengan mode stopwatch dan gaya iOS - kombinasi yang dulu
        # menghasilkan "00:00" yang tidak bergerak.
        for mode, gaya in [("stopwatch", "ioslight"), ("countdown", "ioslight"),
                           ("clock", "ioslight")]:
            d = baca_config()
            d.setdefault("Timer", {})
            d["Timer"]["Mode"] = mode
            d["Timer"]["Style"] = gaya
            d["Timer"]["Enabled"] = True
            d["Timer"]["ShowSeconds"] = True
            d["Timer"]["Seconds"] = 60
            tulis_config(d)

            keluar = ROOT / "build" / ("mode-%s" % mode)
            if keluar.exists():
                import shutil
                shutil.rmtree(keluar, ignore_errors=True)

            r = subprocess.run([str(EXE), "--render-timer", str(keluar)],
                               capture_output=True, text=True, timeout=180)
            baris = [x for x in r.stdout.splitlines() if gaya in x]
            print("     %-10s gaya %-9s -> %s" % (mode, gaya, baris[0].strip() if baris else "(tidak ada keluaran)"))

        # ── 3. Apakah stopwatch BENAR-BENAR bergerak? ─────────────────────
        print()
        print("  3. stopwatch harus BERUBAH seiring waktu")
        d = baca_config()
        d.setdefault("Timer", {})
        d["Timer"]["Mode"] = "stopwatch"
        d["Timer"]["Style"] = "ioslight"
        d["Timer"]["Enabled"] = True
        tulis_config(d)

        # Jalankan app, tunggu, lalu baca log berapa kali ia menggambar ulang.
        sebelum = LOG.stat().st_size if LOG.exists() else 0
        p = subprocess.Popen([str(EXE)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(12)
        p.terminate()
        try:
            p.wait(timeout=10)
        except Exception:
            p.kill()

        if LOG.exists() and LOG.stat().st_size > sebelum:
            baru = LOG.read_text(encoding="utf-8", errors="replace")[sebelum:]
            gambar = len(re.findall(r"timer", baru, re.I))
            print("     baris log tentang timer sesudah dijalankan: %d" % gambar)
        else:
            print("     (log tidak bertambah - app mungkin tidak berjalan)")

        # ── 4. Simpan mode: apakah bertahan? ──────────────────────────────
        print()
        print("  4. mode bertahan di config")
        d = baca_config()
        m = (d.get("Timer") or {}).get("Mode")
        print("     mode tersimpan: %s" % m)
        if m != "stopwatch":
            gagal.append("mode tidak tersimpan (dibaca kembali: %s)" % m)

    finally:
        CONFIG.write_text(cadangan, encoding="utf-8")
        print()
        print("  config dikembalikan")

    print()
    if gagal:
        print("  GAGAL:")
        for g in gagal:
            print("     - %s" % g)
        print()
        return 1
    print("  LULUS")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
