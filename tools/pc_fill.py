"""Isi field di Chrome (Partner Center) lewat UI Automation ValuePattern.

Pemakaian:
  python tools/pc_fill.py --list                 # daftar semua Edit/Document
  python tools/pc_fill.py --fill "TEXT"          # isi Edit yang punya fokus
  python tools/pc_fill.py --fill-at INDEX "TEXT" # isi Edit ke-INDEX
  python tools/pc_fill.py --click INDEX          # klik (Invoke/fokus) kontrol ke-INDEX
"""
import argparse
import sys

try:
    import uiautomation as auto
except ImportError:
    print('uiautomation tidak terpasang')
    sys.exit(2)


def chrome_window():
    """Jendela Chrome yang paling depan (atau yang terbesar)."""
    best = None
    best_area = 0
    for w in auto.GetRootControl().GetChildren():
        try:
            name = w.Name or ''
            cls = w.ClassName or ''
        except Exception:
            continue
        if 'Chrome' not in cls and 'Chrome' not in name:
            continue
        r = w.BoundingRectangle
        area = max(0, r.right - r.left) * max(0, r.bottom - r.top)
        if area > best_area:
            best_area = area
            best = w
    return best


def walk(ctrl, depth=0, limit=14, out=None):
    """Kumpulkan semua kontrol Edit/Document/Button yang terlihat."""
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
            ct = c.ControlTypeName
        except Exception:
            continue
        try:
            r = c.BoundingRectangle
            visible = (r.right - r.left) > 1 and (r.bottom - r.top) > 1
        except Exception:
            visible = False
        if visible and ct in ('EditControl', 'DocumentControl', 'ButtonControl'):
            out.append((c, ct, depth))
        walk(c, depth + 1, limit, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--fill')
    ap.add_argument('--fill-at', nargs=2, metavar=('INDEX', 'TEXT'))
    ap.add_argument('--click')
    ap.add_argument('--focus', action='store_true', help='bawa jendela ke depan dulu')
    args = ap.parse_args()

    win = chrome_window()
    if win is None:
        print('jendela Chrome tidak ditemukan')
        return 2

    if args.focus:
        try:
            win.SetActive()
        except Exception as e:
            print('SetActive gagal:', e)
        auto.SetForegroundWindow(win.NativeWindowHandle)

    items = walk(win)
    edits = [it for it in items if it[1] == 'EditControl']
    print('total kontrol terlihat: %d  (Edit: %d)' % (len(items), len(edits)))

    if args.list:
        for i, (c, ct, d) in enumerate(edits):
            r = c.BoundingRectangle
            name = (c.Name or '')[:60]
            val = ''
            try:
                vp = c.GetValuePattern()
                val = (vp.Value or '')[:50]
            except Exception:
                pass
            print('  [%2d] d=%-2d (%4d,%4d %4dx%-4d) name=%-40s value=%s'
                  % (i, d, r.left, r.top, r.right - r.left, r.bottom - r.top,
                     repr(name), repr(val)))
        return 0

    if args.fill is not None:
        # Edit yang sedang fokus
        for c, ct, d in edits:
            try:
                if c.HasKeyboardFocus:
                    c.GetValuePattern().SetValue(args.fill)
                    print('terisi (fokus):', args.fill)
                    return 0
            except Exception:
                pass
        print('tidak ada Edit yang fokus')
        return 1

    if args.fill_at:
        idx = int(args.fill_at[0])
        text = args.fill_at[1]
        if idx >= len(edits):
            print('index %d di luar jangkauan (ada %d Edit)' % (idx, len(edits)))
            return 1
        c = edits[idx][0]
        try:
            c.GetValuePattern().SetValue(text)
            print('terisi [%d]:' % idx, text)
            return 0
        except Exception as e:
            print('SetValue gagal:', e)
            return 1

    if args.click:
        idx = int(args.click)
        if idx >= len(items):
            print('index %d di luar jangkauan (ada %d kontrol)' % (idx, len(items)))
            return 1
        c = items[idx][0]
        r = c.BoundingRectangle
        cx = (r.left + r.right) // 2
        cy = (r.top + r.bottom) // 2
        try:
            c.SetFocus()
            print('fokus diberikan ke [%d] di (%d, %d)' % (idx, cx, cy))
        except Exception as e:
            print('SetFocus gagal:', e)
        return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())
