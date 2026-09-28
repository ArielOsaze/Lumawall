"""check-timer-display.py — the timer follows the display the user picks in the UI.

Place() used to read Screen.PrimaryScreen unconditionally, so on a multi-monitor desk
the clock could not be moved off the primary display at all: the wallpaper could be
chosen per display, the clock could not. This proves the setting works.

Driven through the UI, not through the config file. The app reads its config once at
startup (MainWindow's `config = store.Load()`), so writing the file from outside
changes nothing until the next launch - a check that wrote the file and then read the
window would be measuring the previous launch's settings and passing or failing for no
reason. Clicking the chip is also the path a person actually takes.

What is measured: the widget is a layered window owned by LumaWall, small, and its
centre falls inside one monitor. So "which display is the timer on" is read from the
window's own rectangle rather than from what the app says it did.

Pass conditions:
  · clicking a display chip moves the widget to that display;
  · it stays there across repaints (the widget re-places itself every tick, so a
    position that is right once and wrong a second later is a real defect);
  · clicking the primary display's chip brings it back.

Run:  python tools/check-timer-display.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_screen

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(os.path.expandvars(r'%LOCALAPPDATA%\LumaWall\config.json'))

POWERSHELL = r'''
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System;using System.Runtime.InteropServices;
public class T {
[DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out R r);
[DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindow(string cls, string win);
[DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindowEx(IntPtr parent, IntPtr after, string cls, string win);
public delegate bool EnumProc(IntPtr h, IntPtr p);
[StructLayout(LayoutKind.Sequential)] public struct R { public int L,T,Rr,B; }
}
"@
$auto = [System.Windows.Automation.AutomationElement]
$scope = [System.Windows.Automation.TreeScope]
$ctrl = [System.Windows.Automation.ControlType]

$target = (Get-Process LumaWall -ErrorAction SilentlyContinue |
           Where-Object { $_.MainWindowHandle -ne 0 } |
           Sort-Object StartTime | Select-Object -First 1)
if (-not $target) { Write-Output 'NO_PROCESS'; exit 1 }
$pid_ = [uint32]$target.Id

$win = $auto::RootElement.FindFirst($scope::Children,
    (New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')))
if (-not $win) { Write-Output 'NO_WINDOW'; exit 1 }

if ('__ACTION__' -eq 'click') {
    [void][T]::ShowWindow($target.MainWindowHandle, 9)
    [void][T]::SetForegroundWindow($target.MainWindowHandle)
    Start-Sleep -Milliseconds 600

    $bcond = New-Object System.Windows.Automation.PropertyCondition($auto::ControlTypeProperty, $ctrl::Button)
    foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
        if ($b.Current.Name -eq 'Luma Studio') {
            $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
            Start-Sleep -Milliseconds 1800
            break
        }
    }

    # Scroll until the display chips are on screen. The card sits low on a long page,
    # and a control that is off-screen cannot be invoked by name reliably.
    $scond = New-Object System.Windows.Automation.PropertyCondition($auto::IsScrollPatternAvailableProperty, $true)
    $best = $null
    foreach ($pane in $win.FindAll($scope::Descendants, $scond)) {
        $sp = $pane.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
        if (-not $sp.Current.VerticallyScrollable) { continue }
        $r = $pane.Current.BoundingRectangle
        if (-not $best -or $r.Height -gt $best.Height) { $best = [pscustomobject]@{ Pat = $sp; Height = $r.Height } }
    }
    if ($best) { $best.Pat.SetScrollPercent([System.Windows.Automation.ScrollPattern]::NoScroll, 85); Start-Sleep -Milliseconds 1000 }

    $wanted = '__WANT__'
    $clicked = $false
    foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
        $name = $b.Current.Name
        if ($name -eq $wanted -or $name.StartsWith($wanted + ' ')) {
            $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
            $clicked = $true
            Write-Output ('CLICKED ' + $name)
            break
        }
    }
    if (-not $clicked) {
        $seen = @()
        foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
            if ($b.Current.Name -match '^DISPLAY\d') { $seen += $b.Current.Name }
        }
        Write-Output ('NO_CHIP seen: ' + ($seen -join ' / '))
    }
    Start-Sleep -Milliseconds 1500
}

if ('__ACTION__' -eq 'timer') {
    [void][T]::ShowWindow($target.MainWindowHandle, 9)
    [void][T]::SetForegroundWindow($target.MainWindowHandle)
    Start-Sleep -Milliseconds 600

    $bcond = New-Object System.Windows.Automation.PropertyCondition($auto::ControlTypeProperty, $ctrl::Button)
    foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
        if ($b.Current.Name -eq 'Luma Studio') {
            $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
            Start-Sleep -Milliseconds 1800
            break
        }
    }

    # The switch is matched by its own label, in every language the app speaks.
    #
    # Toggling "the first switch that is off" is what an earlier version did, and it
    # turned on Tone mapping instead: the switches are found in tree order and the
    # timer's is not the first. The four names come from the timer.enable copy entry,
    # so a language the app gains later has to be added there, not here.
    $labels = @('Tampilkan timer', 'Show a timer', '显示计时器', 'タイマーを表示')
    $want = '__STATE__' -eq 'on'
    $ccond = New-Object System.Windows.Automation.PropertyCondition($auto::ControlTypeProperty, $ctrl::CheckBox)
    $done = $false
    foreach ($c in $win.FindAll($scope::Descendants, $ccond)) {
        if ($labels -notcontains $c.Current.Name) { continue }
        $tp = $c.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
        $isOn = ($tp.Current.ToggleState -eq [System.Windows.Automation.ToggleState]::On)
        if ($isOn -ne $want) {
            $tp.Toggle()
            Start-Sleep -Milliseconds 1500
        }
        $done = $true
        Write-Output ('TIMER ' + $c.Current.Name + ' -> ' + $tp.Current.ToggleState)
        break
    }
    if (-not $done) { Write-Output 'NO_TIMER_SWITCH' }
}

$script:hits = @()
$cb = [T+EnumProc]{
  param($h, $p)
  $owner = [uint32]0
  [void][T]::GetWindowThreadProcessId($h, [ref]$owner)
  if ($owner -eq $pid_ -and [T]::IsWindowVisible($h)) {
    $r = New-Object T+R
    [void][T]::GetWindowRect($h, [ref]$r)
    $w = $r.Rr - $r.L
    $hh = $r.B - $r.T
    # The widget: small, and not the main window.
    if ($w -gt 40 -and $w -lt 700 -and $hh -gt 30 -and $hh -lt 700) {
      $script:hits += ('WIDGET {0} {1} {2} {3}' -f $r.L, $r.T, $w, $hh)
    }
  }
  return $true
}
[void][T]::EnumWindows($cb, [IntPtr]::Zero)

# The results are written AFTER the enumeration, not from inside the callback.
#
# A Write-Output inside a delegate that .NET invoked never reaches the caller's output
# stream: the callback runs outside the pipeline, so its output is discarded silently.
# The enumeration looked like it found nothing while the widget was on screen the whole
# time - the same enumeration written as a script-scope array works. This is the trap
# that made this check report "the timer is on no monitor" about a timer that was there.
$script:hits | ForEach-Object { Write-Output $_ }

# The widget is parented to the desktop so that it cannot cover an application. On this
# build EnumWindows still returns it (the widget is a top-level window that is re-parented
# after creation), so the walk below is a fallback for builds where it is a true child.
$progman = [T]::FindWindow('Progman', $null)
if ($progman -ne [IntPtr]::Zero) {
  $script:deep = @()
  $child = [T]::FindWindowEx($progman, [IntPtr]::Zero, $null, $null)
  while ($child -ne [IntPtr]::Zero) {
    $owner2 = [uint32]0
    [void][T]::GetWindowThreadProcessId($child, [ref]$owner2)
    if ($owner2 -eq $pid_) {
      $r2 = New-Object T+R
      [void][T]::GetWindowRect($child, [ref]$r2)
      $script:deep += ('WIDGET {0} {1} {2} {3}' -f $r2.L, $r2.T, ($r2.Rr - $r2.L), ($r2.B - $r2.T))
    }
    $child = [T]::FindWindowEx($progman, $child, $null, $null)
  }
  $script:deep | ForEach-Object { Write-Output $_ }
}
Write-Output 'DONE'
'''


def drive(action='report', want='', state='', timeout=180):
    script = (POWERSHELL.replace('__ACTION__', action)
              .replace('__WANT__', want)
              .replace('__STATE__', state))
    out = subprocess.run(['powershell', '-NoProfile', '-Command', script],
                         capture_output=True, timeout=timeout)
    return out.stdout.decode('utf-8', 'replace')


def set_timer(on):
    """Switch the timer on or off through its own switch, matched by label."""
    return drive('timer', state='on' if on else 'off')


def widget_rect(text=None):
    """The widget's rectangle as (x, y, w, h), or None."""
    if text is None:
        text = drive('report')
    if 'NO_PROCESS' in text:
        return None
    found = []
    for line in text.splitlines():
        if line.startswith('WIDGET '):
            parts = line.split()
            found.append(tuple(int(v) for v in parts[1:5]))
    if not found:
        return None
    # The widget is the smallest window that is not obviously something else.
    return min(found, key=lambda r: r[2] * r[3])


