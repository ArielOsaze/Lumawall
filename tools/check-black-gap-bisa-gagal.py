#!/usr/bin/env python3
"""Buktikan check-stop-apply.py bisa GAGAL, bukan hanya bisa lulus.

Ini bagian yang paling mudah dilewatkan: pemeriksaan yang selalu lulus tidak
membuktikan apa-apa. Uji ini menjalankan pemeriksaannya terhadap perilaku LAMA
yang bermasalah, dan mengharapkannya menangkap masalahnya.

Caranya tanpa mengubah aplikasi: jendela wallpaper ditutup paksa dari luar,
persis seperti yang dilakukan StopMonitor dulu. Kalau check-stop-apply.py
menganggap itu sebagai masalah, berarti pemeriksaannya benar-benar mengukur
sesuatu.

Pemakaian:
  python tools/check-black-gap-bisa-gagal.py --display DISPLAY3
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_screen  # noqa: E402

user32 = ctypes.WinDLL('user32', use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def pilih_monitor(nama):
    for m in test_screen.monitors():
        if nama in (m.get('device') or ''):
            return m
    return None


def pid_aplikasi():
    out = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "(Get-Process LumaWall -ErrorAction SilentlyContinue | "
         "Where-Object { $_.MainWindowTitle } | Select-Object -First 1).Id"],
        capture_output=True, text=True, timeout=30).stdout
    for t in out.split():
        if t.strip().isdigit():
            return int(t.strip())
    return None


def jendela_wallpaper(pid, monitor):
    """Jendela wallpaper yang menutupi layar yang dimaksud."""
    hasil = []

    def kumpulkan(hwnd):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value != pid:
            return
        r = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        if (r.left == monitor['x'] and r.top == monitor['y']
                and r.right - r.left == monitor['width']
                and r.bottom - r.top == monitor['height']):
            hasil.append(int(hwnd))

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        kumpulkan(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    for nama in ('Progman', 'WorkerW'):
        host = user32.FindWindowW(nama, None)
        if host:
            user32.EnumChildWindows(host, cb, 0)
    return sorted(set(hasil))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--display', default='DISPLAY3')
    args = ap.parse_args()

    monitor = pilih_monitor(args.display)
    if monitor is None:
        print('  layar %s tidak ditemukan' % args.display)
        return 1

    print()
    print('  ══ buktikan pemeriksaan bisa gagal ══')
    print()

    pid = pid_aplikasi()
    if pid is None:
        print('  aplikasi belum berjalan')
        return 1

    jendela = jendela_wallpaper(pid, monitor)
    print('  jendela wallpaper di %s: %d' % (args.display, len(jendela)))
    if not jendela:
        print('  ! tidak ada jendela wallpaper; pasang dulu satu di layar ini')
        return 1
    for h in jendela:
        print('     hwnd %d' % h)
    print()

    # Perlakukan seperti perilaku lama: sembunyikan jendela wallpaper.
    # Disembunyikan, bukan ditutup - supaya aplikasinya tidak kehilangan
    # jendelanya secara permanen dan masih bisa melanjutkan uji.
    print('  ── menyembunyikan jendela wallpaper (perilaku lama) ──')
    for h in jendela:
        user32.ShowWindow(h, 0)  # SW_HIDE
    print('     %d jendela disembunyikan' % len(jendela))
    time.sleep(2)
    print()

    print('  ── menjalankan pemeriksaan terhadap keadaan itu ──')
    r = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / 'check-stop-apply.py'),
         '--display', args.display],
        capture_output=True, text=True, timeout=180)

    keluaran = r.stdout + r.stderr
    for baris in keluaran.splitlines():
        if 'kecerahan' in baris or 'hitam' in baris or '\u2717' in baris:
            print('     %s' % baris.strip())
    print()

    # Kembalikan seperti semula, apa pun hasilnya.
    for h in jendela:
        user32.ShowWindow(h, 5)  # SW_SHOW
    time.sleep(1)

    if r.returncode != 0:
        print('  \u2713 pemeriksaan MENANGKAP masalahnya (keluar dengan kode %d)' % r.returncode)
        print('    Berarti pemeriksaan itu benar-benar mengukur, bukan selalu lulus.')
        return 0

    print('  \u2717 pemeriksaan tetap LULUS padahal jendelanya disembunyikan')
    print('    Berarti pemeriksaan itu tidak mengukur apa yang diklaimnya.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
