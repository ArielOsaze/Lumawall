"""Isi field di halaman Store listing Partner Center lewat UI Automation ValuePattern.

Pemakaian:
  python tools/pc_listing.py --fill            # isi semua field listing EN
  python tools/pc_listing.py --list            # tampilkan semua field
  python tools/pc_listing.py --set "NAMA" "TEKS"  # isi satu field berdasarkan nama
"""
import argparse
import sys
import time

import uiautomation as auto
import win32gui


def chrome_hwnd():
    found = []

    def cb(h, _):
        if not win32gui.IsWindowVisible(h):
            return
        cls = win32gui.GetClassName(h)
        t = win32gui.GetWindowText(h)
        if 'Chrome_WidgetWin' in cls and 'Google Chrome' in t and 'Store listings' in t:
            found.append(h)
    win32gui.EnumWindows(cb, None)
    if not found:
        # fallback: jendela Partner Center apa pun
        def cb2(h, _):
            if not win32gui.IsWindowVisible(h):
                return
            cls = win32gui.GetClassName(h)
            t = win32gui.GetWindowText(h)
            if 'Chrome_WidgetWin' in cls and 'Google Chrome' in t and 'Partner Center' in t:
                found.append(h)
        win32gui.EnumWindows(cb2, None)
    return found[0] if found else None


def collect(hwnd):
    win = auto.ControlFromHandle(hwnd)
    out = []

    def walk(c, d=0):
        if d > 30:
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
                out.append((ct, n, k))
            walk(k, d + 1)
    walk(win)
    return out


def edits_sorted(items):
    res = []
    for ct, n, k in items:
        if ct == 'EditControl':
            r = k.BoundingRectangle
            if r.right > r.left and r.left > 280 and r.top > 120:
                try:
                    v = k.GetValuePattern().Value or ''
                except Exception:
                    v = None
                res.append((r.top, n, k, v))
    res.sort()
    return res


# Isi listing bahasa Inggris untuk LumaWall
EN = {
    'Description*': (
        "LumaWall brings your Windows desktop to life with smooth, GPU-accelerated live "
        "wallpapers. Pick from a huge built-in catalogue of HD and 4K animated art, or use "
        "your own video files. LumaWall renders every frame on the GPU, so your desktop "
        "stays responsive while your wallpaper keeps moving.\n\n"
        "Set a different wallpaper for each monitor, fine-tune tone mapping, add an "
        "iOS-style desktop clock widget, and keep everything running quietly in the tray. "
        "LumaWall is a one-time purchase with no subscription.\n\n"
        "Highlights:\n"
        "- 22,000+ curated dynamic wallpapers, all HD or better\n"
        "- Per-monitor wallpapers with independent placement\n"
        "- GPU rendering that keeps CPU usage low\n"
        "- Ten iOS-style clock widget styles with transparent backgrounds\n"
        "- Full control over pause, playback speed and volume\n"
        "- Works offline with your own video files\n"
        "- English and Indonesian interface"
    ),
    "What's new in this version": (
        "Version 4.5.10\n"
        "- The wallpaper comes back in a fraction of a second after closing a "
        "fullscreen app; it previously stayed black for up to 40 seconds\n"
        "- The checkout and order pages have a navigation menu on phones\n"
        "- The navigation bar is tidier, with the sections grouped into menus\n"
        "\n"
        "Version 4.5.9\n"
        "- Stopping a wallpaper and applying one again no longer leaves the screen "
        "black; the last frame stays up until the next wallpaper is ready\n"
        "- Image wallpapers now appear on Windows 11 - they previously stayed "
        "invisible while the log said they were ready\n"
        "- Wallpapers are no longer cropped on 1366x768 screens\n"
        "- Switching between image and video wallpapers no longer goes black\n"
        "- The wallpaper no longer goes black after closing a fullscreen app"
    ),
    'Product features': (
        "Dynamic wallpaper engine;Per-monitor wallpapers;GPU accelerated;"
        "22,000+ wallpaper catalogue;Clock widget;4K ready;Offline playback;"
        "No subscription"
    ),
    'Short title': 'LumaWall - Live Wallpaper',
    'Voice title': 'LumaWall live wallpaper',
    'Short description': (
        "Animated live wallpapers for Windows. 22,000+ dynamic HD and 4K artworks, "
        "per-monitor setup, GPU accelerated, with an iOS-style clock widget. One-time "
        "purchase, no subscription."
    ),
    'Copyright and trademark info': (
        "Copyright (c) 2026 Xinet Group. All rights reserved. "
        "LumaWall is a trademark of Xinet Group."
    ),
    'Developed by': 'Xinet Group',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--fill', action='store_true')
    ap.add_argument('--set', nargs=2, metavar=('NAME', 'TEXT'))
    args = ap.parse_args()

    hwnd = chrome_hwnd()
    if hwnd is None:
        print('jendela Chrome Store listings tidak ditemukan')
        return 2
    print('Chrome hwnd=%d "%s"' % (hwnd, win32gui.GetWindowText(hwnd)[:60]))

    items = collect(hwnd)
    edits = edits_sorted(items)

    if args.list:
        for top, n, k, v in edits:
            print('   y=%-5d %-42s value=%r' % (top, n[:42], (v or '')[:50]))
        return 0

    if args.set:
        name, text = args.set
        hit = None
        for top, n, k, v in edits:
            if name.lower() in n.lower():
                hit = (n, k)
                break
        if hit is None:
            print('field %r tidak ditemukan' % name)
            return 1
        n, k = hit
        try:
            k.GetValuePattern().SetValue(text)
            print('terisi %s (%d char)' % (n[:40], len(text)))
            return 0
        except Exception as e:
            print('SetValue gagal:', e)
            return 1

    if args.fill:
        done = 0
        for top, n, k, v in edits:
            key = None
            for want in EN:
                if want.lower() == n.lower():
                    key = want
                    break
            if key is None:
                continue
            if v:                      # sudah ada isinya, jangan ditimpa
                print('   lewati %-42s (sudah ada isi)' % n[:42])
                continue
            try:
                k.GetValuePattern().SetValue(EN[key])
                print('   OK  %-42s (%d char)' % (n[:42], len(EN[key])))
                done += 1
                time.sleep(0.35)
            except Exception as e:
                print('   GAGAL %-42s %s' % (n[:42], e))
        print('selesai: %d field terisi' % done)
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())
