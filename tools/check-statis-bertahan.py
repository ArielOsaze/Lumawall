#!/usr/bin/env python3
"""Pantau wallpaper statis setelah aplikasinya dipindahkan dari layar uji.

Dua kesalahan pengukuran yang sudah terjadi dan dicegah di sini:

  1. Jendela aplikasi LumaWall sendiri bisa berdiri di atas layar yang diukur.
     Titik sampelnya lalu jatuh di dalam jendela itu, dan yang terbaca adalah
     warna antarmuka aplikasi - terang, diam, dan selalu "terlihat baik" apa
     pun yang dilakukan wallpapernya. Jendela aplikasi karena itu dipindahkan
     lebih dulu, dan perpindahannya diverifikasi.

  2. Beberapa detik pertama setelah aplikasi dijalankan memang belum ada yang
     menggambar. Menghitung itu sebagai kegagalan akan membuat pemeriksaan ini
     selalu gagal, jadi yang diperiksa adalah apakah wallpaper, setelah muncul,
     tetap ada.

Pemakaian:
  python tools/check-statis-bertahan.py --display DISPLAY3
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_screen  # noqa: E402

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)

CONFIG = Path('C:/Users/ariel/AppData/Local/LumaWall/config.json')
APP = 'C:/Users/ariel/AppData/Local/Programs/LumaWall/LumaWall.exe'
GAMBAR = 'C:/Users/ariel/AppData/Local/LumaWall/Wallpapers/uji-statis-terang.png'


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def pilih_monitor(nama):
    for m in test_screen.monitors():
        if nama in (m.get('device') or ''):
            return m
    return None


def pid_aplikasi():
    keluaran = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "(Get-Process LumaWall -ErrorAction SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle } | Select-Object -First 1).Id"],
        capture_output=True, text=True, timeout=30).stdout
    for t in keluaran.split():
        if t.strip().isdigit():
            return int(t.strip())
    return None


def jendela_di(monitor, pid):
    """Jendela besar milik proses ini yang menutupi layar yang diukur."""
    hasil = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value != pid:
            return True
        if not user32.IsWindowVisible(hwnd):
            return True
        r = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        lebar, tinggi = r.right - r.left, r.bottom - r.top
        if lebar < 200 or tinggi < 150:
            return True
        if (r.left < monitor['x'] + monitor['width'] and r.right > monitor['x']
                and r.top < monitor['y'] + monitor['height'] and r.bottom > monitor['y']):
            hasil.append(int(hwnd))
        return True

    user32.EnumWindows(cb, 0)
    return sorted(set(hasil))


def pindahkan(hwnd, x=-3000, y=60, lebar=1400, tinggi=860):
    SWP_NOZORDER, SWP_NOACTIVATE = 0x0004, 0x0010
    return bool(user32.SetWindowPos(hwnd, 0, x, y, lebar, tinggi, SWP_NOZORDER | SWP_NOACTIVATE))


def baca(mon):
    hdc = user32.GetDC(None)
    if not hdc:
        return None
    try:
        nilai = []
        for fx, fy in ((0.5, 0.5), (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
            x = mon['x'] + int(mon['width'] * fx)
            y = mon['y'] + int(mon['height'] * fy)
            w = gdi32.GetPixel(hdc, x, y)
            if w == 0xFFFFFFFF:
                continue
            r, g, b = w & 0xFF, (w >> 8) & 0xFF, (w >> 16) & 0xFF
            nilai.append(0.299 * r + 0.587 * g + 0.114 * b)
        return statistics.mean(nilai) if nilai else None
    finally:
        user32.ReleaseDC(None, hdc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--display', default='DISPLAY3')
    ap.add_argument('--detik', type=int, default=25)
    args = ap.parse_args()

    monitor = pilih_monitor(args.display)
    if monitor is None:
        print('  layar %s tidak ditemukan' % args.display)
        return 1
    if not Path(GAMBAR).exists():
        print('  ! gambar uji tidak ada: %s' % GAMBAR)
        return 1

    print()
    print('  ══ wallpaper statis bertahan? (%s, %d detik) ══' % (args.display, args.detik))
    print()

    cfg = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    for item in (cfg.get('MonitorVideos') or []):
        if isinstance(item, dict) and args.display in str(item.get('Key', '')):
            item['Value'] = GAMBAR
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')

    subprocess.run(['powershell', '-NoProfile', '-Command',
                    'Stop-Process -Name LumaWall -Force -ErrorAction SilentlyContinue'],
                   capture_output=True, timeout=60)
    time.sleep(4)
    subprocess.Popen(['powershell', '-NoProfile', '-Command', 'Start-Process "%s"' % APP],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(18)

    # Pindahkan jendela aplikasi keluar dari layar uji, lalu pastikan pindah.
    pid = pid_aplikasi()
    if pid is None:
        print('  ! aplikasi tidak berjalan')
        return 1

    penutup = jendela_di(monitor, pid)
    if not penutup:
        print('  tidak ada jendela aplikasi yang menutupi %s' % args.display)
    else:
        for h in penutup:
            r = RECT()
            user32.GetWindowRect(h, ctypes.byref(r))
            print('  memindahkan hwnd %d dari (%d,%d) %dx%d'
                  % (h, r.left, r.top, r.right - r.left, r.bottom - r.top))
            if not pindahkan(h):
                print('     ! gagal memindahkan (err=%d)' % ctypes.get_last_error())
        time.sleep(2)
        masih = jendela_di(monitor, pid)
        if masih:
            print('     ! masih ada %d jendela di layar uji - pengukuran tidak sah' % len(masih))
            return 1
        print('     \u2713 layar uji bersih')
    print()

    print('  gambar uji hijau terang (~154); desktop di baliknya ~15')
    print()
    semua = []
    for i in range(args.detik):
        n = baca(monitor)
        semua.append(n)
        tanda = '   <-- TURUN' if (i > 0 and semua[i - 1] - n > 40) else ''
        print('  t=%2ds  %6.1f%s' % (i, n, tanda))
        time.sleep(1)

    terlihat = [n for n in semua if n > 100]
    print()
    if not terlihat:
        print('  \u2717 wallpaper statis tidak pernah terlihat (maksimum %.1f)' % max(semua))
        return 1

    mulai = semua.index(terlihat[0])
    sesudah = semua[mulai:]
    print('  muncul pada detik %d, lalu dipantau %d detik' % (mulai, len(sesudah)))
    print('  minimum %.1f   maksimum %.1f' % (min(sesudah), max(sesudah)))
    print()
    if min(sesudah) > 100:
        print('  \u2713 wallpaper statis tetap terlihat sepanjang %d detik' % len(sesudah))
        return 0
    print('  \u2717 wallpaper statis hilang setelah terlihat (turun ke %.1f)' % min(sesudah))
    return 1


if __name__ == '__main__':
    sys.exit(main())
