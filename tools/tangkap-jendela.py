#!/usr/bin/env python3
"""Tangkap halaman aplikasi dengan PrintWindow - tanpa menyentuh layar pengguna.

KENAPA ALAT INI ADA:

CopyFromScreen menyalin apa yang terlihat di layar FISIK. Untuk melihat halaman
katalog, itu berarti jendela aplikasi harus benar-benar terlihat di salah satu
monitor - dan kalau jendela dipindah ke monitor yang tidak menyala, hasilnya
hitam. Itu yang terjadi sebelumnya: "tangkapan hampir seluruhnya hitam".

PrintWindow berbeda: ia meminta JENDELA menggambar dirinya sendiri ke sebuah
bitmap, tanpa peduli apakah jendela itu terlihat, tertutup jendela lain, atau
berada di monitor yang mana. Jadi layar pengguna tidak perlu disentuh sama
sekali - dan itu penting karena pengguna sedang bekerja di layar utama.

PW_RENDERFULLCONTENT (0x00000002) diperlukan untuk jendela yang isinya
digambar lewat DirectComposition - tanpa bendera itu, WebView2 dan sebagian
permukaan WPF menghasilkan hitam.
"""

import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time
from pathlib import Path

user32 = ctypes.WinDLL('user32', use_last_error=True)
gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)

PW_RENDERFULLCONTENT = 0x00000002
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG),
                ('biPlanes', wt.WORD), ('biBitCount', wt.WORD),
                ('biCompression', wt.DWORD), ('biSizeImage', wt.DWORD),
                ('biXPelsPerMeter', wt.LONG), ('biYPelsPerMeter', wt.LONG),
                ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wt.DWORD * 3)]


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def pids():
    r = subprocess.run(['powershell', '-NoProfile', '-Command',
                        '(Get-Process LumaWall -EA SilentlyContinue).Id'],
                       capture_output=True, text=True, timeout=30)
    return set(int(x) for x in r.stdout.split() if x.strip().isdigit())


def jendela():
    kumpulan = pids()
    hasil = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value not in kumpulan:
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
        hasil.append((int(hwnd), r.left, r.top, w, h))
        return True

    user32.EnumWindows(cb, 0)
    return hasil


def tangkap(hwnd, w, h, tujuan):
    """Minta jendela menggambar dirinya ke bitmap, lalu simpan sebagai PNG."""
    hdc_jendela = user32.GetWindowDC(hwnd)
    if not hdc_jendela:
        return False, 'GetWindowDC gagal'

    hdc_memori = gdi32.CreateCompatibleDC(hdc_jendela)
    hbitmap = gdi32.CreateCompatibleBitmap(hdc_jendela, w, h)
    gdi32.SelectObject(hdc_memori, hbitmap)

    ok = user32.PrintWindow(hwnd, hdc_memori, PW_RENDERFULLCONTENT)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h          # negatif = baris dari atas
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0

    panjang = w * h * 4
    buffer = ctypes.create_string_buffer(panjang)
    baris = gdi32.GetDIBits(hdc_memori, hbitmap, 0, h, buffer,
                            ctypes.byref(bmi), DIB_RGB_COLORS)

    gdi32.DeleteObject(hbitmap)
    gdi32.DeleteDC(hdc_memori)
    user32.ReleaseDC(hwnd, hdc_jendela)

    if not ok or baris == 0:
        return False, 'PrintWindow mengembalikan %s, baris=%d' % (ok, baris)

    # Disimpan sebagai BMP lalu dikonversi, supaya tidak perlu pustaka gambar.
    Path(tujuan).parent.mkdir(parents=True, exist_ok=True)
    with open(tujuan, 'wb') as f:
        ukuran_baris = w * 4
        ukuran_data = ukuran_baris * h
        f.write(b'BM')
        f.write((14 + 40 + ukuran_data).to_bytes(4, 'little'))
        f.write((0).to_bytes(2, 'little'))
        f.write((0).to_bytes(2, 'little'))
        f.write((14 + 40).to_bytes(4, 'little'))
        f.write((40).to_bytes(4, 'little'))
        f.write(w.to_bytes(4, 'little', signed=True))
        f.write((-h).to_bytes(4, 'little', signed=True))
        f.write((1).to_bytes(2, 'little'))
        f.write((32).to_bytes(2, 'little'))
        f.write((0).to_bytes(4, 'little'))
        f.write(ukuran_data.to_bytes(4, 'little'))
        f.write((2835).to_bytes(4, 'little'))
        f.write((2835).to_bytes(4, 'little'))
        f.write((0).to_bytes(4, 'little'))
        f.write((0).to_bytes(4, 'little'))
        f.write(buffer.raw[:ukuran_data])

    return True, tujuan


def main():
    if len(sys.argv) < 2:
        print('  pakai: python tools/tangkap-jendela.py <nama-keluaran>')
        return 2

    nama = sys.argv[1]
    print()
    print('  ══ tangkap jendela dengan PrintWindow ══')
    print()

    j = jendela()
    if not j:
        print('  ! jendela LumaWall tidak ditemukan')
        return 1

    hwnd, x, y, w, h = sorted(j, key=lambda t: -t[3] * t[4])[0]
    print('  jendela: %dx%d di (%d,%d)' % (w, h, x, y))

    # Ditampilkan kalau sedang di tray: PrintWindow tetap butuh jendela yang
    # punya permukaan gambar, dan jendela yang belum pernah ditampilkan belum
    # punya itu.
    terlihat = user32.IsWindowVisible(hwnd)
    if not terlihat:
        print('  jendela tersembunyi - ditampilkan sementara')
        user32.ShowWindow(hwnd, 9)   # SW_RESTORE
        time.sleep(2.0)

    tujuan = str(Path('build') / ('jendela-%s.bmp' % nama))
    ok, pesan = tangkap(hwnd, w, h, tujuan)

    # Dikembalikan ke tray supaya tidak mengganggu.
    if not terlihat:
        user32.ShowWindow(hwnd, 0)   # SW_HIDE

    if not ok:
        print('  ! gagal: %s' % pesan)
        return 1

    print('  disimpan: %s' % tujuan)

    # Diperiksa: hasil yang seluruhnya hitam berarti PrintWindow tidak
    # menggambar apa pun, dan itu harus dilaporkan.
    with open(tujuan, 'rb') as f:
        f.seek(14 + 40)
        data = f.read()

    terang = 0
    total = 0
    for i in range(0, len(data) - 4, 4 * 97):
        b, g, r = data[i], data[i + 1], data[i + 2]
        total += 1
        if b + g + r > 90:
            terang += 1

    persen = 100.0 * terang / max(1, total)
    print('  piksel terang: %.1f%% dari %d sampel' % (persen, total))
    if persen < 3:
        print('  ! hasil hampir seluruhnya hitam - PrintWindow tidak menggambar')
        return 1

    print('  OK - jendela berhasil ditangkap')
    return 0


if __name__ == '__main__':
    sys.exit(main())
