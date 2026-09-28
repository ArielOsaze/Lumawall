"""test_screen.py — park the window a checker drives on a monitor nobody is looking at.

The window checkers have to move the pointer and press real buttons, because the
questions they answer - "is the hover visible", "does clicking here put the clock
there" - are about what happens on screen and cannot be answered from a screenshot
of the app's own drawing.

That means the pointer jumps around the desktop while the suite runs, and the app
window sits in the middle of the screen the user is working on. Running the suite
was therefore something you could not do while using the machine.

So: the checkers move the window they drive onto a monitor that is not the primary
one, and move it back afterwards.

Choosing the monitor
--------------------

Prefer, in order:

  1. $LUMAWALL_TEST_SCREEN, when set: a device name ("\\\\.\\DISPLAY3") or a 1-based
     index into the enumeration order. An explicit choice always wins.
  2. The smallest non-primary monitor. Smallest, not first, because a checker that
     drives a 1920x1080 window is less in the way on the 1366x768 panel, and a
     smaller window is quicker to raise and screenshot.
  3. The primary monitor, when it is the only one. On a single-monitor machine the
     tests still have to run somewhere.

The window is placed at the monitor's top-left with a small margin, not centred, so
that two checkers running one after another do not leave the window somewhere new
each time.

Run it directly to see what it would choose:

    python tools/test_screen.py
"""

import ctypes
import ctypes.wintypes as wintypes
import os

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

CCHDEVICENAME = 32


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


class MONITORINFOEX(ctypes.Structure):
    """MONITORINFO plus the device name.

    szDevice is the reason to use this rather than plain MONITORINFO: it carries
    "\\\\.\\DISPLAY2", the same name the app's config uses, so a checker can be told
    which monitor to use by the name the user would recognise. MONITORINFO alone only
    offers the enumeration order, which does not correspond to the names.
    """
    _fields_ = [('cbSize', wintypes.DWORD), ('rcMonitor', RECT),
                ('rcWork', RECT), ('dwFlags', wintypes.DWORD),
                ('szDevice', ctypes.c_wchar * CCHDEVICENAME)]


MONITORENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.POINTER(RECT), ctypes.c_void_p)

MONITORINFOF_PRIMARY = 1
HWND_TOP = 0
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010


def monitors():
    """Every monitor, left to right, as dicts: device, x, y, width, height, primary."""
    found = []

    def callback(hmonitor, hdc, rect, data):
        info = MONITORINFOEX()
        info.cbSize = ctypes.sizeof(MONITORINFOEX)
        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            r = info.rcMonitor
            found.append({
                'device': info.szDevice,
                'x': r.left, 'y': r.top,
                'width': r.right - r.left, 'height': r.bottom - r.top,
                'primary': bool(info.dwFlags & MONITORINFOF_PRIMARY),
            })
        return 1

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), None)
    found.sort(key=lambda m: (m['x'], m['y']))
    return found


def choose(monitors_list=None, need_width=0, need_height=0):
    """The monitor a checker should drive, by the rules in the module docstring.

    need_width/need_height, when given, restrict the choice to monitors the window
    actually fits on. A window larger than the monitor is not merely cramped: the part
    that hangs off the edge cannot be clicked, so a checker that clicks by screen
    coordinate fails with "the click missed the cell" about a pad that is off-screen.
    That is what happened with a 1580x950 window on the 1366x768 panel - the pad sat at
    y=801 on a 768-tall screen.
    """
    found = monitors_list if monitors_list is not None else monitors()
    if not found:
        return None

    def fits(m):
        return m['width'] >= need_width and m['height'] >= need_height

    wanted = os.environ.get('LUMAWALL_TEST_SCREEN', '').strip()
    if wanted:
        for m in found:
            if m['device'].upper() == wanted.upper():
                return m
        if wanted.isdigit():
            index = int(wanted) - 1
            if 0 <= index < len(found):
                return found[index]
        # An explicit choice that matches nothing is a mistake worth hearing about,
        # rather than silently falling back to the screen the user is working on.
        raise SystemExit(
            'LUMAWALL_TEST_SCREEN=%s does not match a monitor. Available: %s'
            % (wanted, ', '.join(m['device'] for m in found)))

    others = [m for m in found if not m['primary'] and fits(m)]
    if others:
        return min(others, key=lambda m: m['width'] * m['height'])
    # No non-primary monitor is big enough. Prefer the primary if it fits - being in the
    # way is worse than not running the check, and a window that fits is still clickable.
    for m in found:
        if m['primary'] and fits(m):
            return m
    # Nothing fits: return the largest, so the caller can at least resize into it.
    return max(found, key=lambda m: m['width'] * m['height'])


