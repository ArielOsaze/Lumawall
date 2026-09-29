"""Bukti bahwa wallpaper tidak lagi hitam setelah keluar dari app fullscreen.

Uji ini JUJUR: ia memastikan dulu bahwa window fullscreen benar-benar menutupi
layar (kecerahan harus turun). Kalau tidak, uji dinyatakan TIDAK VALID, bukan
lulus - karena tes yang tidak pernah bisa gagal tidak membuktikan apa pun.

Pemakaian:
  python tools/check-fullscreen-recovery.py
  python tools/check-fullscreen-recovery.py --display \\\\.\\DISPLAY3 --wait 6
"""
import argparse
import sys
import time

import win32api
import win32con
import win32gui
from PIL import ImageGrab

WS_EX_TOPMOST = 0x00000008
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
SW_SHOW = 5

_wndclass_atom = None


def monitors():
    out = []
    for hmon, _hdc, _rect in win32api.EnumDisplayMonitors():
        info = win32api.GetMonitorInfo(hmon)
        out.append((info['Device'], info['Monitor'], bool(info['Flags'] & 1)))
    return out


def brightness(box):
    img = ImageGrab.grab(bbox=box, all_screens=True).convert('L').resize((48, 27))
    px = list(img.getdata())
    return sum(px) / float(len(px))


def _wndproc(hwnd, msg, wparam, lparam):
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


def make_fullscreen_window(bounds):
    """Window hitam fullscreen topmost, benar-benar menutupi monitor."""
    global _wndclass_atom
    left, top, right, bottom = bounds
    hinst = win32api.GetModuleHandle(None)

    if _wndclass_atom is None:
        cls = win32gui.WNDCLASS()
        cls.lpfnWndProc = _wndproc
        cls.lpszClassName = 'LumaWallFullscreenProbe'
        cls.hInstance = hinst
        cls.hbrBackground = win32gui.GetStockObject(win32con.BLACK_BRUSH)
        try:
            _wndclass_atom = win32gui.RegisterClass(cls)
        except Exception:
            _wndclass_atom = cls.lpszClassName

    hwnd = win32gui.CreateWindowEx(
        WS_EX_TOPMOST, _wndclass_atom, 'LumaWall Fullscreen Probe',
        WS_POPUP | WS_VISIBLE,
        left, top, right - left, bottom - top,
        0, 0, hinst, None)
    win32gui.ShowWindow(hwnd, SW_SHOW)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, left, top,
                          right - left, bottom - top,
                          win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE)
    win32gui.UpdateWindow(hwnd)
    return hwnd


def read_log_tail(path, since_byte):
    """Baca bagian log yang baru sejak since_byte."""
    try:
        with open(path, 'rb') as f:
            f.seek(since_byte)
            return f.read().decode('utf-8', 'replace')
    except Exception:
        return ''


def log_size(path):
    try:
        import os
        return os.path.getsize(path)
    except Exception:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--display')
    ap.add_argument('--threshold', type=float, default=10.0,
                    help='kecerahan minimum agar dianggap tidak hitam')
    ap.add_argument('--wait', type=float, default=6.0,
                    help='detik menunggu setelah fullscreen ditutup')
    args = ap.parse_args()

    log_path = r'C:\Users\ariel\AppData\Local\LumaWall\Logs\lumawall.log'

    mons = monitors()
    print('  monitor:')
    for dev, rect, primary in mons:
        print('     %-14s %-28s primary=%s' % (dev, rect, primary))

    target = None
    for dev, rect, primary in mons:
        if args.display:
            # Toleran terhadap escaping shell: cukup cocokkan 'DISPLAY3' saja.
            want = args.display.replace('\\', '').upper()
            have = dev.replace('\\', '').upper()
            if want == have or want in have:
                target = (dev, rect)
                break
        elif not primary:
            target = (dev, rect)
            break
    if target is None:
        target = (mons[0][0], mons[0][1])

    dev, rect = target
    box = (rect[0], rect[1], rect[2], rect[3])
    print('  layar uji: %s %s' % (dev, rect))

    # Pastikan wallpaper di layar ini TIDAK sedang paused. Kalau sudah paused,
    # tes tidak bisa menguji jalur resume - jadi kita laporkan sebagai TIDAK VALID
    # alih-alih lulus palsu.
    log_before = log_size(log_path)
    mark = log_before

    before = brightness(box)
    print('  kecerahan sebelum fullscreen : %.1f' % before)

    hwnd = make_fullscreen_window(rect)
    time.sleep(3.0)
    during = brightness(box)
    print('  kecerahan saat fullscreen    : %.1f' % during)

    if during > args.threshold:
        print()
        print('  TIDAK VALID: window fullscreen tidak menutupi layar')
        print('              (kecerahan %.1f masih di atas %.1f)' % (during, args.threshold))
        try:
            win32gui.DestroyWindow(hwnd)
        except Exception:
            pass
        return 2

    # Apakah app benar-benar mem-pause layar ini? Itu yang membuat tes bermakna.
    covered = read_log_tail(log_path, mark)
    paused_here = ('paused [' in covered and dev.upper() in covered.upper()) or \
                  ('Covering window on ' + dev in covered)
    if not paused_here:
        print('  catatan: tidak ada bukti pause untuk layar ini di log')

    win32gui.DestroyWindow(hwnd)
    closed_at = time.time()
    mark = log_size(log_path)
    print('  window fullscreen ditutup')

    recovered = None
    while time.time() - closed_at < args.wait:
        time.sleep(0.3)
        now = brightness(box)
        if now >= args.threshold:
            recovered = time.time() - closed_at
            break

    after = brightness(box)
    print('  kecerahan setelah fullscreen : %.1f' % after)

    # Verifikasi jalur resume benar-benar terjadi.
    resumed_log = read_log_tail(log_path, mark)
    resumed_here = 'resumed [' in resumed_log and dev.upper() in resumed_log.upper()

    if recovered is not None:
        print()
        print('  LULUS: wallpaper kembali dalam %.1f detik (batas %.1f detik)'
              % (recovered, args.wait))
        print('         resume terdeteksi di log: %s' % ('ya' if resumed_here else 'tidak'))
        return 0

    print()
    print('  GAGAL: layar masih gelap (%.1f < %.1f) setelah %.1f detik'
          % (after, args.threshold, args.wait))
    return 1


if __name__ == '__main__':
    sys.exit(main())
