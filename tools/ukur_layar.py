#!/usr/bin/env python3
"""Alat ukur layar yang tidak bisa tertipu oleh jendela aplikasi sendiri.

Dua kesalahan pengukuran pernah terjadi berulang kali, dan keduanya menghasilkan
laporan "semuanya baik" untuk keadaan yang sebenarnya rusak. Keduanya dicegah di
sini, sekali, supaya tidak perlu diingat lagi oleh setiap pemeriksa:

  1. JENDELA APLIKASI SENDIRI MENUTUPI LAYAR YANG DIUKUR.
     Jendela LumaWall bisa berdiri di atas layar uji, dan titik sampelnya jatuh
     di dalam jendela itu. Yang terbaca lalu adalah warna antarmuka aplikasi -
     terang, diam, dan selalu tampak benar. Setiap pengukuran karena itu
     memindahkan jendela aplikasi lebih dulu dan MEMVERIFIKASI bahwa layarnya
     benar-benar bersih sebelum membaca apa pun.

  2. WARNA YANG DIBACA TIDAK DIKETAHUI.
     "Terang" tidak berarti "wallpaper benar". Pemeriksa yang memakai gambar uji
     harus membandingkan dengan warna gambar itu, bukan dengan ambang sembarang,
     supaya wallpaper yang salah pun tidak lolos.

Isi modul ini:

  RECT                     struct Windows untuk koordinat jendela
  monitors()               daftar layar (dari test_screen)
  pid_aplikasi()           PID proses LumaWall yang punya jendela utama
  jendela_di(mon, pid)     jendela besar milik pid yang menutupi layar itu
  bersihkan_layar(mon)     pindahkan jendela aplikasi keluar; True kalau bersih
  baca(mon)                kecerahan rata-rata layar, 0-255
  baca_warna(mon)          daftar warna heksadesimal di titik sampel
  tunggu_tergambar(mon)    tunggu sampai layar tidak kosong, kembalikan detiknya
"""
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

# Layar yang benar-benar kosong terbaca di bawah nilai ini. Dipakai untuk
# membedakan "belum ada yang menggambar" dari "ada yang menggambar gelap".
AMBANG_KOSONG = 8


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def monitors():
    return test_screen.monitors()


def pilih(nama):
    """Layar berdasarkan namanya, misalnya 'DISPLAY3'."""
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


def semua_pid_aplikasi():
    """Semua PID proses LumaWall."""
    keluaran = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         '(Get-Process LumaWall -ErrorAction SilentlyContinue).Id'],
        capture_output=True, text=True, timeout=30).stdout
    hasil = set()
    for t in keluaran.split():
        if t.strip().isdigit():
            hasil.add(int(t.strip()))
    return hasil


def jendela_di(monitor, pid, min_lebar=200, min_tinggi=150):
    """Jendela besar milik pid yang menutupi layar ini."""
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
        if (r.right - r.left) < min_lebar or (r.bottom - r.top) < min_tinggi:
            return True
        if (r.left < monitor['x'] + monitor['width'] and r.right > monitor['x']
                and r.top < monitor['y'] + monitor['height'] and r.bottom > monitor['y']):
            hasil.append(int(hwnd))
        return True

    user32.EnumWindows(cb, 0)
    return sorted(set(hasil))


def bersihkan_layar(monitor, pid=None, x=-3000, y=60, lebar=1400, tinggi=860, verbose=True):
    """Pindahkan jendela aplikasi keluar dari layar ini.

    Mengembalikan True kalau layarnya benar-benar bersih sesudahnya. Kalau tidak
    bersih, pengukuran apa pun di layar ini tidak sah dan pemanggilnya harus
    berhenti - bukan melanjutkan dan melaporkan angka yang menyesatkan.
    """
    if pid is None:
        pid = pid_aplikasi()
    if pid is None:
        return False

    SWP_NOZORDER, SWP_NOACTIVATE = 0x0004, 0x0010
    penutup = jendela_di(monitor, pid)
    if not penutup:
        return True

    for h in penutup:
        r = RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        if verbose:
            print('     memindahkan hwnd %d dari (%d,%d) %dx%d'
                  % (h, r.left, r.top, r.right - r.left, r.bottom - r.top))
        user32.SetWindowPos(h, 0, x, y, lebar, tinggi, SWP_NOZORDER | SWP_NOACTIVATE)

    time.sleep(2)
    masih = jendela_di(monitor, pid)
    if masih:
        if verbose:
            print('     ! %d jendela masih menutupi layar uji' % len(masih))
        return False
    if verbose:
        print('     \u2713 layar uji bersih')
    return True


def baca(monitor):
    """Kecerahan rata-rata layar, 0-255."""
    hdc = user32.GetDC(None)
    if not hdc:
        return None
    try:
        nilai = []
        for fx, fy in ((0.5, 0.5), (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
            x = monitor['x'] + int(monitor['width'] * fx)
            y = monitor['y'] + int(monitor['height'] * fy)
            w = gdi32.GetPixel(hdc, x, y)
            if w == 0xFFFFFFFF:
                continue
            r, g, b = w & 0xFF, (w >> 8) & 0xFF, (w >> 16) & 0xFF
            nilai.append(0.299 * r + 0.587 * g + 0.114 * b)
        return statistics.mean(nilai) if nilai else None
    finally:
        user32.ReleaseDC(None, hdc)


def baca_warna(monitor):
    """Warna di titik sampel, sebagai '#RRGGBB'."""
    hdc = user32.GetDC(None)
    if not hdc:
        return []
    try:
        warna = []
        for fx, fy in ((0.5, 0.5), (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
            x = monitor['x'] + int(monitor['width'] * fx)
            y = monitor['y'] + int(monitor['height'] * fy)
            w = gdi32.GetPixel(hdc, x, y)
            if w == 0xFFFFFFFF:
                continue
            warna.append('#%02X%02X%02X' % (w & 0xFF, (w >> 8) & 0xFF, (w >> 16) & 0xFF))
        return warna
    finally:
        user32.ReleaseDC(None, hdc)


def tunggu_tergambar(monitor, batas=40, ambang=AMBANG_KOSONG):
    """Tunggu sampai layar tidak kosong. Kembalikan detik yang dibutuhkan, atau None."""
    for i in range(batas):
        n = baca(monitor)
        if n is not None and n > ambang:
            return i
        time.sleep(1)
    return None


def jalankan_app(tunggu=18):
    subprocess.run(['powershell', '-NoProfile', '-Command',
                    'Stop-Process -Name LumaWall -Force -ErrorAction SilentlyContinue'],
                   capture_output=True, timeout=60)
    time.sleep(4)
    subprocess.Popen(['powershell', '-NoProfile', '-Command',
                      'Start-Process "%s"'
                      % 'C:/Users/ariel/AppData/Local/Programs/LumaWall/LumaWall.exe'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(tunggu)
