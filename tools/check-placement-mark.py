"""Check that the placement pad shows the clock where the timer will actually go.

Why this exists
---------------
The placement picker was redesigned twice and both designs were checked by eye.

The first was nine cells containing nine dots. It "passed" every measurement and was still
unreadable: nine anonymous dots do not say which side is which. The user's words were
"placement bagian ini loh kirainya apa kananya apa kadang bikin bingung".

The second was nine cells each containing a miniature 3x3 screen. That one was broken by
arithmetic: a cell is 40px, its inner grid 32px, so each sub-cell was 10.7px and the 13px
clock mark overflowed into its neighbours.

The design now is one screen with one clock mark on it, and nine invisible drop targets. So
the question is not "are there nine cells" but "is the mark where the chosen position says it
is", and that is a question about pixels.

How it checks
-------------
The pad is not located by guessing offsets from a label - that was wrong three times. It is
located from the mark itself: with the position at middle-centre the mark is at the centre of
the pad, so the pad's origin is the mark's centre minus half the pad. That is self-calibrating
and cannot drift when the layout changes.

Each click is then confirmed twice:
  * the config file must record the position that was clicked - proof the click landed on the
    right cell, not just somewhere on the page;
  * the mark must be drawn in the third of the pad that position names - proof the pad shows
    what it recorded.

A pad that ignores clicks fails the first check. A pad that records the click but does not
move the mark fails the second. Both were real bugs here.

Usage: python tools/check-placement-mark.py
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SHOT = ROOT / 'build' / 'placement-check.png'
CONFIG = Path.home() / 'AppData' / 'Local' / 'LumaWall' / 'config.json'

# Where the mark must be, as a fraction of the pad. The pad is the screen, so a third is
# 0.17 / 0.50 / 0.83.
FRACTION = {'left': 0.17, 'center': 0.50, 'right': 0.83,
            'top': 0.17, 'middle': 0.50, 'bottom': 0.83}

# Positions to drive, in order. Three is enough to prove the mark moves and lands in
# different thirds; more would only take longer.
POSITIONS = ['top-left', 'bottom-right', 'middle-center']

# The pad is 126x126 by construction.
PAD = 126.0

# How far the mark may sit from where the position says, as a fraction of the pad. A third
# is 0.33 wide, so 0.16 keeps a pass inside the right cell while allowing for the mark's own
# size and for the pad not being pixel-aligned.
TOLERANCE = 0.16

LABELS = [
    'Kiri atas', 'Atas tengah', 'Kanan atas',
    'Kiri tengah', 'Tengah', 'Kanan tengah',
    'Kiri bawah', 'Bawah tengah', 'Kanan bawah',
    'Top left', 'Top centre', 'Top right',
    'Middle left', 'Centre', 'Middle right',
    'Bottom left', 'Bottom centre', 'Bottom right',
]


def ps(script, timeout=200):
    p = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                        '-Command', script],
                       capture_output=True, text=True, timeout=timeout)
    return (p.stdout or '') + (p.stderr or '')


# Which process to drive.
#
# Get-Process LumaWall can return more than one: the app itself, and any short-lived
# instance another checker started (--render-timer runs the same executable). Taking the
# first one picked the wrong process when the suite ran them back to back, and every
# coordinate derived from it was wrong - the click for bottom-right landed outside the pad
# and the app recorded middle-center.
#
# The app is the one with a main window. That is the only one that can be photographed and
# clicked, so it is the only one worth finding.
PROCESS = r'''
$proc = Get-Process LumaWall -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } |
        Sort-Object StartTime | Select-Object -First 1
if (-not $proc) { Write-Output 'NO_PROCESS'; exit 1 }
'''


def config_position():
    """The position the app has recorded, or None if it cannot be read."""
    try:
        return json.loads(CONFIG.read_text(encoding='utf-8'))['Timer'].get('Position')
    except Exception:
        return None


def click(x, y):
    """Click at a screen coordinate, after making sure the app is the foreground window.

    SetForegroundWindow alone is not enough: Windows refuses it when the calling process is
    not the foreground process, which is exactly the case when a checker is driving the app
    from a terminal. The click then lands on the terminal, the app records nothing, and the
    checker blames the app. That happened: every position recorded as middle-center.

    ShowWindow(SW_RESTORE) + SetWindowPos(HWND_TOPMOST) + SetWindowPos(HWND_NOTOPMOST)
    is the standard way to force it: the topmost bounce brings the window forward and the
    second call removes topmost so the app is not left floating above everything.
    """
    out = ps(r'''
Add-Type @"
using System;using System.Runtime.InteropServices;
public class N {
 [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint x,uint y,uint d,int e);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
 [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
 [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
 [DllImport("user32.dll")] public static extern int GetWindowTextW(IntPtr h, System.Text.StringBuilder s, int n);
 public static string Title(IntPtr h){ var sb=new System.Text.StringBuilder(300); GetWindowTextW(h,sb,300); return sb.ToString(); }
 public static bool Focus(IntPtr h) {
   ShowWindow(h, 9);
   BringWindowToTop(h);
   SetWindowPos(h, new IntPtr(-1), 0,0,0,0, 0x0001 | 0x0002 | 0x0040);
   SetWindowPos(h, new IntPtr(-2), 0,0,0,0, 0x0001 | 0x0002 | 0x0040);
   SetForegroundWindow(h);
   System.Threading.Thread.Sleep(250);
   return GetForegroundWindow() == h;
 }
 public static void Click(int x,int y){ SetCursorPos(x,y); System.Threading.Thread.Sleep(130);
  mouse_event(2,0,0,0,0); System.Threading.Thread.Sleep(80); mouse_event(4,0,0,0,0); } }
"@
$p = Get-Process LumaWall -ErrorAction SilentlyContinue |
      Where-Object { $_.MainWindowHandle -ne 0 } | Sort-Object StartTime | Select-Object -First 1
if (-not $p) { Write-Output 'NO_PROCESS'; exit 1 }
[void][N]::Focus($p.MainWindowHandle)
# What actually has the focus at the moment of the click? If it is not LumaWall the click
# lands somewhere else, and the checker would blame the app for a click it never delivered.
Write-Output ('BEFORE ' + [N]::Title([N]::GetForegroundWindow()))
[N]::Click(%d, %d)
Start-Sleep -Milliseconds 120
Write-Output ('AFTER  ' + [N]::Title([N]::GetForegroundWindow()))
''' % (int(x), int(y)), timeout=60)
    return out


def find_mark():
    """The clock mark: the accent-coloured block shaped like it, about 22x9."""
    subprocess.run([sys.executable, str(ROOT / 'tools' / 'shot-window.py'), str(SHOT)],
                   capture_output=True, text=True, cwd=str(ROOT), timeout=200)
    if not SHOT.exists():
        return None
    a = np.asarray(Image.open(SHOT).convert('RGB')).astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    red = (r > 170) & (g < 95) & (b < 130)

    ys, xs = np.where(red)
    if len(ys) == 0:
        return None
    seen = np.zeros_like(red, dtype=bool)
    best = None
    for sy, sx in zip(ys.tolist(), xs.tolist()):
        if seen[sy, sx]:
            continue
        stack = [(sy, sx)]
        seen[sy, sx] = True
        pts = []
        while stack:
            cy, cx = stack.pop()
            pts.append((cy, cx))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < red.shape[0] and 0 <= nx < red.shape[1] \
                        and red[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        py = [p[0] for p in pts]
        px = [p[1] for p in pts]
        w = max(px) - min(px) + 1
        h = max(py) - min(py) + 1
        if 16 <= w <= 30 and 5 <= h <= 14:
            cand = {'w': w, 'h': h, 'n': len(pts),
                    'cx': (min(px) + max(px)) / 2.0,
                    'cy': (min(py) + max(py)) / 2.0}
            if best is None or cand['n'] > best['n']:
                best = cand
    return best


def window_origin():
    out = ps(r'''
Add-Type @"
using System;using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
 public struct R { public int L,T,Rr,B; } }
"@
''' + PROCESS + r'''
$r = New-Object W+R
[void][W]::GetWindowRect($proc.MainWindowHandle, [ref]$r)
Write-Output ('ORIGIN {0} {1}' -f $r.L, $r.T)
''')
    line = [l for l in out.splitlines() if l.startswith('ORIGIN')]
    if not line:
        return None
    parts = line[0].split()
    return int(parts[1]), int(parts[2])


def open_studio():
    """Bring the window up, open Luma Studio, and scroll the placement card into view."""
    out = ps(r'''
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System;using System.Runtime.InteropServices;
public class W {
 [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); }
"@
$auto = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$ctrl = [System.Windows.Automation.ControlType]
$win = $auto::RootElement.FindFirst($scope::Children,
    (New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')))
if (-not $win) { Write-Output 'NO_WINDOW'; exit 1 }

# A minimised window cannot be photographed and its rectangle is the -32000 sentinel.
''' + PROCESS + r'''
[void][W]::ShowWindow($proc.MainWindowHandle, 9)
Start-Sleep -Milliseconds 700
[void][W]::SetForegroundWindow($proc.MainWindowHandle)
Start-Sleep -Milliseconds 400

$bcond = New-Object System.Windows.Automation.PropertyCondition($auto::ControlTypeProperty, $ctrl::Button)
foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
    if ($b.Current.Name -eq 'Luma Studio') {
        $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        Start-Sleep -Milliseconds 1500
        break
    }
}

$scond = New-Object System.Windows.Automation.PropertyCondition($auto::IsScrollPatternAvailableProperty, $true)
$best = $null
foreach ($pane in $win.FindAll($scope::Descendants, $scond)) {
    $sp = $pane.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
    if (-not $sp.Current.VerticallyScrollable) { continue }
    $r = $pane.Current.BoundingRectangle
    if (-not $best -or $r.Height -gt $best.Height) { $best = [pscustomobject]@{ Pat = $sp; Height = $r.Height } }
}
if ($best) { $best.Pat.SetScrollPercent([System.Windows.Automation.ScrollPattern]::NoScroll, 68); Start-Sleep -Milliseconds 900 }
Write-Output 'READY'
''', timeout=300)
    return 'READY' in out


def scroll_to(percent):
    """Scroll the Studio page to a percentage, for the scroll search below."""
    out = ps(r'''
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$auto = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$win = $auto::RootElement.FindFirst($scope::Children,
    (New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')))
if (-not $win) { Write-Output 'NO_WINDOW'; exit 1 }
$scond = New-Object System.Windows.Automation.PropertyCondition($auto::IsScrollPatternAvailableProperty, $true)
$best = $null
foreach ($pane in $win.FindAll($scope::Descendants, $scond)) {
    $sp = $pane.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
    if (-not $sp.Current.VerticallyScrollable) { continue }
    $r = $pane.Current.BoundingRectangle
    if (-not $best -or $r.Height -gt $best.Height) { $best = [pscustomobject]@{ Pat = $sp; Height = $r.Height } }
}
if ($best) { $best.Pat.SetScrollPercent([System.Windows.Automation.ScrollPattern]::NoScroll, %d) }
Write-Output 'SCROLLED'
''' % int(percent), timeout=120)
    return 'SCROLLED' in out


def find_scroll_with_mark():
    """Scroll until the clock mark is visible and near the middle of the window.

    Returns True when a usable offset was found.
    """
    best = None
    for percent in (30, 40, 50, 60, 68, 75, 82, 90):
        scroll_to(percent)
        time.sleep(0.8)
        mark = find_mark()
        if mark is None:
            continue
        # Distance from the middle of the window; smaller is better.
        r = window_rect()
        if r is None:
            return True
        mid_x = (r[2] - r[0]) / 2.0
        mid_y = (r[3] - r[1]) / 2.0
        score = abs(mark['cx'] - mid_x) + abs(mark['cy'] - mid_y)
        if best is None or score < best[0]:
            best = (score, percent)
            if score < 220:
                break
    if best is None:
        return False
    scroll_to(best[1])
    time.sleep(0.9)
    print('  pad visible at scroll %d%%' % best[1])
    return find_mark() is not None


def window_rect():
    """The window rectangle as (left, top, right, bottom)."""
    out = ps(r'''
Add-Type @"
using System;using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
 public struct R { public int L,T,Rr,B; } }
"@
''' + PROCESS + r'''
$r = New-Object W+R
[void][W]::GetWindowRect($proc.MainWindowHandle, [ref]$r)
Write-Output ('RECT {0} {1} {2} {3}' -f $r.L, $r.T, $r.Rr, $r.B)
''')
    for line in out.splitlines():
        if line.startswith('RECT'):
            parts = line.split()
            return (int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
    return None


def main():
    print('  opening Luma Studio')
    if not open_studio():
        print('  FAIL could not open the Studio page')
        return 1

    # Park the window on a monitor the user is not working on, and put it back at the
    # end. This checker clicks the placement pad with the real pointer, so on the primary
    # monitor it takes over the screen and the user cannot type while it runs.
    #
    # resize_to_fit is required here, not optional: the window is 1580x950 and the
    # smallest test monitor is 1366x768, so an unresized window hangs off the bottom -
    # the pad sat at y=801 on a 768-tall screen and every click missed.
    sys.path.insert(0, str(ROOT / 'tools'))
    import test_screen
    hwnd = find_hwnd()
    monitor, was_at = test_screen.park(hwnd, margin=40, resize_to_fit=True)
    if monitor:
        print('  driving it on %s' % test_screen.describe(monitor))
    try:
        return _measure()
    finally:
        test_screen.restore(hwnd, was_at)


def find_hwnd():
    """The app's main window handle, or None."""
    out = ps(PROCESS + r'''
Write-Output ('HWND ' + $proc.MainWindowHandle)
''')
    for line in out.splitlines():
        if line.startswith('HWND'):
            value = int(line.split()[1])
            return value or None
    return None


