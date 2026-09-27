"""Photograph the app's scrollbar and report its colour.

Why this exists
---------------
"the scrollbar on the right is white" is a complaint about a pixel, so the check has to
look at the pixel. This finds the running LumaWall window, captures the strip along its
right edge where the scrollbar is drawn, and reports the brightest colour in it - which is
the scrollbar, because the window behind it is near-black.

It fails loudly when no window is found, so a pass cannot come from having nothing to look
at.

Usage:
    python tools/check-scrollbar.py            # capture and report
    python tools/check-scrollbar.py --save     # also write build/scrollbar.png
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageGrab

ROOT = Path(__file__).resolve().parent.parent

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()


def find_window(process_name='LumaWall'):
    """The main window of the process called `process_name`.

    Matching on the window title alone is not enough: a browser tab showing the site is
    titled "LumaWall - ... - Google Chrome", so the first version of this measured the
    scrollbar of a Chrome window and reported a light bar that was not the app's.
    """
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True

        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return True

        # The process's image name has to be the app, not a browser that happens to be
        # showing a page about it.
        PROCESS_QUERY_LIMITED = 0x1000
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid.value)
        if not handle:
            return True
        try:
            buf = ctypes.create_unicode_buffer(512)
            size = wt.DWORD(512)
            if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return True
            exe = Path(buf.value).stem
        finally:
            kernel32.CloseHandle(handle)

        if exe.lower() != process_name.lower():
            return True

        rect = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w > 400 and h > 300:
            n = user32.GetWindowTextLengthW(hwnd)
            title = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, title, n + 1)
            found.append((hwnd, title.value, rect.left, rect.top, w, h))
        return True

    user32.EnumWindows(callback, 0)
    return found[0] if found else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--save', action='store_true')
    args = ap.parse_args()

    win = find_window()
    if not win:
        print('  no LumaWall window is open, so there is nothing to measure.')
        print('  Start the app first - a check that has nothing to look at cannot pass.')
        return 1

    hwnd, title, x, y, w, h = win
    print('  window: %r  at %d,%d  %dx%d' % (title, x, y, w, h))

    # The strip just inside the right edge, which is where the vertical bar is drawn.
    strip_w = 22
    box = (x + w - strip_w, y + 80, x + w, y + h - 80)
    shot = ImageGrab.grab(bbox=box, all_screens=True)
    a = np.asarray(shot.convert('RGB')).reshape(-1, 3)
    if not len(a):
        print('  captured nothing')
        return 1

    lum = a.astype(int).sum(axis=1) / 3.0
    brightest = int(lum.max())
    p95 = int(np.percentile(lum, 95))
    mean = int(lum.mean())

    # Which pixel is brightest, and is it neutral (a grey scrollbar) or tinted?
    idx = int(lum.argmax())
    rgb = tuple(int(v) for v in a[idx])
    spread = max(rgb) - min(rgb)

    print('  strip: %dx%d at the right edge' % (shot.width, shot.height))
    print('    mean luminance   %d' % mean)
    print('    95th percentile  %d' % p95)
    print('    brightest        %d  rgb%s  (colour spread %d)' % (brightest, rgb, spread))

    if args.save:
        out = ROOT / 'build' / 'scrollbar.png'
        out.parent.mkdir(parents=True, exist_ok=True)
        shot.resize((shot.width * 4, shot.height), Image.NEAREST).save(out)
        print('    wrote %s' % out)

    # A pass with nothing on screen is not a pass.
    #
    # The first version of this reported OK when the strip was uniformly dark, which is
    # exactly what an empty strip looks like. It passed while measuring nothing. A dark
    # scrollbar has a thumb that is lighter than the window behind it, so a strip with no
    # variation at all means no bar was captured and the result is unknown, not good.
    if brightest - mean < 12:
        print()
        print('  FAIL  the strip is uniform (brightest %d, mean %d), so no scrollbar was'
              % (brightest, mean))
        print('        captured. Scroll a page that overflows, then run this again -')
        print('        a check that measured nothing cannot report a pass.')
        return 1

    # A white Aero2 scrollbar sits near 240; a dark one sits well below 120. The window
    # behind it is #07080B, about 8.
    if brightest > 200:
        print()
        print('  FAIL  the brightest pixel is %d - that is a light scrollbar on a dark'
              % brightest)
        print('        window. WPF\'s built-in template is still in use.')
        return 1
    if brightest > 120:
        print()
        print('  FAIL  the brightest pixel is %d, brighter than a dark bar should be.'
              % brightest)
        return 1

    print()
    print('  OK    a scrollbar is visible and stays dark (brightest %d, was ~240 before)'
          % brightest)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
