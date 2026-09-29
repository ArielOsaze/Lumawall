"""Klik elemen di Chrome lewat UI Automation (InvokePattern / LegacyIAccessible).

Pemakaian:
  python tools/chrome_invoke.py --list "Packages"
  python tools/chrome_invoke.py --click "Packages"
  python tools/chrome_invoke.py --click "Store listings"
  python tools/chrome_invoke.py --dump            # semua elemen yang bisa diklik
"""
import argparse
import sys
import time

import win32gui
import win32api
import win32con
import uiautomation as auto


def chrome_hwnd():
    found = []

    def cb(h, _):
        if not win32gui.IsWindowVisible(h):
            return
        cls = win32gui.GetClassName(h)
        r = win32gui.GetWindowRect(h)
        if 'Chrome_WidgetWin' in cls and (r[2] - r[0]) > 800:
            found.append((h, win32gui.GetWindowText(h), r))
    win32gui.EnumWindows(cb, None)
    if not found:
        return None, None, None
    found.sort(key=lambda t: -((t[2][2] - t[2][0]) * (t[2][3] - t[2][1])))
    return found[0]


def activate(hwnd):
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
    time.sleep(0.4)


def collect(ctrl, depth=0, limit=40, out=None):
    """Kumpulkan semua kontrol yang punya nama."""
    if out is None:
        out = []
    if depth > limit:
        return out
    try:
        children = ctrl.GetChildren()
    except Exception:
        return out
    for c in children:
        try:
            name = c.Name or ''
            ct = c.ControlTypeName
        except Exception:
            continue
        if name:
            out.append((c, ct, depth, name))
        collect(c, depth + 1, limit, out)
    return out


def try_invoke(c):
    """Coba semua pola yang bisa mengklik."""
    # 1) InvokePattern
    try:
        p = c.GetInvokePattern()
        p.Invoke()
        return 'InvokePattern'
    except Exception:
        pass
    # 2) LegacyIAccessible DoDefaultAction
    try:
        p = c.GetLegacyIAccessiblePattern()
        p.DoDefaultAction()
        return 'LegacyIAccessible'
    except Exception:
        pass
    # 3) klik di tengah kotaknya
    try:
        r = c.BoundingRectangle
        x = (r.left + r.right) // 2
        y = (r.top + r.bottom) // 2
        if r.right > r.left:
            win32api.SetCursorPos((x, y))
            time.sleep(0.15)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.09)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return 'klik-piksel (%d,%d)' % (x, y)
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list')
    ap.add_argument('--click')
    ap.add_argument('--dump', action='store_true')
    ap.add_argument('--exact', action='store_true', help='nama harus sama persis')
    args = ap.parse_args()

    hwnd, title, rect = chrome_hwnd()
    if hwnd is None:
        print('Chrome tidak ditemukan')
        return 2
    print('Chrome: %s' % title[:60])
    activate(hwnd)

    win = auto.ControlFromHandle(hwnd)
    if win is None:
        print('tidak bisa ambil kontrol')
        return 2

    items = collect(win)
    print('total kontrol bernama: %d' % len(items))

    if args.dump:
        for c, ct, d, name in items:
            if ct in ('HyperlinkControl', 'ButtonControl', 'ListItemControl',
                      'TextControl', 'TabItemControl'):
                r = c.BoundingRectangle
                print('   %-18s d=%-2d %-55s (%d,%d)'
                      % (ct, d, name[:55], (r.left + r.right) // 2, (r.top + r.bottom) // 2))
        return 0

    target = args.list or args.click
    if not target:
        return 0

    hits = []
    for c, ct, d, name in items:
        if args.exact:
            ok = (name.strip() == target)
        else:
            ok = (target.lower() in name.lower())
        if ok:
            hits.append((c, ct, d, name))

    print('cocok: %d' % len(hits))
    for c, ct, d, name in hits:
        r = c.BoundingRectangle
        print('   %-18s %-50s (%d,%d %dx%d)'
              % (ct, name[:50], r.left, r.top, r.right - r.left, r.bottom - r.top))

    if args.list:
        return 0

    if args.click:
        if not hits:
            print('tidak ada yang cocok')
            return 1
        # pilih yang paling mungkin: Hyperlink/ListItem/Button dulu
        order = {'HyperlinkControl': 0, 'ListItemControl': 1, 'ButtonControl': 2,
                 'TextControl': 3, 'TabItemControl': 4}
        hits.sort(key=lambda h: (order.get(h[1], 9), h[2]))
        for c, ct, d, name in hits[:4]:
            how = try_invoke(c)
            if how:
                print('-> %s via %s' % (name[:50], how))
                time.sleep(1.0)
                return 0
        print('semua cara gagal')
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
