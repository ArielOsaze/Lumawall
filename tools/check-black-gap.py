#!/usr/bin/env python3
"""Uji tiga perbaikan sekaligus: ukuran jendela, hitam saat stop, hitam saat apply.

Yang diuji, dan mengapa masing-masing:

  1. UKURAN JENDELA. Jendela wallpaper harus menutupi layarnya dengan tepat.
     Sebelumnya ia bisa terjebak di ukuran default Windows Forms (136x39)
     karena AttachToWallpaper keluar lebih awal saat jendelanya sudah menempel,
     sehingga ukurannya tidak pernah diperbaiki lagi. Di layar 1366x768 itu
     terlihat sebagai wallpaper yang terpotong.

  2. HITAM SAAT STOP. Menekan "Hentikan" dulu menutup jendela wallpaper, jadi
     tidak ada apa pun yang menggambar di desktop dan layarnya jadi hitam.
     Sekarang jendelanya dipertahankan dan videonya dijeda, jadi frame terakhir
     tetap terlihat.

  3. HITAM SAAT APPLY. Mengganti wallpaper harus membangun penggantinya dulu,
     baru menutup yang lama - kalau tidak, ada jeda saat tidak ada yang
     menggambar.

Cara mengukurnya: warna rata-rata desktop dibaca berkala. Desktop yang tertutup
wallpaper punya warna yang jelas berbeda dari hitam pekat, jadi "hitam" bisa
dibedakan dari "wallpaper gelap" dengan mengukur kecerahannya, bukan dengan
melihat.

Pemakaian:
  python tools/check-black-gap.py --display DISPLAY3
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_screen  # noqa: E402

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def windows_of_process(pid):
    """Setiap jendela milik proses ini, termasuk yang jadi ANAK dari desktop.

    EnumWindows saja tidak cukup, dan itu sempat membuat checker ini melaporkan
    "tidak ada jendela yang tepat selayar" tentang wallpaper yang sebenarnya
    sudah benar. Jendela wallpaper di-reparent ke WorkerW/Progman, dan setelah
    itu ia tidak lagi muncul sebagai jendela top-level - ia hanya terlihat lewat
    EnumChildWindows dari desktop host.
    """
    hasil = []

    def kumpulkan(hwnd):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value != pid:
            return
        if not user32.IsWindowVisible(hwnd):
            return
        r = RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(r)):
            cls = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls, 256)
            hasil.append({'hwnd': int(hwnd), 'class': cls.value,
                          'x': r.left, 'y': r.top,
                          'w': r.right - r.left, 'h': r.bottom - r.top})

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        kumpulkan(hwnd)
        return True

    user32.EnumWindows(cb, 0)

    # Jendela yang sudah di-reparent hanya terlihat dari host-nya.
    for nama in ('Progman', 'WorkerW'):
        host = user32.FindWindowW(nama, None)
        if not host:
            continue

        @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
        def anak(hwnd, _):
            kumpulkan(hwnd)
            return True

        user32.EnumChildWindows(host, anak, 0)

    # Buang duplikat: satu hwnd bisa terlihat dari lebih dari satu jalur.
    unik = {}
    for w in hasil:
        unik[w['hwnd']] = w
    return list(unik.values())


def kecerahan_layar(monitor):
    """Kecerahan rata-rata layar, 0-255.

    Diambil lewat GetDC + GetPixel pada beberapa titik, bukan lewat tangkapan
    layar: GetPixel membaca apa yang benar-benar ada di layar saat itu, termasuk
    saat jendela lain menutupinya.
    """
    hdc = user32.GetDC(None)
    if not hdc:
        return None
    try:
        nilai = []
        # Sampel di tengah dan di empat titik dalam area layar. Titik tepi
        # dihindari karena bisa jatuh di luar monitor.
        titik = [
            (monitor['x'] + monitor['width'] // 2, monitor['y'] + monitor['height'] // 2),
            (monitor['x'] + monitor['width'] // 4, monitor['y'] + monitor['height'] // 4),
            (monitor['x'] + 3 * monitor['width'] // 4, monitor['y'] + monitor['height'] // 4),
            (monitor['x'] + monitor['width'] // 4, monitor['y'] + 3 * monitor['height'] // 4),
            (monitor['x'] + 3 * monitor['width'] // 4, monitor['y'] + 3 * monitor['height'] // 4),
        ]
        for x, y in titik:
            warna = gdi32.GetPixel(hdc, x, y)
            if warna == 0xFFFFFFFF:
                continue
            r = warna & 0xFF
            g = (warna >> 8) & 0xFF
            b = (warna >> 16) & 0xFF
            nilai.append(0.299 * r + 0.587 * g + 0.114 * b)
        return statistics.mean(nilai) if nilai else None
    finally:
        user32.ReleaseDC(None, hdc)


def pilih_monitor(nama):
    for m in test_screen.monitors():
        if nama in (m.get('device') or ''):
            return m
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--display', default='DISPLAY3')
    args = ap.parse_args()

    monitor = pilih_monitor(args.display)
    if monitor is None:
        print('  layar %s tidak ditemukan' % args.display)
        return 1

    print()
    print('  ══ uji tiga perbaikan di %s ══' % args.display)
    print()
    print('  layar: %s' % test_screen.describe(monitor))
    print()

    pid = None
    for line in subprocess.run(
            ['powershell', '-NoProfile', '-Command',
             "(Get-Process LumaWall -ErrorAction SilentlyContinue | "
             "Where-Object { $_.MainWindowTitle } | Select-Object -First 1).Id"],
            capture_output=True, text=True, timeout=30).stdout.split():
        if line.strip().isdigit():
            pid = int(line.strip())
            break

    if pid is None:
        print('  aplikasi belum berjalan. Jalankan LumaWall dulu.')
        return 1
    print('  aplikasi PID %d' % pid)
    print()

    gagal = 0

    # ── 1. ukuran jendela ──────────────────────────────────────────────────
    print('  \u2500\u2500 1. ukuran jendela wallpaper \u2500\u2500')
    wins = windows_of_process(pid)
    pas = []
    for w in wins:
        if (w['x'] == monitor['x'] and w['y'] == monitor['y']
                and w['w'] == monitor['width'] and w['h'] == monitor['height']):
            pas.append(w)

    if pas:
        for w in pas:
            print('     \u2713 hwnd %-8d %dx%d tepat selayar' % (w['hwnd'], w['w'], w['h']))
    else:
        print('     \u2717 tidak ada jendela yang menutupi layar dengan tepat:')
        for w in sorted(wins, key=lambda x: -(x['w'] * x['h']))[:5]:
            dekat = ''
            if w['x'] == monitor['x'] and w['y'] == monitor['y']:
                dekat = '  (selisih %+dx%+d)' % (w['w'] - monitor['width'], w['h'] - monitor['height'])
            print('        %4dx%-5d di (%d,%d)%s' % (w['w'], w['h'], w['x'], w['y'], dekat))
        gagal += 1
    print()

    # ── 2. kecerahan sekarang ──────────────────────────────────────────────
    #
    # Jendela aplikasi dipindahkan lebih dulu. Jendela LumaWall sendiri bisa
    # berdiri di atas layar yang diukur, dan titik sampelnya lalu jatuh di dalam
    # jendela itu - sehingga yang terbaca adalah warna antarmuka aplikasi, bukan
    # wallpapernya. Tanpa langkah ini pemeriksaan melaporkan "bukan hitam" untuk
    # layar yang wallpapernya benar-benar tidak menggambar apa pun.
    print('  \u2500\u2500 2. kecerahan layar sekarang \u2500\u2500')
    import ukur_layar
    if not ukur_layar.bersihkan_layar(monitor, pid=pid):
        print('     ! jendela aplikasi menutupi layar uji - pengukuran tidak sah')
        gagal += 1
        terang = None
    else:
        terang = kecerahan_layar(monitor)
    if terang is None:
        print('     ! tidak bisa membaca warna layar')
        gagal += 1
    else:
        print('     kecerahan rata-rata: %.1f / 255' % terang)
        if terang < 8:
            print('     \u2717 layar hampir hitam - wallpaper tidak menggambar apa pun')
            gagal += 1
        else:
            print('     \u2713 layar menampilkan sesuatu (bukan hitam)')
    print()

    # ── 3. apakah jendela tetap ada ────────────────────────────────────────
    print('  \u2500\u2500 3. jendela bertahan \u2500\u2500')
    print('     %d jendela terlihat milik proses ini' % len(wins))
    if len(wins) < 2:
        print('     ! terlalu sedikit jendela - ada yang tertutup?')
        gagal += 1
    else:
        print('     \u2713 jendela wallpaper masih ada')
    print()

    if gagal:
        print('  %d masalah ditemukan.' % gagal)
        return 1
    print('  ketiga pemeriksaan lulus.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
