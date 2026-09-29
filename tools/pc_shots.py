"""Upload screenshot ke Store listing Partner Center + Save.

Jalankan: python tools/pc_shots.py [file1.png file2.png ...]

Alur: klik drop zone -> isi File name di dialog -> IDOK -> tunggu -> Save.
"""
import ctypes
import os
import sys
import time

import uiautomation as auto
import win32api
import win32con
import win32gui

CHROME_TITLE = 'Store listings'
DROP_X, DROP_Y = 450, 1000      # titik di dalam drop zone (aman, di layar)
BASE = r'C:\Users\ariel\Documents\Codex\2026-09-20\bik\work\build\store-upload'


def chrome():
    found = []

    def cb(h, _):
        if not win32gui.IsWindowVisible(h):
            return
        cls = win32gui.GetClassName(h)
        t = win32gui.GetWindowText(h)
        if 'Chrome_WidgetWin' in cls and 'Google Chrome' in t and CHROME_TITLE in t:
            found.append((h, t))
    win32gui.EnumWindows(cb, None)
    return found[0] if found else (None, None)


def items(ctrl, depth=0, out=None):
    if out is None:
        out = []
    if depth > 25:
        return out
    try:
        kids = ctrl.GetChildren()
    except Exception:
        return out
    for k in kids:
        try:
            out.append((k.ControlTypeName, k.Name or '', k))
        except Exception:
            continue
        items(k, depth + 1, out)
    return out


def find_dialog():
    found = []

    def cb(h, _):
        if win32gui.IsWindowVisible(h):
            t = win32gui.GetWindowText(h)
            if t in ('Open', 'Select File', 'Upload', 'Choose File'):
                found.append(h)
    win32gui.EnumWindows(cb, None)
    return found[0] if found else None


def upload(path):
    """Klik drop zone, isi path, klik Open."""
    # fokuskan Chrome dulu
    hwnd, title = chrome()
    if hwnd is None:
        return 'Chrome tidak ditemukan'
    try:
        auto.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.8)

    # klik drop zone
    win32api.SetCursorPos((DROP_X, DROP_Y))
    time.sleep(0.35)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.18)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(3.5)

    dlg = find_dialog()
    if dlg is None:
        return 'dialog tidak terbuka'

    try:
        auto.SetForegroundWindow(dlg)
    except Exception:
        pass
    time.sleep(0.9)

    w = auto.ControlFromHandle(dlg)
    for ct, n, k in items(w):
        if ct == 'EditControl' and 'file name' in n.lower():
            k.GetValuePattern().SetValue('"%s"' % path)
            break
    time.sleep(1.0)
    ctypes.windll.user32.SendMessageW(dlg, 0x0111, 1, 0)   # WM_COMMAND IDOK
    time.sleep(2.0)
    return 'ok'


def click_save():
    hwnd, _ = chrome()
    if hwnd is None:
        return 'Chrome tidak ditemukan'
    try:
        auto.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(0.8)

    win = auto.ControlFromHandle(hwnd)
    all_items = items(win)

    # cari tombol Save
    for ct, n, k in all_items:
        if ct == 'ButtonControl' and n.strip().lower() == 'save':
            r = k.BoundingRectangle
            if r.right <= r.left:
                continue
            # kalau di luar layar, scroll dulu
            if not (60 <= r.top <= 1050):
                win32api.SetCursorPos((960, 500))
                time.sleep(0.2)
                for _ in range(25):
                    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120, 0)
                    time.sleep(0.09)
                time.sleep(1.5)
                all_items = items(win)
                for ct2, n2, k2 in all_items:
                    if ct2 == 'ButtonControl' and n2.strip().lower() == 'save':
                        r = k2.BoundingRectangle
                        if r.right > r.left and 60 <= r.top <= 1050:
                            break
                else:
                    return 'Save tidak ditemukan setelah scroll'
            x = (r.left + r.right) // 2
            y = (r.top + r.bottom) // 2
            win32api.SetCursorPos((x, y))
            time.sleep(0.3)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.15)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return 'Save diklik di (%d,%d)' % (x, y)
    return 'tombol Save tidak ditemukan'


def status():
    hwnd, _ = chrome()
    if hwnd is None:
        return 'Chrome tidak ditemukan'
    win = auto.ControlFromHandle(hwnd)
    res = []
    for ct, n, k in items(win):
        if ct == 'TabItemControl' and ('Desktop' in n or 'Xbox' in n):
            res.append(n.strip())
    return ' | '.join(res)


def main():
    files = sys.argv[1:]
    for f in files:
        path = f if os.path.isabs(f) else os.path.join(BASE, f)
        if not os.path.exists(path):
            print('   LEWATI (tidak ada): %s' % path)
            continue
        print('   upload %s -> %s' % (os.path.basename(path), upload(path)))
        time.sleep(6)
        print('      status: %s' % status())
    if files:
        print('   %s' % click_save())
        time.sleep(6)
        print('   status akhir: %s' % status())
    else:
        print('   status: %s' % status())
    return 0


if __name__ == '__main__':
    sys.exit(main())