def _measure():
    origin = window_origin()
    if origin is None:
        print('  FAIL could not read the window rectangle')
        return 1
    ox, oy = origin

    # Calibrate on the mark. The pad is 126x126 and the mark sits at the centre of the cell
    # the config names, so the pad's origin is derivable from the mark alone - once we know
    # which cell the mark is in, which the config tells us.
    position = config_position()
    print('  recorded position: %s' % position)
    if position is None or '-' not in position:
        print('  FAIL the config does not name a position')
        return 1

    # Find a scroll offset where the pad is fully inside the window.
    #
    # The page is taller than the window, so the placement card has to be scrolled to.
    # A fixed percentage does not work: the window is resized to fit the test monitor,
    # and 68% put the pad below the bottom edge - the check then reported "no clock mark
    # found" about a pad that was simply off-screen. So search for the offset where the
    # mark is actually visible, and use the one that puts it nearest the middle.
    if not find_scroll_with_mark():
        print('  FAIL the placement pad is not visible at any scroll offset')
        return 1
    origin = window_origin()
    ox, oy = origin
    position = config_position()

    def pad_origin_from(mark, recorded):
        """The pad's top-left, derived from where the mark is and what it means."""
        rec_row, rec_col = recorded.split('-')
        return (mark['cx'] + ox - PAD * FRACTION[rec_col],
                mark['cy'] + oy - PAD * FRACTION[rec_row])

    mark = find_mark()
    if mark is None:
        print('  FAIL no clock mark found')
        return 1
    pad_x, pad_y = pad_origin_from(mark, position)
    print('  calibrated from the mark at (%.0f, %.0f)' % (mark['cx'], mark['cy']))
    print()

    failures = []
    results = []
    for position in POSITIONS:
        row, col = position.split('-')
        want_x, want_y = FRACTION[col], FRACTION[row]

        # Re-calibrate before every click.
        #
        # Clicking rebuilds the page (the timer moves, the card redraws), and if the scroll
        # position shifts by even a few pixels the pad moves with it - so a click computed
        # from the pad's old position lands outside the cell it aimed at. That is exactly
        # what happened to bottom-right: it recorded middle-center.
        #
        # The mark is always drawn at the centre of the cell that the config names, so the
        # pad's origin can be derived from it exactly, every time, with no accumulated drift.
        mark = find_mark()
        recorded = config_position()
        if mark is None or recorded is None:
            failures.append('%s: could not calibrate (mark=%s, recorded=%s)'
                            % (position, mark is not None, recorded))
            print('  %-14s could not calibrate' % position)
            continue
        if '-' not in recorded:
            failures.append('%s: the app recorded an unknown position %r' % (position, recorded))
            print('  %-14s unknown recorded position %r' % (position, recorded))
            continue
        rec_row, rec_col = recorded.split('-')
        pad_x = mark['cx'] + ox - PAD * FRACTION[rec_col]
        pad_y = mark['cy'] + oy - PAD * FRACTION[rec_row]

        click_out = click(pad_x + PAD * want_x, pad_y + PAD * want_y)
        time.sleep(1.2)

        # Proof the click landed on the cell it aimed at.
        recorded = config_position()
        if recorded != position:
            # The first click after the window is brought forward is sometimes swallowed
            # while Windows finishes activating it. A person would click again; so does this,
            # once, and only once - a pad that needs three clicks is broken, not warming up.
            time.sleep(0.6)
            click_out = click(pad_x + PAD * want_x, pad_y + PAD * want_y)
            time.sleep(1.2)
            recorded = config_position()

        if recorded != position:
            # Report what had the focus, so a click that never reached the app is not
            # mistaken for an app that ignored it.
            focus = ''
            for line in click_out.splitlines():
                if line.startswith('BEFORE') or line.startswith('AFTER'):
                    focus += line + '  '
            failures.append('%s: the app recorded %r, so the click missed the cell (%s)'
                            % (position, recorded, focus.strip() or 'no focus report'))
            print('  %-14s click recorded as %-14s <<< MISSED THE CELL  %s'
                  % (position, recorded, focus.strip()))
            continue

        mark = find_mark()
        if mark is None:
            failures.append('%s: no clock mark after clicking' % position)
            print('  %-14s no mark' % position)
            continue

        fx = (mark['cx'] + ox - pad_x) / PAD
        fy = (mark['cy'] + oy - pad_y) / PAD
        dx, dy = abs(fx - want_x), abs(fy - want_y)
        ok = dx < TOLERANCE and dy < TOLERANCE
        results.append((position, fx, fy, want_x, want_y, ok))
        print('  %-14s recorded %-14s mark at %.2f/%.2f, want %.2f/%.2f  %s'
              % (position, recorded, fx, fy, want_x, want_y, 'ok' if ok else '<<< WRONG'))
        if not ok:
            failures.append('%s put the mark at %.2f/%.2f, expected %.2f/%.2f'
                            % (position, fx, fy, want_x, want_y))

    print()

    # The mark has to move. Two positions producing the same coordinates means the pad
    # records clicks but does not draw them.
    if len(results) >= 2:
        moved = any(abs(a[1] - b[1]) > 0.20 or abs(a[2] - b[2]) > 0.20
                    for i, a in enumerate(results) for b in results[i + 1:])
        if moved:
            print('  ok    the mark moves when the position changes')
        else:
            failures.append('the mark did not move between positions')
            print('  FAIL  the mark did not move between positions')

    if failures:
        for f in failures:
            print('  FAIL %s' % f)
        return 1
    print('  PASS the pad records the click and draws the clock in that third')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
