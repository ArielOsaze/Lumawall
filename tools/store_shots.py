"""Ambil screenshot Store 1920x1080 dari jendela LumaWall tanpa mengganggu layar utama.

Jendela dipindah ke monitor sekunder (DISPLAY2) dan TIDAK diaktifkan,
jadi apa pun yang sedang kamu kerjakan di layar utama tetap jalan.
Navigasi halaman diklik lewat UI Automation InvokePattern (tidak butuh fokus).
"""
import ctypes
import os
import sys
import time

import uiautomation as auto
import win32api
import win32con
import win32gui
import win32ui
from PIL import Image

OUT = r'build\store-shots'
W, H = 1920, 1080


def find_hidden_lumawall():
    found = []

    def cb(h, _):
        cls = win32gui.GetClassName(h)
        t = win32gui.GetWindowText(h)
        if 'HwndWrapper[LumaWall' in cls and t == 'LumaWall':
            r = win32gui.GetWindowRect(h)
            found.append((h, r))
    win32gui.EnumWindows(cb, None)
    return found


def capture(hwnd, path):
    """Tangkap isi jendela lewat screen grab area jendela (WebView2 tidak bisa PrintWindow)."""
    from PIL import ImageGrab
    r = win32gui.GetWindowRect(hwnd)
    # pastikan jendela benar-benar terlihat (tidak tertutup) di monitor sekunder
    img = ImageGrab.grab(bbox=(r[0], r[1], r[2], r[3]), all_screens=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return img.size


def click_nav(hwnd, label):
    win = auto.ControlFromHandle(hwnd)
    items = []

    def walk(c, d=0):
        if d > 25:
            return
        try:
            kids = c.GetChildren()
        except Exception:
            return
        for k in kids:
            try:
                n = k.Name or ''
                ct = k.ControlTypeName
            except Exception:
                continue
            if n:
                items.append((ct, n, k))
            walk(k, d + 1)
    walk(win)

    hits = [(ct, n, k) for ct, n, k in items if label.lower() in n.lower()]
    order = {'ListItemControl': 0, 'TabItemControl': 1, 'ButtonControl': 2,
             'HyperlinkControl': 3, 'TextControl': 4}
    hits.sort(key=lambda t: order.get(t[0], 9))
    for ct, n, k in hits:
        for how in ('invoke', 'legacy'):
            try:
                if how == 'invoke':
                    k.GetInvokePattern().Invoke()
                else:
                    k.GetLegacyIAccessiblePattern().DoDefaultAction()
                return '%s [%s]' % (n[:40], how)
            except Exception:
                continue
    return None


def main():
    pages = sys.argv[1:] or ['Discover', 'Library', 'Displays', 'Performance', 'Luma Studio']
    found = find_hidden_lumawall()
    if not found:
        print('jendela LumaWall (HwndWrapper) tidak ditemukan')
        return 2
    hwnd, rect = found[0]
    print('LumaWall hwnd=%d rect=%s' % (hwnd, rect))

    # tampilkan tanpa aktivasi + pindah ke monitor sekunder, ukuran 1920x1080
    win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
    time.sleep(0.6)
    win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, -1920, 0, W, H,
                          win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW)
    time.sleep(1.5)
    print('posisi setelah dipindah: %s' % (win32gui.GetWindowRect(hwnd),))

    os.makedirs(OUT, exist_ok=True)
    for i, page in enumerate(pages, 1):
        nav = click_nav(hwnd, page)
        time.sleep(2.5)
        slug = page.lower().replace(' ', '-')
        path = os.path.join(OUT, '%d-%s.png' % (i, slug))
        size = capture(hwnd, path)
        print('   %-13s -> %-38s %dx%d  nav=%s' % (page, path, size[0], size[1], nav))

    # sembunyikan lagi supaya tidak mengganggu
    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
    print('jendela disembunyikan lagi')
    return 0


if __name__ == '__main__':
    sys.exit(main())