def park(hwnd, monitor=None, margin=8, resize_to_fit=False):
    """Move a window onto the chosen monitor. Returns (monitor, previous_rect).

    The size is left alone by default: some checkers measure the title-bar strip at the
    window's own top-right, so resizing would move the thing they are measuring. With
    resize_to_fit the window is made to fit the monitor, which is what a checker that
    clicks by coordinate needs when the window is larger than the screen it was moved to.

    The previous rectangle is returned so the caller can put the window back. The
    window being moved is the user's own running LumaWall: leaving it on another
    monitor after the suite finishes would be a change they did not ask for.
    """
    target = monitor
    if target is None and hwnd:
        if resize_to_fit:
            # The window will be made to fit whatever monitor is chosen, so the only
            # requirement is that the monitor is not the one the user is working on.
            target = choose()
        else:
            # The window keeps its size, so the monitor has to be able to hold it: a
            # window hanging off the edge has parts that cannot be clicked.
            r = rect_of(hwnd)
            target = choose(need_width=r.right - r.left, need_height=r.bottom - r.top)
    if target is None or not hwnd:
        return None, None
    before = rect_of(hwnd)

    width, height = 0, 0
    if resize_to_fit:
        w = before.right - before.left
        h = before.bottom - before.top
        width = min(w, target['width'] - 2 * margin)
        height = min(h, target['height'] - 2 * margin)

    user32.SetWindowPos(hwnd, HWND_TOP, target['x'] + margin, target['y'] + margin,
                        width, height, SWP_NOZORDER | SWP_NOACTIVATE)
    return target, before


def restore(hwnd, before):
    """Put a window back where park() found it, at the size it had."""
    if not hwnd or not before:
        return
    user32.SetWindowPos(hwnd, HWND_TOP, before.left, before.top,
                        before.right - before.left, before.bottom - before.top,
                        SWP_NOZORDER | SWP_NOACTIVATE)


class parked(object):
    """Context manager: move the window for the duration, then put it back.

        with test_screen.parked(hwnd, resize_to_fit=True) as monitor:
            ...drive the window...

    The restore happens even when the body raises, so a checker that fails halfway
    does not leave the user's window stranded - or resized - on the test monitor.
    """

    def __init__(self, hwnd, monitor=None, margin=8, resize_to_fit=False):
        self.hwnd = hwnd
        self.monitor = monitor
        self.margin = margin
        self.resize_to_fit = resize_to_fit
        self.before = None

    def __enter__(self):
        self.monitor, self.before = park(self.hwnd, self.monitor, self.margin,
                                         self.resize_to_fit)
        return self.monitor

    def __exit__(self, *exc):
        restore(self.hwnd, self.before)
        return False


def rect_of(hwnd):
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r


def describe(monitor):
    if not monitor:
        return 'no monitor'
    return '%s %dx%d at %d,%d%s' % (
        monitor['device'], monitor['width'], monitor['height'],
        monitor['x'], monitor['y'], ' (primary)' if monitor['primary'] else '')


if __name__ == '__main__':
    every = monitors()
    print('monitors:')
    for m in every:
        print('  %s' % describe(m))
    print()
    print('a checker would drive: %s' % describe(choose(every)))
    print()
    print('set LUMAWALL_TEST_SCREEN to force one, e.g. LUMAWALL_TEST_SCREEN=\\\\.\\DISPLAY3')