def monitor_of(rect):
    """Which monitor holds the centre of a rectangle."""
    cx = rect[0] + rect[2] / 2.0
    cy = rect[1] + rect[3] / 2.0
    for m in test_screen.monitors():
        if m['x'] <= cx < m['x'] + m['width'] and m['y'] <= cy < m['y'] + m['height']:
            return m
    return None


def short_name(device):
    """\\\\.\\DISPLAY3 -> DISPLAY3, matching the chip label."""
    return device.split('\\')[-1]


def timer_enabled():
    """Whether the timer is switched on, read from the config the app writes."""
    try:
        data = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    except Exception:
        return None
    return data.get('Timer', {}).get('Enabled')


def main():
    if not CONFIG.exists():
        print('  the app has never run, so there is nothing to check')
        return 1

    screens = test_screen.monitors()
    if len(screens) < 2:
        print('  SKIP: one display only, so there is nowhere to move the timer to')
        return 2

    target = test_screen.choose(screens)
    primary = [m for m in screens if m['primary']][0]
    print('  moving the timer to %s' % test_screen.describe(target))

    # The chips only exist while the timer is switched on, so the timer is switched on
    # for the duration and put back afterwards. A check that leaves the user's timer on
    # after running has changed their settings, which is worse than not running.
    was_on = timer_enabled() is True
    if not was_on:
        print('  the timer is switched off; switching it on through the Studio page')
        out = set_timer(True)
        if 'NO_TIMER_SWITCH' in out:
            print('  FAIL the timer switch was not found on the Studio page')
            return 1
        for _ in range(10):
            if timer_enabled() is True:
                break
            time.sleep(1.0)
        if timer_enabled() is not True:
            print('  FAIL the timer did not switch on')
            return 1

    try:
        return _measure(target, primary)
    finally:
        if not was_on:
            set_timer(False)
            print('  the timer was switched back off')


