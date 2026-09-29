"""Buka satu bahasa di Manage languages lalu upload screenshot + Save.

Pemakaian:
  python tools/pc_lang_shots.py "Japanese (Japan)"
  python tools/pc_lang_shots.py "Chinese (China)"
"""
import ctypes
import os
import sys
import time

import uiautomation as auto
import win32api
import win32con
import win32gui

BASE = r'C:\Users\ariel\Documents\Codex\2026-09-20\bik\work\build\store-upload'
SHOTS = ['1-discover.png', '2-library.png', '3-performance.png']
DROP = (450, 1000)


def find_chrome():
    found = []

    def cb(h, _):
        if not win32gui.IsWindowVisible(h):
            return
        cls = win32gui.GetClassName(h)
        t = win32gui.GetWindowText(h)
        if 'Chrome_WidgetWin' in cls and 'Google Chrome' in t and 'Partner Center' in t:
            r = win32gui.GetWindowRect(h)
            found.append((h, t, r))
    win32gui.EnumWindows(cb, None)
    if not found:
        return None
    found.sort(key=lambda t: -((t[2][2] - t[2][0]) * (t[2][3] - t[2][1])))
    return found[0]


def items(hwnd, depth=45):
    win = auto.ControlFromHandle(hwnd)
    out = []

    def walk(c, d=0):
        if d > depth:
            return
        try:
            kids = c.GetChildren()
        except Exception:
            return
        for k in kids:
            try:
                out.append((k.ControlTypeName, k.Name or '', k.BoundingRectangle, k))
            except Exception:
                continue
            walk(k, d + 1)
    walk(win)
    return out


def click(x, y):
    win32api.SetCursorPos((x, y))
    time.sleep(0.35)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.16)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def upload_once(hwnd):
    """Klik drop zone, isi path, IDOK."""
    click(*DROP)
    time.sleep(4)
    found = []

    def cb(h, _):
        if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h) == 'Open':
            found.append(h)
    win32gui.EnumWindows(cb, None)
    if not found:
        return 'dialog tidak terbuka'
    D = found[0]
    try:
        auto.SetForegroundWindow(D)
    except Exception:
        pass
    time.sleep(1.0)
    w = auto.ControlFromHandle(D)
    out = []
    stack = [w]
    while stack:
        c = stack.pop()
        try:
            for k in c.GetChildren():
                out.append(k)
                stack.append(k)
        except Exception:
            continue
    joined = ' '.join('"%s"' % os.path.join(BASE, f) for f in SHOTS)
    for k in out:
        try:
            if k.ControlTypeName == 'EditControl' and 'file name' in (k.Name or '').lower():
                k.GetValuePattern().SetValue(joined)
                break
        except Exception:
            continue
    time.sleep(1.2)
    ctypes.windll.user32.SendMessageW(D, 0x0111, 1, 0)
    return 'ok'


def save(hwnd):
    for _ in range(6):
        for ct, n, r, k in items(hwnd):
            if ct == 'ButtonControl' and n.strip().lower() == 'save':
                if r.right <= r.left:
                    continue
                if 60 <= r.top <= 1045:
                    click((r.left + r.right) // 2, (r.top + r.bottom) // 2)
                    return 'Save diklik'
                break
        win32api.SetCursorPos((960, 500))
        time.sleep(0.25)
        for _ in range(10):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120, 0)
            time.sleep(0.11)
        time.sleep(1.5)
    return 'Save tidak ditemukan'


def main():
    if len(sys.argv) < 2:
        print('pakai: python tools/pc_lang_shots.py "Japanese (Japan)"')
        return 2
    lang = sys.argv[1]

    info = find_chrome()
    if info is None:
        print('Chrome Partner Center tidak ditemukan')
        return 2
    hwnd, title, rect = info
    print('Chrome hwnd=%d "%s"' % (hwnd, title[:55]))

    try:
        auto.SetForegroundWindow(hwnd)
    except Exception:
        pass
    time.sleep(1.2)

    # klik hyperlink bahasa
    hit = None
    for ct, n, r, k in items(hwnd):
        if ct == 'HyperlinkControl' and n.strip() == lang:
            hit = r
            break
    if hit is None:
        print('link %r tidak ditemukan' % lang)
        return 1
    click((hit.left + hit.right) // 2, (hit.top + hit.bottom) // 2)
    time.sleep(9)
    print('judul: %s' % win32gui.GetWindowText(hwnd)[:70])

    # scroll ke bagian screenshots
    win32api.SetCursorPos((960, 500))
    time.sleep(0.3)
    for _ in range(4):
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -120, 0)
        time.sleep(0.12)
    time.sleep(2)

    print('upload: %s' % upload_once(hwnd))
    time.sleep(30)

    # status tab
    for ct, n, r, k in items(hwnd):
        if ct == 'TabItemControl' and ('Desktop' in n or 'Xbox' in n):
            print('   %s' % n.strip()[:25])

    print(save(hwnd))
    time.sleep(8)
    return 0


if __name__ == '__main__':
    sys.exit(main())
