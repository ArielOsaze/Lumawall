"""Klik di jendela Chrome yang DIPASTIKAN di depan dulu.

Pemakaian:
  python tools/win_click.py --list-windows
  python tools/win_click.py --list-tabs
  python tools/win_click.py --activate
  python tools/win_click.py --click X Y
  python tools/win_click.py --click-rel RX RY      # relatif ke jendela Chrome (0..1)
  python tools/win_click.py --tab "PART_OF_TITLE"  # pilih tab Chrome berdasarkan judul
  python tools/win_click.py --type "TEKS"
  python tools/win_click.py --key 0x23             # kirim satu VK
"""
import argparse
import sys
import time

import win32con
import win32gui
import win32api
import uiautomation as auto


def find_chrome(title_filter=None):
    """Jendela utama Chrome (yang terbesar, judulnya 'Google Chrome').

    title_filter: kalau diisi, hanya jendela yang judulnya mengandung teks ini.
    """
    result = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        r = win32gui.GetWindowRect(hwnd)
        w = r[2] - r[0]
        h = r[3] - r[1]
        # hanya Chrome sungguhan (bukan Electron/Hermes yang kelasnya mirip)
        if 'Chrome_WidgetWin' not in cls:
            return
        if 'Google Chrome' not in title:
            return
        if title_filter and title_filter.lower() not in title.lower():
            return
        # jendela minimized punya koordinat -32000
        minimized = (r[0] <= -30000)
        result.append((hwnd, title, r, 0 if minimized else w * h))

    win32gui.EnumWindows(cb, None)
    if not result:
        return None
    # prioritaskan yang tidak minimized, lalu yang terbesar
    result.sort(key=lambda t: (-t[3], t[0]))
    return result[0]


def activate(hwnd):
    """Bawa jendela ke depan; restore dulu kalau minimized."""
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.5)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        # trik: tekan ALT supaya proses ini boleh mengambil foreground
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            print('SetForegroundWindow gagal:', e)
    time.sleep(0.4)
    return win32gui.GetForegroundWindow() == hwnd


def click(x, y):
    win32api.SetCursorPos((x, y))
    time.sleep(0.15)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.09)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.2)


def type_text(text):
    import ctypes
    for ch in text:
        # pakai SendInput lewat ctypes supaya karakter khusus aman
        ctypes.windll.user32.keybd_event(0, 0, 0, 0)  # no-op, jaga fokus
        auto.SendKeys('{text}', interval=0.02) if False else None
    # cara paling andal: tempel lewat clipboard
    import subprocess
    p = subprocess.run(['powershell', '-NoProfile', '-Command',
                        'Set-Clipboard -Value $args[0]', text],
                       capture_output=True)
    if p.returncode != 0:
        print('Set-Clipboard gagal:', p.stderr.decode('utf-8', 'replace'))
        return False
    time.sleep(0.3)
    auto.SendKeys('{Ctrl}v', interval=0.05)
    return True


def list_tabs(hwnd):
    """Daftar tab Chrome (judul + posisi) lewat UI Automation."""
    win = auto.ControlFromHandle(hwnd)
    if win is None:
        print('tidak bisa ambil kontrol dari hwnd')
        return []
    tabs = []
    for c in win.GetChildren():
        ct = c.ControlTypeName
        if ct != 'PaneControl':
            continue
        for cc in c.GetChildren():
            if cc.ControlTypeName == 'TabControl':
                for t in cc.GetChildren():
                    r = t.BoundingRectangle
                    tabs.append((t.Name, r.left, r.top, r.right, r.bottom, t))
    return tabs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list-windows', action='store_true')
    ap.add_argument('--list-tabs', action='store_true')
    ap.add_argument('--activate', action='store_true')
    ap.add_argument('--click', nargs=2, metavar=('X', 'Y'))
    ap.add_argument('--click-rel', nargs=2, metavar=('RX', 'RY'))
    ap.add_argument('--tab')
    ap.add_argument('--type')
    ap.add_argument('--key')
    ap.add_argument('--window', help='hanya jendela Chrome yang judulnya mengandung ini')
    args = ap.parse_args()

    if args.list_windows:
        def cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t:
                    r = win32gui.GetWindowRect(hwnd)
                    print('  hwnd=%-10d %-60s %s' % (hwnd, t[:60], r))
        win32gui.EnumWindows(cb, None)
        return 0

    info = find_chrome(args.window)
    if info is None:
        print('Chrome tidak ditemukan')
        return 2
    hwnd, title, rect, _ = info
    print('Chrome hwnd=%d  "%s"  rect=%s' % (hwnd, title[:60], rect))

    if args.list_tabs:
        tabs = list_tabs(hwnd)
        for i, (n, l, t, r, b, _c) in enumerate(tabs):
            print('  [%d] %-60s  (%d,%d %dx%d)  tengah=(%d,%d)'
                  % (i, n[:60], l, t, r - l, b - t, (l + r) // 2, (t + b) // 2))
        return 0

    if not activate(hwnd):
        print('peringatan: Chrome mungkin tidak di depan')

    if args.activate:
        print('Chrome diaktifkan')
        return 0

    if args.tab:
        tabs = list_tabs(hwnd)
        hit = None
        for n, l, t, r, b, c in tabs:
            if args.tab.lower() in (n or '').lower():
                hit = (n, l, t, r, b, c)
                break
        if hit is None:
            print('tab tidak ditemukan: %r' % args.tab)
            print('tab yang ada:')
            for n, l, t, r, b, c in tabs:
                print('   -', n)
            return 1
        n, l, t, r, b, c = hit
        cx = (l + r) // 2
        cy = (t + b) // 2
        print('klik tab "%s" di (%d, %d)' % (n, cx, cy))
        click(cx, cy)
        time.sleep(0.8)
        return 0

    if args.click:
        x, y = int(args.click[0]), int(args.click[1])
        click(x, y)
        print('klik (%d, %d)' % (x, y))
        return 0

    if args.click_rel:
        rx, ry = float(args.click_rel[0]), float(args.click_rel[1])
        x = int(rect[0] + (rect[2] - rect[0]) * rx)
        y = int(rect[1] + (rect[3] - rect[1]) * ry)
        click(x, y)
        print('klik relatif (%.2f, %.2f) -> (%d, %d)' % (rx, ry, x, y))
        return 0

    if args.type:
        if type_text(args.type):
            print('teks ditempel:', args.type)
            return 0
        return 1

    if args.key:
        vk = int(args.key, 16) if args.key.lower().startswith('0x') else int(args.key)
        win32api.keybd_event(vk, 0, 0, 0)
        time.sleep(0.06)
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.25)
        print('tombol 0x%02X dikirim' % vk)
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())
