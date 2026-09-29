"""Isi file dialog Windows lewat UI Automation ValuePattern.

Pemakaian:
  python tools/file_dialog.py --list
  python tools/file_dialog.py --set "C:\\path\\ke\\file.msix"
  python tools/file_dialog.py --open          # klik tombol Open
"""
import argparse
import sys
import time

import uiautomation as auto
import win32gui


def find_dialog():
    """Cari jendela dialog file (judul 'Open' / 'Save As')."""
    found = []

    def cb(h, _):
        if not win32gui.IsWindowVisible(h):
            return
        t = win32gui.GetWindowText(h)
        cls = win32gui.GetClassName(h)
        if t in ('Open', 'Save As', 'Select File', 'Choose File') or \
           ('#32770' in cls and 'Open' in t):
            found.append((h, t))
    win32gui.EnumWindows(cb, None)
    return found


def walk(c, depth=0, out=None):
    if out is None:
        out = []
    if depth > 25:
        return out
    try:
        kids = c.GetChildren()
    except Exception:
        return out
    for k in kids:
        try:
            ct = k.ControlTypeName
            n = k.Name or ''
        except Exception:
            continue
        out.append((ct, n, k))
        walk(k, depth + 1, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--set')
    ap.add_argument('--open', action='store_true')
    args = ap.parse_args()

    dialogs = find_dialog()
    if not dialogs:
        print('dialog file tidak ditemukan')
        return 2
    hwnd, title = dialogs[0]
    print('dialog: hwnd=%d "%s"' % (hwnd, title))

    win = auto.ControlFromHandle(hwnd)
    if win is None:
        print('kontrol tidak didapat')
        return 2

    items = walk(win)
    edits = [(ct, n, k) for ct, n, k in items if ct == 'EditControl']
    buttons = [(ct, n, k) for ct, n, k in items if ct == 'ButtonControl']

    if args.list:
        print('Edit:')
        for ct, n, k in edits:
            try:
                v = k.GetValuePattern().Value or ''
            except Exception:
                v = '(?)'
            print('   %-24s value=%r' % (n[:24], v[:70]))
        print('Button:')
        for ct, n, k in buttons:
            print('   %s' % n[:50])
        return 0

    if args.set:
        # pilih Edit "File name:" (bukan Search Box)
        target = None
        for ct, n, k in edits:
            if 'file name' in n.lower():
                target = k
                break
        if target is None:
            for ct, n, k in edits:
                if 'search' not in n.lower():
                    target = k
        if target is None:
            print('field nama file tidak ditemukan')
            return 1
        try:
            target.GetValuePattern().SetValue(args.set)
            print('nilai diset:', args.set)
        except Exception as e:
            print('SetValue gagal:', e)
            return 1
        time.sleep(0.5)
        return 0

    if args.open:
        target = None
        for ct, n, k in buttons:
            if n.strip().lower() == 'open':
                target = k
                break
        if target is None:
            print('tombol Open tidak ditemukan')
            return 1
        try:
            target.GetInvokePattern().Invoke()
            print('tombol Open diklik')
        except Exception:
            # fallback: klik piksel
            r = target.BoundingRectangle
            import win32api, win32con
            x = (r.left + r.right) // 2
            y = (r.top + r.bottom) // 2
            win32api.SetCursorPos((x, y))
            time.sleep(0.15)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.09)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            print('tombol Open diklik (piksel %d,%d)' % (x, y))
        time.sleep(1.0)
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())