def _measure(target, primary):
    failures = []
    target_short = short_name(target['device'])
    primary_short = short_name(primary['device'])

    # 1. Move it to the chosen display.
    text = drive('click', target_short)
    if 'NO_CHIP' in text:
        seen = text.split('NO_CHIP seen:')[-1].strip()
        print('  FAIL no chip for %s was found (saw: %s)' % (target_short, seen))
        return 1
    print('  clicked the %s chip' % target_short)

    found = None
    for _ in range(15):
        time.sleep(1.0)
        rect = widget_rect()
        if rect is None:
            continue
        on = monitor_of(rect)
        if on and on['device'] == target['device']:
            found = (rect, on)
            break

    if not found:
        rect = widget_rect()
        on = monitor_of(rect) if rect else None
        print('  FAIL the timer is not on %s (it is on %s)'
              % (target['device'], test_screen.describe(on)))
        failures.append('the timer did not move to %s' % target['device'])
    else:
        rect, on = found
        print('  ok    the timer is on %s at %d,%d %dx%d'
              % (on['device'], rect[0], rect[1], rect[2], rect[3]))

        # It re-places itself on every tick, so a position that is right once and wrong
        # a second later is a real defect rather than a settling artefact.
        for _ in range(3):
            time.sleep(2.5)
            again = widget_rect()
            on2 = monitor_of(again) if again else None
            if not again or not on2 or on2['device'] != target['device']:
                failures.append('the timer left %s while running' % target['device'])
                print('  FAIL the timer left %s after a repaint' % target['device'])
                break
        else:
            print('  ok    it stays there across repaints')

    # 2. Put it back where the user had it.
    text = drive('click', primary_short)
    if 'NO_CHIP' in text:
        failures.append('no chip for the primary display was found')
        print('  FAIL no chip for %s was found' % primary_short)
    else:
        back = None
        for _ in range(15):
            time.sleep(1.0)
            rect = widget_rect()
            if rect is None:
                continue
            on = monitor_of(rect)
            if on and on['device'] == primary['device']:
                back = on
                break
        if back:
            print('  ok    clicking %s brings it back' % primary_short)
        else:
            rect = widget_rect()
            on = monitor_of(rect) if rect else None
            failures.append('the timer did not return to %s (it is on %s)'
                            % (primary['device'], test_screen.describe(on)))
            print('  FAIL the timer did not return to %s' % primary['device'])

    print()
    if failures:
        for f in failures:
            print('  FAIL %s' % f)
        return 1
    print('  PASS the timer follows the display picked in Luma Studio')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
