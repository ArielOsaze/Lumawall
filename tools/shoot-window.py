#!/usr/bin/env python3
"""Tangkap jendela aplikasi lewat PrintWindow, langsung dari Python.

CopyFromScreen menyalin apa yang ada di LAYAR, jadi ia gagal ketika jendelanya
baru ditampilkan (isinya belum digambar -> bidang hitam) atau ketika ada jendela
lain di atasnya. PrintWindow meminta jendelanya menggambar dirinya sendiri, jadi
hasilnya tidak bergantung pada keadaan layar.

Pemakaian:
  python tools/shoot-window.py --keluar build/ui.png [--tampilkan]
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time
from pathlib import Path

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG),
        ('biPlanes', wt.WORD), ('biBitCount', wt.WORD),
        ('biCompression', wt.DWORD), ('biSizeImage', wt.DWORD),
        ('biXPelsPerMeter', wt.LONG), ('biYPelsPerMeter', wt.LONG),
        ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wt.DWORD * 3)]


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def pid_lumawall():
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         '(Get-Process LumaWall -EA SilentlyContinue).Id'],
        capture_output=True, text=True, timeout=30)
    return set(int(x) for x in r.stdout.split() if x.strip().isdigit())


def jendela_utama():
    pids = pid_lumawall()
    hasil = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value not in pids:
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, cls, 256)
        if not cls.value.startswith('HwndWrapper'):
            return True
        r = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return True
        w, h = r.right - r.left, r.bottom - r.top
        if w < 700 or h < 500:
            return True
        hasil.append((int(hwnd), w, h))
        return True

    user32.EnumWindows(cb, 0)
    if not hasil:
        return None
    return sorted(hasil, key=lambda t: -t[1] * t[2])[0][0]


def tangkap(hwnd, keluar):
    """PrintWindow(PW_RENDERFULLCONTENT) -> PNG, sepenuhnya di Python."""
    r = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        return None

    hdc_jendela = user32.GetWindowDC(hwnd)
    if not hdc_jendela:
        return None

    hdc_memori = gdi32.CreateCompatibleDC(hdc_jendela)
    bitmap = gdi32.CreateCompatibleBitmap(hdc_jendela, w, h)
    if not hdc_memori or not bitmap:
        gdi32.DeleteDC(hdc_memori)
        user32.ReleaseDC(hwnd, hdc_jendela)
        return None

    gdi32.SelectObject(hdc_memori, bitmap)

    # 2 = PW_RENDERFULLCONTENT. Tanpa ini, jendela yang memakai komposisi
    # DirectComposition menghasilkan bitmap kosong.
    user32.PrintWindow(hwnd, hdc_memori, 2)

    # Bitmap GDI -> byte BGRA, dibaca lewat GetDIBits.
    bi = BITMAPINFO()
    bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.bmiHeader.biWidth = w
    bi.bmiHeader.biHeight = -h          # negatif = baris dari atas ke bawah
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    bi.bmiHeader.biCompression = 0      # BI_RGB

    panjang = w * h * 4
    buffer = (ctypes.c_char * panjang)()
    baris = gdi32.GetDIBits(hdc_memori, bitmap, 0, h, buffer, ctypes.byref(bi), 0)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(hdc_memori)
    user32.ReleaseDC(hwnd, hdc_jendela)

    if baris == 0:
        return None

    # Ditulis lewat PNG encoder milik WPF/PowerShell yang sudah ada, supaya tidak
    # bergantung pada Pillow yang belum tentu terpasang.
    bmp = keluar.with_suffix('.bmp')
    with open(bmp, 'wb') as f:
        # BMP header
        ukuran_header = 14 + 40
        f.write(b'BM')
        f.write((ukuran_header + panjang).to_bytes(4, 'little'))
        f.write((0).to_bytes(4, 'little'))
        f.write(ukuran_header.to_bytes(4, 'little'))
        f.write(ctypes.string_at(ctypes.byref(bi.bmiHeader), 40))
        f.write(ctypes.string_at(buffer, panjang))

    # BMP -> PNG
    ps = (
        "Add-Type -AssemblyName System.Drawing;"
        "$b = [System.Drawing.Image]::FromFile('%s');"
        "$b.Save('%s', [System.Drawing.Imaging.ImageFormat]::Png);"
        "$b.Dispose();" % (str(bmp.resolve()).replace('\\', '\\\\'),
                           str(keluar.resolve()).replace('\\', '\\\\'))
    )
    subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                   capture_output=True, text=True, timeout=90)
    try:
        bmp.unlink()
    except Exception:
        pass

    return (w, h) if keluar.exists() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keluar', default='build/ui.png')
    ap.add_argument('--tampilkan', action='store_true')
    args = ap.parse_args()

    hwnd = jendela_utama()
    if hwnd is None:
        print('  ! jendela LumaWall tidak ditemukan')
        return 1

    if args.tampilkan and not user32.IsWindowVisible(hwnd):
        user32.ShowWindow(hwnd, 9)
        user32.ShowWindow(hwnd, 5)
        time.sleep(1.5)

    keluar = Path(args.keluar)
    keluar.parent.mkdir(parents=True, exist_ok=True)

    ukuran = tangkap(hwnd, keluar)
    if ukuran:
        print('  disimpan: %s  %dx%d  (%.0f KB)'
              % (keluar, ukuran[0], ukuran[1], keluar.stat().st_size / 1024))
        return 0
    print('  ! gagal menangkap')
    return 1


if __name__ == '__main__':
    sys.exit(main())
