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


def config_position():
    """The position the app has recorded, or None if it cannot be read."""
    try:
        return json.loads(CONFIG.read_text(encoding='utf-8'))['Timer'].get('Position')
    except Exception:
        return None


def click(x, y):
    ps(r'''
Add-Type @"
using System;using System.Runtime.InteropServices;
public class N { [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint x,uint y,uint d,int e);
 public static void Click(int x,int y){ SetCursorPos(x,y); System.Threading.Thread.Sleep(120);
  mouse_event(2,0,0,0,0); System.Threading.Thread.Sleep(70); mouse_event(4,0,0,0,0); } }
"@
[N]::Click(%d, %d)
''' % (int(x), int(y)), timeout=60)


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
$p = Get-Process LumaWall | Select-Object -First 1
$r = New-Object W+R
[void][W]::GetWindowRect($p.MainWindowHandle, [ref]$r)
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
$proc = Get-Process LumaWall | Select-Object -First 1
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


def main():
    print('  opening Luma Studio')
    if not open_studio():
        print('  FAIL could not open the Studio page')
        return 1

    origin = window_origin()
    if origin is None:
        print('  FAIL could not read the window rectangle')
        return 1
    ox, oy = origin

    # Calibrate on the mark. The pad is 126x126 and the mark sits at the centre of its cell,
    # so with the position at middle-centre the pad's top-left is the mark's centre minus 63.
    position = config_position()
    print('  recorded position: %s' % position)
    if position != 'middle-center':
        # Put it there first, using the calibration we do have: none. So click the middle of
        # the pad, which we can find because the mark is inside it - the pad is the 126px
        # square around the mark, and the middle cell is the mark's own neighbourhood.
        mark = find_mark()
        if mark is None:
            print('  FAIL no clock mark to calibrate from')
            return 1
        mx, my = mark['cx'] + ox, mark['cy'] + oy
        # The mark is somewhere in the pad; clicking the pad's own centre is the middle cell
        # only if we know the pad. Try the mark's cell first: with any position the mark is at
        # the centre of a 42px cell, and the pad centre is the middle of the three cells.
        # Rather than guess, click the point 63px away in the direction that centres it.
        # The pad is 3 cells; the mark's cell centre is the mark itself. Move from the mark
        # to the middle cell by one cell (42px) at a time, in the direction of the middle.
        # We do not know the direction, so try the three horizontal options on the row the
        # mark is already in, then verify against the config.
        settled = False
        for dx in (0, -42, 42):
            click(mx + dx, my)
            time.sleep(1.2)
            if config_position() == 'middle-center':
                settled = True
                break
        if not settled:
            print('  FAIL could not bring the pad to middle-centre to calibrate')
            return 1
        position = 'middle-center'
        print('  moved to middle-centre for calibration')

    mark = find_mark()
    if mark is None:
        print('  FAIL no clock mark found')
        return 1
    pad_x = mark['cx'] + ox - PAD / 2.0
    pad_y = mark['cy'] + oy - PAD / 2.0
    print('  pad at screen (%.0f, %.0f), calibrated from the mark' % (pad_x, pad_y))
    print()

    failures = []
    results = []
    for position in POSITIONS:
        row, col = position.split('-')
        want_x, want_y = FRACTION[col], FRACTION[row]

        click(pad_x + PAD * want_x, pad_y + PAD * want_y)
        time.sleep(1.2)

        # Proof the click landed on the cell it aimed at.
        recorded = config_position()
        if recorded != position:
            failures.append('%s: the app recorded %r, so the click missed the cell'
                            % (position, recorded))
            print('  %-14s click recorded as %-14s <<< MISSED THE CELL' % (position, recorded))
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
