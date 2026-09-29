#!/usr/bin/env python3
"""Uji Stop lalu Apply pada wallpaper VIDEO, sambil mengukur jeda hitam.

Ini keluhan aslinya: "dari aturan stop wallpaper trs apply ulang terdapat jeda
hitam yg sangat cukup lama".

Pemeriksaan versi sebelumnya memakai wallpaper statis, dan untuk wallpaper statis
"Hentikan" memang tidak mengubah apa pun - jadi uji itu tidak pernah menyentuh
jalur yang dikeluhkan. Di sini wallpapernya video, supaya perpindahan
stop-ke-apply benar-benar terjadi.

Cara kerjanya:

  1. aplikasi dijalankan dengan wallpaper video, dan ditunggu sampai tergambar
  2. jendela aplikasi dipindahkan keluar dari layar uji, supaya yang terukur
     benar-benar wallpapernya dan bukan antarmuka aplikasinya
  3. Hentikan ditekan, lalu Terapkan ditekan, sementara kecerahan dipantau

Yang dicari adalah penurunan ke nyaris nol di antara kedua tekanan itu. Video
boleh gelap pada suatu frame; layar kosong tidak.

Pemakaian:
  python tools/check-stop-apply-video.py --display DISPLAY3
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ukur_layar  # noqa: E402

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)

CONFIG = Path('C:/Users/ariel/AppData/Local/LumaWall/config.json')


class Pengukur(threading.Thread):
    def __init__(self, monitor, jeda=0.1):
        super().__init__(daemon=True)
        self.monitor = monitor
        self.jeda = jeda
        self.jalan = True
        self.contoh = []

    def run(self):
        mulai = time.time()
        while self.jalan:
            n = ukur_layar.baca(self.monitor)
            if n is not None:
                self.contoh.append((time.time() - mulai, n))
            time.sleep(self.jeda)

    def hentikan(self):
        self.jalan = False
        self.join(timeout=3)


def tekan(nama, waktu_tunggu=25):
    skrip = (
        "Add-Type -AssemblyName UIAutomationClient;"
        "$w = [System.Windows.Automation.AutomationElement]::RootElement;"
        "$c = New-Object System.Windows.Automation.PropertyCondition("
        "[System.Windows.Automation.AutomationElement]::NameProperty, 'LumaWall');"
        "$win = $w.FindFirst([System.Windows.Automation.TreeScope]::Children, $c);"
        "if (-not $win) { Write-Output 'NO_WINDOW'; exit }"
        "$b = New-Object System.Windows.Automation.PropertyCondition("
        "[System.Windows.Automation.AutomationElement]::NameProperty, '%s');"
        "$el = $win.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $b);"
        "if (-not $el) { Write-Output 'NO_BUTTON'; exit }"
        "try {"
        "  $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke();"
        "  Write-Output 'OK'"
        "} catch { Write-Output 'NO_PATTERN' }"
    ) % nama
    r = subprocess.run(['powershell', '-NoProfile', '-Command', skrip],
                       capture_output=True, text=True, timeout=waktu_tunggu)
    return (r.stdout or '').strip() == 'OK'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--display', default='DISPLAY3')
    args = ap.parse_args()

    monitor = ukur_layar.pilih(args.display)
    if monitor is None:
        print('  layar %s tidak ditemukan' % args.display)
        return 1

    print()
    print('  ══ Stop lalu Apply pada VIDEO (%s) ══' % args.display)
    print()

    cfg = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    video = None
    for p in (cfg.get('Library') or []):
        s = str(p)
        if s.lower().endswith(('.mp4', '.webm', '.mkv', '.mov')) and Path(s).exists():
            video = Path(s)
            break
    if video is None:
        print('  ! tidak ada video di library')
        return 1
    print('  video: %s' % video.name)
    print()

    for item in (cfg.get('MonitorVideos') or []):
        if isinstance(item, dict) and args.display in str(item.get('Key', '')):
            item['Value'] = str(video)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')

    ukur_layar.jalankan_app()

    if not ukur_layar.bersihkan_layar(monitor):
        print('  ! layar uji tidak bisa dibersihkan - pengukuran tidak sah')
        return 1

    if ukur_layar.tunggu_tergambar(monitor) is None:
        print('  ! wallpaper video tidak pernah tergambar')
        return 1
    time.sleep(3)
    print('  wallpaper tergambar (%.1f)' % ukur_layar.baca(monitor))
    print()

    # Buka halaman Displays supaya tombolnya ada.
    if not tekan('Displays'):
        print('  ! halaman Displays tidak bisa dibuka')
        return 1
    time.sleep(2.5)

    # Tombolnya bernama "Stop" pada antarmuka Inggris dan "Hentikan" pada
    # antarmuka Indonesia, dan bahasanya bisa berubah kapan saja. Mencari satu
    # nama saja membuat pemeriksaan ini gagal karena hal yang tidak ada
    # hubungannya dengan yang diuji.
    def tekan_salah_satu(nama_inggris, nama_indonesia):
        for nama in (nama_inggris, nama_indonesia):
            if tekan(nama):
                return nama
        return None

    ukur = Pengukur(monitor)
    ukur.start()
    try:
        print('  ── menekan Stop ──')
        dipakai = tekan_salah_satu('Stop', 'Hentikan')
        if dipakai is None:
            print('     ! tombol Stop tidak ditemukan')
            return 1
        print('     \u2713 "%s" ditekan' % dipakai)
        time.sleep(3)

        tengah = ukur_layar.baca(monitor)
        print('     kecerahan setelah Stop: %.1f' % tengah)
        if tengah < 8:
            print('     \u2717 LAYAR HITAM setelah Stop - frame terakhir hilang')
            return 1
        print('     \u2713 frame terakhir masih terlihat')
        print()

        print('  ── menekan Apply ──')
        dipakai2 = tekan_salah_satu('Apply', 'Terapkan')
        if dipakai2 is None:
            print('     ! tombol Apply tidak ditemukan')
            return 1
        print('     \u2713 ditekan')
        time.sleep(9)
    finally:
        time.sleep(0.4)
        ukur.hentikan()

    print()
    print('  ── hasil pengukuran ──')
    if not ukur.contoh:
        print('     ! tidak ada sampel')
        return 1

    nol = [t for t, n in ukur.contoh if n < 8]
    print('     %d sampel selama %.1f detik' % (len(ukur.contoh), ukur.contoh[-1][0]))
    print('     kecerahan: min %.1f, rata-rata %.1f, maks %.1f'
          % (min(n for _, n in ukur.contoh),
             statistics.mean(n for _, n in ukur.contoh),
             max(n for _, n in ukur.contoh)))
    print()
    if nol:
        print('     \u2717 ADA %d sampel nyaris hitam (%.1f detik)'
              % (len(nol), nol[-1] - nol[0]))
        print('       pada detik: %s' % ', '.join('%.1f' % t for t in nol[:10]))
        return 1
    print('  \u2713 tidak ada jeda hitam: kecerahan tidak pernah turun ke nyaris nol')
    return 0


if __name__ == '__main__':
    sys.exit(main())
