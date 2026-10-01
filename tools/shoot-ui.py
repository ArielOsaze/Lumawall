#!/usr/bin/env python3
"""Tangkap layar halaman Luma Studio dan Displays, untuk memeriksa kerapian UI.

Dipakai untuk melihat sendiri apa yang berantakan, bukan menebak dari kode.
Aman dijalankan saat pengguna bekerja: jendela aplikasi dipindahkan ke layar
uji lebih dulu, dan layar utama tidak disentuh.

Pemakaian:
  python tools/shoot-ui.py --halaman studio
  python tools/shoot-ui.py --halaman displays
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ukur_layar  # noqa: E402

user32 = ctypes.WinDLL('user32', use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [('left', wt.LONG), ('top', wt.LONG),
                ('right', wt.LONG), ('bottom', wt.LONG)]


def pid_lumawall():
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         '(Get-Process LumaWall -EA SilentlyContinue).Id'],
        capture_output=True, text=True, timeout=30)
    return set(int(x) for x in r.stdout.split() if x.strip().isdigit())


def jendela_app():
    """Jendela utama LumaWall, termasuk yang sedang tersembunyi.

    Jendela aplikasi bisa tidak terlihat karena sedang di tray - dan pencarian
    yang hanya menerima jendela terlihat akan melaporkan "aplikasinya tidak
    jalan" padahal ia jalan. Itu menyesatkan: yang salah cuma jendelanya
    tersembunyi, bukan aplikasinya berhenti.
    """
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
        ti = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, ti, 512)
        hasil.append((int(hwnd), ti.value, r.left, r.top, w, h))
        return True

    user32.EnumWindows(cb, 0)
    return hasil


def pindah_ke_layar_uji(hwnd, monitor):
    """Pindahkan jendela aplikasi ke layar uji, tanpa menyentuh layar lain."""
    # Ukuran yang cukup untuk melihat seluruh halaman, tetapi tidak melebihi
    # layar uji.
    w = min(1500, monitor['width'] - 20)
    h = min(940, monitor['height'] - 20)
    x = monitor['x'] + (monitor['width'] - w) // 2
    y = monitor['y'] + (monitor['height'] - h) // 2
    user32.SetWindowPos(hwnd, 0, x, y, w, h, 0x0004 | 0x0010)
    time.sleep(0.6)


def klik_tombol_nav(monitor, label):
    """Klik tombol navigasi berdasarkan namanya, lewat UI Automation."""
    ps = r'''
param([string]$Label, [int]$X, [int]$Y, [int]$W, [int]$H)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty, $Label)
$el = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond)
if ($el -eq $null) { Write-Output "TIDAK ADA"; exit 1 }
$r = $el.Current.BoundingRectangle
if ($r.Left -lt $X -or $r.Left -gt ($X + $W) -or $r.Top -lt $Y -or $r.Top -gt ($Y + $H)) {
    Write-Output "DI LUAR"; exit 2
}
$p = New-Object System.Windows.Point(($r.Left + $r.Width / 2), ($r.Top + $r.Height / 2))
[System.Windows.Forms.Cursor]::Position = $p
Write-Output "OK $($r.Left),$($r.Top) $($r.Width)x$($r.Height)"
'''
    r = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         'Add-Type -AssemblyName System.Windows.Forms;' + ps,
         '-Label', label, '-X', str(monitor['x']), '-Y', str(monitor['y']),
         '-W', str(monitor['width']), '-H', str(monitor['height'])],
        capture_output=True, text=True, timeout=90)
    return r.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--halaman', required=True,
                    choices=['studio', 'displays', 'koleksi', 'discover'])
    ap.add_argument('--display', default='DISPLAY3')
    args = ap.parse_args()

    mon = ukur_layar.pilih(args.display)
    if mon is None:
        print('  layar %s tidak ada' % args.display)
        return 1

    print()
    print('  ══ tangkap halaman %s ══' % args.halaman)
    print()

    j = jendela_app()
    if not j:
        print('  ! jendela LumaWall tidak ditemukan - jalankan aplikasinya dulu')
        return 1

    hwnd, judul, x, y, w, h = j[0]
    print('  jendela: %dx%d di (%d,%d)' % (w, h, x, y))

    # Ditampilkan dulu kalau sedang di tray. Tanpa ini jendelanya tidak
    # terlihat dan tangkapan layarnya kosong.
    SW_SHOW = 5
    SW_RESTORE = 9
    if not user32.IsWindowVisible(hwnd):
        print('  jendela sedang tersembunyi (tray) - ditampilkan')
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.ShowWindow(hwnd, SW_SHOW)
        time.sleep(1.2)

    # Dipindahkan ke layar uji supaya layar utama tidak tersentuh.
    pindah_ke_layar_uji(hwnd, mon)
    j2 = jendela_app()
    if j2:
        hwnd, judul, x, y, w, h = j2[0]
        print('  dipindah: %dx%d di (%d,%d)' % (w, h, x, y))

    # Bawa ke depan.
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)

    # Klik navigasi yang diminta.
    label = {'studio': 'Luma Studio', 'displays': 'Monitor',
             'koleksi': 'Koleksi', 'discover': 'Jelajahi'}[args.halaman]
    hasil = klik_tombol_nav(mon, label)
    print('  navigasi "%s": %s' % (label, hasil))
    if hasil.startswith('OK'):
        import ctypes.wintypes as wt2
        # Klik di posisi yang dilaporkan.
        bagian = hasil.split()[1].split(',')
        px, py = int(bagian[0]), int(bagian[1])
        user32.SetCursorPos(px + 20, py + 10)
        time.sleep(0.2)
        user32.mouse_event(0x0002, 0, 0, 0, 0)   # LEFTDOWN
        time.sleep(0.05)
        user32.mouse_event(0x0004, 0, 0, 0, 0)   # LEFTUP
        time.sleep(1.5)

    # Tangkap jendelanya.
    j3 = jendela_app()
    if not j3:
        print('  ! jendela hilang')
        return 1
    hwnd, judul, x, y, w, h = sorted(j3, key=lambda t: -t[4] * t[5])[0]

    out = Path('build') / ('ui-%s.png' % args.halaman)
    out.parent.mkdir(parents=True, exist_ok=True)
    ps = (
        "Add-Type -AssemblyName System.Drawing;"
        "$b = New-Object System.Drawing.Bitmap(%d,%d);"
        "$g = [System.Drawing.Graphics]::FromImage($b);"
        "$g.CopyFromScreen(%d,%d,0,0,(New-Object System.Drawing.Size(%d,%d)));"
        "$b.Save('%s');" % (w, h, x, y, w, h, str(out.resolve()).replace('\\', '\\\\'))
    )
    subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                   capture_output=True, text=True, timeout=60)

    if out.exists():
        print('  disimpan: %s  (%dx%d)' % (out, w, h))
        return 0
    print('  ! tangkapan gagal')
    return 1


if __name__ == '__main__':
    sys.exit(main())
