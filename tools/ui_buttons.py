"""ui_buttons.py — list the controls a page exposes to UI Automation.

Used while building the Studio page: a control that is not exposed to UI Automation
cannot be read or operated by a screen reader, and cannot be driven by a checker
either. That is how the timer switch was found to be invisible to assistive
technology - it was a Border with a click handler, so it appeared in no list at all.

    python tools/ui_buttons.py                 # every button in the window
    python tools/ui_buttons.py --page "Luma Studio" --scroll 85 --visible
    python tools/ui_buttons.py --kind CheckBox

Output is UTF-8 decoded explicitly: PowerShell writes its output in the console
code page, and the page labels contain characters outside ASCII (the "·" between a
display name and "Primary"), which made a plain capture fail with a UnicodeDecodeError.
"""

import argparse
import subprocess
import sys

POWERSHELL = r'''
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$auto = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$ctrl = [System.Windows.Automation.ControlType]

$win = $auto::RootElement.FindFirst($scope::Children,
    (New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')))
if (-not $win) { Write-Output 'NO_WINDOW'; exit 1 }

if ('__PAGE__' -ne '') {
    $bcond = New-Object System.Windows.Automation.PropertyCondition($auto::ControlTypeProperty, $ctrl::Button)
    foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
        if ($b.Current.Name -eq '__PAGE__') {
            $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
            Start-Sleep -Milliseconds 1800
            break
        }
    }
}

if (__SCROLL__ -ge 0) {
    $scond = New-Object System.Windows.Automation.PropertyCondition($auto::IsScrollPatternAvailableProperty, $true)
    $best = $null
    foreach ($pane in $win.FindAll($scope::Descendants, $scond)) {
        $sp = $pane.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
        if (-not $sp.Current.VerticallyScrollable) { continue }
        $r = $pane.Current.BoundingRectangle
        if (-not $best -or $r.Height -gt $best.Height) { $best = [pscustomobject]@{ Pat = $sp; Height = $r.Height } }
    }
    if ($best) { $best.Pat.SetScrollPercent([System.Windows.Automation.ScrollPattern]::NoScroll, __SCROLL__); Start-Sleep -Milliseconds 900 }
}

$kind = '__KIND__'
$cond = if ($kind -eq 'Any') {
    New-Object System.Windows.Automation.PropertyCondition($auto::IsControlElementProperty, $true)
} else {
    New-Object System.Windows.Automation.PropertyCondition($auto::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::$kind)
}

$only = '__VISIBLE__' -eq 'True'
foreach ($e in $win.FindAll($scope::Descendants, $cond)) {
    if ($only -and $e.Current.IsOffscreen) { continue }
    $r = $e.Current.BoundingRectangle
    $state = ''
    try {
        $tp = $e.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
        $state = ' [' + $tp.Current.ToggleState + ']'
    } catch { }
    Write-Output ('ITEM|{0}|{1}|{2}|{3}|{4}|{5}' -f $e.Current.ControlType.ProgrammaticName,
                  $e.Current.Name, $r.X, $r.Y, $r.Width, $r.Height)
}
'''


def run(page='', scroll=-1, kind='Any', visible=False, timeout=200):
    script = (POWERSHELL
              .replace('__PAGE__', page)
              .replace('__SCROLL__', str(scroll))
              .replace('__KIND__', kind)
              .replace('__VISIBLE__', 'True' if visible else 'False'))
    out = subprocess.run(['powershell', '-NoProfile', '-Command', script],
                         capture_output=True, timeout=timeout)
    return out.stdout.decode('utf-8', 'replace'), out.stderr.decode('utf-8', 'replace')


def items(text):
    """Parse the ITEM lines.

    A control name can contain "|", so the fields are split from the right: the last
    four are always the rectangle, and the two before them are kind and name. Splitting
    from the left put the tail of a name into the coordinates and raised IndexError.
    """
    found = []
    for line in text.splitlines():
        if not line.startswith('ITEM|'):
            continue
        parts = line.split('|')
        if len(parts) < 6:
            continue
        try:
            rect = [int(v) for v in parts[-4:]]
        except ValueError:
            continue
        found.append({
            'kind': parts[1].replace('ControlType.', ''),
            'name': '|'.join(parts[2:-4]),
            'x': rect[0], 'y': rect[1], 'w': rect[2], 'h': rect[3],
        })
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', default='', help='open this page first (a button name)')
    ap.add_argument('--scroll', type=int, default=-1, help='scroll percent, 0-100')
    ap.add_argument('--kind', default='Any',
                    help='Button, CheckBox, Text, Slider, ComboBox, ... or Any')
    ap.add_argument('--visible', action='store_true', help='only what is on screen')
    args = ap.parse_args()

    text, err = run(args.page, args.scroll, args.kind, args.visible)
    if 'NO_WINDOW' in text:
        print('  the LumaWall window is not open')
        return 1

    rows = items(text)
    if not rows:
        print('  no %s controls found' % args.kind)
        if err.strip():
            print('  %s' % err.strip().splitlines()[-1])
        return 1

    for r in rows:
        state = ' %d,%d %dx%d' % (r['x'], r['y'], r['w'], r['h'])
        print('  %-11s %s%s' % (r['kind'], r['name'], state))
    print()
    print('  %d control(s)' % len(rows))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
