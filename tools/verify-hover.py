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


TITLE_BUTTONS = ('Minimize', 'Maximize', 'Close to tray')


def title_buttons(window_rect):
    """[(name, x)] for the title-bar buttons, read from the app itself.

    The buttons are found by name through UI Automation rather than by fixed offsets from
    the window's right edge. The offsets that were used before - right-110, right-66,
    right-22 - were correct for a 1580x950 window on the primary screen, and two of the
    three missed once the window was moved and resized to fit the 1366x768 test monitor.
    The reading then said "minimize does not react to hover" about a button that was fine.

    Falls back to the old offsets only if UI Automation cannot answer, so a machine where
    the automation server is unavailable still gets a measurement rather than a crash.
    """
    script = r'''
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$auto = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$ctrl = [System.Windows.Automation.ControlType]
$win = $auto::RootElement.FindFirst($scope::Children,
    (New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')))
if (-not $win) { Write-Output 'NO_WINDOW'; exit }
$bcond = New-Object System.Windows.Automation.PropertyCondition($auto::ControlTypeProperty, $ctrl::Button)
foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
    $n = $b.Current.Name
    if ($n -eq 'Minimize' -or $n -eq 'Maximize' -or $n -eq 'Close to tray') {
        $br = $b.Current.BoundingRectangle
        if ($br.Width -gt 0) {
            Write-Output ('BTN|{0}|{1}|{2}' -f $n, [int]($br.X + $br.Width / 2), [int]($br.Y + $br.Height / 2))
        }
    }
}
'''
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command', script],
                             capture_output=True, timeout=90)
        text = out.stdout.decode('utf-8', 'replace')
    except Exception:
        text = ''

    found = {}
    for line in text.splitlines():
        if line.startswith('BTN|'):
            parts = line.split('|')
            found[parts[1]] = (int(parts[2]), int(parts[3]))

    if len(found) == len(TITLE_BUTTONS):
        # Absolute screen coordinates, so the caller does not need to know the offsets.
        return [(name.lower().split()[0], found[name]) for name in TITLE_BUTTONS]

    # Fallback: the offsets that were correct before, as absolute positions. y is 27px
    # below the window top, which is where the buttons sit in this title bar.
    y = window_rect.top + 27
    return [('minimize', (window_rect.right - 116, y)),
            ('maximize', (window_rect.right - 72, y)),
            ('close', (window_rect.right - 28, y))]


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

    # Park the window on a monitor the user is not working on, and put it back at the
    # end. Driving this window means moving the pointer to its title bar and raising it
    # above everything; doing that on the primary monitor takes over the screen the
    # user is using. The restore is a finally, so an early return still puts it back.
    import test_screen
    monitor, was_at = test_screen.park(hwnd, margin=40, resize_to_fit=True)
    print('  driving it on %s' % test_screen.describe(monitor))
    try:
        return _measure(hwnd, monitor, pid)
    finally:
        test_screen.restore(hwnd, was_at)


def _measure(hwnd, monitor, pid):
    # The owning process id is passed in rather than looked up again: the hover is only
    # believed when the window under the cursor belongs to this process, and a name that
    # is not in scope here would raise instead - which is what happened when this became
    # its own function and the parameter was forgotten.
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
    # Raised, but NOT resized or moved: park() already put the window where it belongs,
    # and changing it here desynchronised this check from the buttons it aims at.
    #
    # Measured: park() left the window at 1280 wide (right edge 3240), then this call
    # shrank it to 1200 (right edge 3160) - and UI Automation went on reporting the
    # buttons at 3124/3168/3212, positions from the OLD width. Two of the three were then
    # outside the window, the pointer landed on the desktop, and the check reported that
    # the buttons did not react.
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
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
    h = r.bottom - r.top
    # A minimised window reports a 160x28 sentinel at a normal-looking position on some
    # builds, and a strip measured from it is empty screen - every button "reacts",
    # because the pixels being compared are the desktop behind it. That produced a PASS
    # over a window that was not on screen. A real window here is at least 900x600.
    if w < 900 or h < 600:
        print('  the window is %dx%d, which is not a restored window; re-run with it open'
              % (w, h))
        return 1
    print('  window %d,%d  %dx%d' % (r.left, r.top, w, h))

    # The strip is wide enough for all three buttons and their spacing, taken from where
    # the buttons really are rather than from a fixed 150px: the buttons are 44px wide and
    # the leftmost sits 138px from the right edge at this size, so 150 was only just enough.
    buttons = title_buttons(r)
    leftmost = min(x for _, (x, _) in buttons) - 40
    strip = RECT(leftmost, r.top, r.right, r.top + 54)
    print('  buttons at %s' % ', '.join('%s x=%d' % (n, x) for n, (x, _) in buttons))
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

        for name, (button_x, _) in buttons:
            # Re-assert the foreground before each reading: another window can take
            # the top slot between samples, and then the app never sees MouseEnter.
            #
            # SetForegroundWindow alone is not reliable here. Windows refuses it when the
            # calling process is not the foreground process - which is the case when this
            # runs from a terminal, and also when it runs inside the checker suite with
            # other tools having opened windows. The symptom is a checker that passes alone
            # and fails in the suite, reporting "minimize does not react to hover" about a
            # button that is perfectly fine.
            #
            # The topmost bounce is the standard way to force it: raise above everything,
            # then drop topmost again so the window is not left floating.
            #
            # The raise is not instant, and one attempt is not enough in the suite: a
            # checker that ran just before can still own the top slot for a moment, and the
            # reading is then taken against whatever window is there instead. That was the
            # in-suite failure - "close: the app was not under the cursor" on the last
            # sample only. So retry until the app really is under the pointer, and give up
            # after a few tries rather than reading a stale window.
            on_app = False
            for attempt in range(4):
                fg2 = user32.GetForegroundWindow()
                fgt2 = user32.GetWindowThreadProcessId(fg2, None)
                user32.AttachThreadInput(fgt2, myt, True)
                user32.ShowWindow(hwnd, 9)                      # SW_RESTORE
                user32.BringWindowToTop(hwnd)
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                    SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
                user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                                    SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
                user32.SetForegroundWindow(hwnd)
                user32.AttachThreadInput(fgt2, myt, False)
                time.sleep(0.6)
                user32.SetCursorPos(button_x, r.top + 27)
                time.sleep(1.0)

                # Confirm the app is under the pointer before believing the reading.
                pt = POINT(button_x, r.top + 27)
                hit = user32.WindowFromPoint(pt)
                hp = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hit, ctypes.byref(hp))
                on_app = (hp.value == pid)
                if on_app:
                    break

            im = grab(strip, os.path.join('build', 'hover-%s.png' % name))
            px = im.load()

            # The comparison is over the whole captured strip, sized from the buttons
            # themselves, rather than a fixed 150x54 that could cut a button off.
            sw = strip.right - strip.left
            sh = strip.bottom - strip.top
            changed = 0
            aero = 0
            cols = {}
            for y in range(sh):
                for x in range(sw):
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
