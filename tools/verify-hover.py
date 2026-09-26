"""verify-hover.py — proves the Aero hover is gone, by counting pixels.

The static check (verify-no-aero-hover.py) proves the style is registered and has no
hover trigger. That is necessary but not sufficient: what matters is what appears on
screen, and only a screenshot settles that. A vision model was asked to read an
earlier capture and got it wrong - it reported a pale blue close button that the
pixels say is (33, 43, 65). Hence counting pixels.

Four traps, every one of which produced a wrong answer first:

  · A minimised window sits at -32000,-32000 with a 160x28 rect, so the button strip
    was measured off-screen.
  · A window straddling two monitors can have the right end of its title bar above
    the second monitor's top edge; the capture of that strip is black, and (0,0,0)
    everywhere reads as "no hover".
  · Another window on top means the app never receives MouseEnter, so the hover never
    appears and the reading is a false pass. The app is raised, and the test checks
    the app is really under the cursor before believing each reading.
  · PIL's ImageGrab and Win32 GetWindowRect use different origins for a multi-monitor
    desktop, so a bbox taken from the rect lands on the wrong monitor. The capture
    goes through CopyFromScreen, which uses the same coordinates as the rect.

Pass conditions: no Aero-blue pixel on any button, and every button still changes on
hover - a hover that does nothing is also a defect, because the pointer then gives no
feedback about what it is about to press.

Run:  python tools/verify-hover.py
"""

import ctypes
import os
import subprocess
import sys
import time

from PIL import Image

AERO = (190, 230, 253)      # #BEE6FD, baked into WPF's default Button template
TOL = 18
HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
SWP_NOSIZE, SWP_NOMOVE, SWP_SHOWWINDOW, SWP_NOACTIVATE = 0x1, 0x2, 0x40, 0x10

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]


def grab(rect, path):
    """Capture a screen rectangle, in the same coordinates GetWindowRect reports."""
    w, h = rect.right - rect.left, rect.bottom - rect.top
    ps = (r'Add-Type -AssemblyName System.Drawing; '
          r'$b = New-Object System.Drawing.Bitmap %d, %d; '
          r'$g = [System.Drawing.Graphics]::FromImage($b); '
          r'$g.CopyFromScreen(%d, %d, 0, 0, $b.Size); '
          r'$b.Save("%s"); $g.Dispose(); $b.Dispose()'
          % (w, h, rect.left, rect.top, os.path.abspath(path)))
    subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                   capture_output=True, timeout=60)
    return Image.open(path).convert('RGB')


def main():
    q = subprocess.run(['powershell', '-NoProfile', '-Command',
                        '(Get-Process LumaWall -ErrorAction SilentlyContinue | Select-Object -First 1).Id'],
                       capture_output=True, text=True)
    if not q.stdout.strip():
        print('  LumaWall is not running')
        return 1
    pid = int(q.stdout.strip())

    found = []

    def cb(h, _):
        p = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(h):
            n = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(h, n, 256)
            if n.value == 'LumaWall':
                found.append(h)
        return True

    CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(CB(cb), None)
    if not found:
        # Not a failure of the app. The app can be running with its window closed - it
        # lives in the tray, so "running but no visible window" is a normal state, and
        # reporting it as a failure made this check unusable unless the window happened
        # to be open. There is nothing to measure in that state, so it says so.
        print('  SKIP: LumaWall is running but has no visible window '
              '(it is in the tray), so there is no title bar to measure')
        return 2
    hwnd = found[0]
    print('  LumaWall pid %d' % pid)

    # Restore, then place the window wholly inside one monitor, so the right end of
    # the title bar is on a screen that exists.
    #
    # SetForegroundWindow fails silently when the calling process does not own the
    # foreground window, and without the foreground the app never receives
    # MouseEnter - so the hover never appears and the test reads zero Aero pixels,
    # which looks like a pass. Attaching to the foreground thread first makes the
    # call take effect. This was the last of four reasons this check lied.
    fg = user32.GetForegroundWindow()
    fgt = user32.GetWindowThreadProcessId(fg, None)
    myt = ctypes.windll.kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(fgt, myt, True)
    user32.ShowWindow(hwnd, 9)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 80, 60, 1200, 800,
                        SWP_SHOWWINDOW | SWP_NOACTIVATE)
    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
    user32.AttachThreadInput(fgt, myt, False)
    time.sleep(1.6)

    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    if r.left < -20000:
        print('  the window is still minimised; restore it and re-run')
        return 1
    w = r.right - r.left
    print('  window %d,%d  %dx%d' % (r.left, r.top, w, r.bottom - r.top))

    strip = RECT(r.right - 150, r.top, r.right, r.top + 54)
    failures = []

    try:
        # With no button hovered, for comparison. Raise first: a previous run leaves
        # the window not-topmost, and another window over that strip makes the base
        # capture black.
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.6)
        user32.SetCursorPos(r.left + w // 3, r.top + 27)
        time.sleep(1.0)
        away = grab(strip, os.path.join('build', 'hover-away.png'))
        base = away.load()
        if sum(base[20, 8]) < 20:
            print('  the captured strip is black - the capture is not landing on the')
            print('  window. Move the app fully onto one monitor and re-run.')
            return 1
        print('  strip with nothing hovered reads %s' % (base[20, 8],))
        print()

        for name, dx in [('minimize', 40), ('maximize', 84), ('close', 128)]:
            # Re-assert the foreground before each reading: another window can take
            # the top slot between samples, and then the app never sees MouseEnter.
            fg2 = user32.GetForegroundWindow()
            fgt2 = user32.GetWindowThreadProcessId(fg2, None)
            user32.AttachThreadInput(fgt2, myt, True)
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            user32.AttachThreadInput(fgt2, myt, False)
            time.sleep(0.5)
            user32.SetCursorPos(r.right - 150 + dx, r.top + 27)
            time.sleep(1.0)

            # Confirm the app is under the pointer before believing the reading.
            pt = POINT(r.right - 150 + dx, r.top + 27)
            hit = user32.WindowFromPoint(pt)
            hp = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hit, ctypes.byref(hp))
            on_app = (hp.value == pid)

            im = grab(strip, os.path.join('build', 'hover-%s.png' % name))
            px = im.load()

            changed = 0
            aero = 0
            cols = {}
            for y in range(54):
                for x in range(150):
                    c = px[x, y]
                    if (abs(c[0] - AERO[0]) < TOL and abs(c[1] - AERO[1]) < TOL
                            and abs(c[2] - AERO[2]) < TOL):
                        aero += 1
                    if c != base[x, y]:
                        changed += 1
                        cols[c] = cols.get(c, 0) + 1

            top = sorted(cols.items(), key=lambda t: -t[1])[:1]
            notes = []
            if aero:
                failures.append('%s shows the Aero blue' % name)
                notes.append('%d AERO PIXELS' % aero)
            if not on_app:
                failures.append('%s: the app was not under the cursor' % name)
                notes.append('not under cursor')
            elif changed < 200:
                failures.append('%s does not react to hover' % name)
                notes.append('no hover')
            if not notes:
                notes.append('%d px changed, hover %s' % (changed, top[0][0] if top else '?'))

            print('    %-9s  %s' % (name, ', '.join(notes)))

        print()
        if failures:
            for f in failures:
                print('  FAIL  %s' % f)
            return 1
        print('  no Aero blue on any button, and each one still lifts on hover')
        print('  crops: build/hover-away.png and build/hover-<button>.png')
        return 0
    finally:
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE)


if __name__ == '__main__':
    sys.exit(main())
