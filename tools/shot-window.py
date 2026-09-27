"""Photograph the LumaWall window itself, not whatever is on top of it.

Why this exists
---------------
ImageGrab copies screen pixels, so when the wallpaper engine or another window sits
above the app the capture shows THAT, not the app. PrintWindow asks the window to
draw itself into an offscreen bitmap instead, which works even when the window is
covered. PW_RENDERFULLCONTENT (2) is required because the window hosts a composited
surface.

Usage: python tools/shot-window.py <out.png>
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time
from pathlib import Path

from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetProcessDPIAware()


class BMI(ctypes.Structure):
    _fields_ = [
        ('biSize', wt.DWORD), ('biWidth', ctypes.c_long), ('biHeight', ctypes.c_long),
        ('biPlanes', wt.WORD), ('biBitCount', wt.WORD), ('biCompression', wt.DWORD),
        ('biSizeImage', wt.DWORD), ('biXPelsPerMeter', ctypes.c_long),
        ('biYPelsPerMeter', ctypes.c_long), ('biClrUsed', wt.DWORD),
        ('biClrImportant', wt.DWORD),
    ]


class BIH(ctypes.Structure):
    _fields_ = [('bmiHeader', BMI), ('bmiColors', wt.DWORD * 3)]


def find_window(title='LumaWall', min_width=400):
    hit = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        t = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, t, n + 1)
        if t.value != title:
            return True
        r = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        if (r.right - r.left) < min_width:
            return True
        hit.append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    return hit[0] if hit else 0


def shot(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top

    hdc = user32.GetWindowDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    user32.PrintWindow(hwnd, mdc, 2)

    bi = BIH()
    bi.bmiHeader.biSize = ctypes.sizeof(BMI)
    bi.bmiHeader.biWidth = w
    bi.bmiHeader.biHeight = -h
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    bi.bmiHeader.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)

    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(hwnd, hdc)

    return Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1).convert('RGB')


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else 'build/window.png')
    hwnd = find_window()
    if not hwnd:
        print('  the LumaWall window was not found')
        return 1
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.2)
    img = shot(hwnd)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)

    import numpy as np
    lum = np.asarray(img).mean(axis=2)
    print('  wrote %s %dx%d' % (out, img.size[0], img.size[1]))
    print('  near-black pixels: %.1f%%' % ((lum < 12).mean() * 100))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
