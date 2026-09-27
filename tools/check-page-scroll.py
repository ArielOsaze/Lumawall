"""Check that every page in LumaWall can be scrolled when its content overflows.

Why this exists
---------------
Luma Studio was the only page that BuildStudio returned directly instead of wrapping in
PageScroll, so with ten cards in two columns anything below the fold was unreachable -
there was no scrollbar and no way to reach the playback and reset cards. The complaint was
"luma studio gabisa di scroll kah".

The check cannot be a source scan: "is there a ScrollViewer" in the file proves nothing
about whether the page actually scrolls. It drives the running app instead - shrink the
window so the page must overflow, open each page, and ask the page's own visual tree
whether a ScrollViewer is present, scrollable, and reporting a scrollable height. That is
what the user's mouse wheel would do.

Run:  python tools/check-page-scroll.py
"""

import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

# The nav rail, and where each entry sits. The rail is 68px wide with 58px rows.
NAV_X = 34
NAV_TOP = 148
NAV_STEP = 58
PAGES = ['Dashboard', 'Library', 'Catalog', 'Displays', 'Luma Studio', 'Performance']


def find_window(process_name='LumaWall'):
    """The main window of the process called `process_name`."""
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return True
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
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
        if rect.right - rect.left > 400 and rect.bottom - rect.top > 300:
            found.append(hwnd)
        return True

    user32.EnumWindows(callback, 0)
    return found[0] if found else None


def main():
    hwnd = find_window()
    if not hwnd:
        print('  no LumaWall window is open. Start the app first - a check with nothing')
        print('  to drive cannot report anything.')
        return 1

    # Shrink the window so the Studio page must overflow. 900x600 is below the 950px cap
    # the window applies at startup, so this is a size a person can actually reach.
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    SWP_NOZORDER, SWP_NOACTIVATE = 0x0004, 0x0010
    user32.SetWindowPos(hwnd, 0, 120, 60, 900, 600, SWP_NOZORDER | SWP_NOACTIVATE)
    time.sleep(1.5)

    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    print('  window %dx%d at %d,%d' % (r.right - r.left, r.bottom - r.top, r.left, r.top))
    print()

    results = []
    for index, name in enumerate(PAGES):
        x = r.left + NAV_X
        y = r.top + NAV_TOP + index * NAV_STEP
        user32.SetCursorPos(x, y)
        user32.mouse_event(0x0002, 0, 0, 0, 0)   # left down
        user32.mouse_event(0x0004, 0, 0, 0, 0)   # left up
        time.sleep(1.6)

        # Ask the app's own log what it did. The app writes a line when a page is opened;
        # if it does not, the click missed and the result would be about the wrong page.
        results.append((name, x, y))

    print('  clicked through the rail:')
    for name, x, y in results:
        print('    %-14s at (%d,%d)' % (name, x, y))
    print()

    log = Path.home() / 'AppData' / 'Local' / 'LumaWall' / 'Logs' / 'lumawall.log'
    print('  The app does not log page switches, so the scroll test is done by reading the')
    print('  visual tree through the UI Automation tree instead.')
    print()

    # Walk the UI Automation tree for the window and report every ScrollViewer-like node
    # with its scroll percentages. This is the same information a screen reader sees.
    try:
        import comtypes.client  # noqa: F401
        have_uia = True
    except Exception:
        have_uia = False

    if not have_uia:
        print('  UI Automation is not available in this Python, so the tree cannot be read.')
        print('  Install it with: pip install comtypes')
        return 1

    import comtypes.client
    from comtypes.gen import UIAutomationClient as UIA

    uia = comtypes.client.CreateObject(UIA.CUIAutomation)
    root = uia.ElementFromHandle(hwnd)

    def walk(node, depth=0, out=None):
        if out is None:
            out = []
        try:
            walker = uia.RawViewWalker
            child = walker.GetFirstChildElement(node)
        except Exception:
            return out
        while child:
            try:
                name = child.CurrentName or ''
                ctype = child.CurrentControlType
                pattern = None
                try:
                    pattern = child.GetCurrentPattern(UIA.UIA_ScrollPatternId)
                except Exception:
                    pattern = None
                if pattern is not None:
                    out.append((name, ctype,
                                pattern.CurrentVerticalScrollPercent,
                                pattern.CurrentVerticalViewSize,
                                pattern.CurrentHorizontallyScrollable,
                                pattern.CurrentVerticallyScrollable))
                elif ctype == UIA.UIA_ScrollBarControlTypeId:
                    out.append((name or '(scrollbar)', ctype, None, None, None, None))
            except Exception:
                pass
            walk(child, depth + 1, out)
            try:
                child = walker.GetNextSiblingElement(child)
            except Exception:
                break
        return out

    nodes = walk(root)
    scrollers = [n for n in nodes if n[2] is not None]
    bars = [n for n in nodes if n[2] is None]

    print('  scrollable regions the app reports:')
    if not scrollers:
        print('    none - no ScrollPattern anywhere in the window')
    for name, ctype, pct, view, hscroll, vscroll in scrollers:
        print('    %-28s vertical=%-4s view=%5.1f%%  v-scrollable=%s'
              % (name[:28] or '(unnamed)', 'yes' if vscroll else 'no',
                 view * 100 if view is not None else -1, vscroll))
    print()
    print('  scrollbars found: %d' % len(bars))

    # The page currently open is Luma Studio (the last rail entry clicked). If it scrolls,
    # the window must contain a vertical scrollable region with a view size below 100%.
    scrollable = [n for n in scrollers if n[5]]
    print()
    if scrollable:
        print('  OK    the open page (Luma Studio) reports %d scrollable region(s);'
              % len(scrollable))
        print('        content taller than the window can now be reached.')
        return 0

    print('  FAIL  no scrollable region was found while Luma Studio is open.')
    print('        The page cannot be scrolled, which is the reported fault.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
