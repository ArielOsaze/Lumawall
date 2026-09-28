# Prove the desktop timer cannot cover an application.
#
# The requirement: "widget timer ya harus setara sama wallpaper placement nya gabole
# menimpa apps yg dibuka" - the timer must sit at the wallpaper's level and must not
# cover windows the user has open.
#
# How it is proved: EnumWindows reports top-level windows in Z-ORDER, top to bottom. So
# the position of a window in that list IS its height on screen: a lower index is higher
# up. This test opens a window, moves it over the timer, and asserts that the covering
# window comes BEFORE the timer in that list.
#
# Why not WindowFromPoint: the timer carries WS_EX_TRANSPARENT, which makes it
# click-through, and hit-testing therefore skips it entirely - it reported "Paint is on
# top" even when the timer really was topmost. The Z-order list cannot be fooled that way.
#
# Usage: powershell -File tools/check-timer-zorder.ps1

Add-Type -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool EnumWindows(EnumProc cb, IntPtr p);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern int GetClassName(IntPtr h, System.Text.StringBuilder s, int n);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern int GetWindowLong(IntPtr h, int index);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool GetWindowRect(IntPtr h, out RECT r);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool IsWindowVisible(IntPtr h);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool SetForegroundWindow(IntPtr h);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
[System.Runtime.InteropServices.DllImport("user32.dll")]
public static extern bool ShowWindow(IntPtr h, int cmd);
public delegate bool EnumProc(IntPtr h, IntPtr p);
[System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
public struct RECT { public int Left, Top, Right, Bottom; }
'@ -Name W -Namespace Z -ErrorAction SilentlyContinue

$WS_EX_TOPMOST = 0x00000008

function Get-Class([IntPtr]$h) {
    if ($h -eq [IntPtr]::Zero) { return '' }
    $sb = New-Object System.Text.StringBuilder 256
    [Z.W]::GetClassName($h, $sb, 256) | Out-Null
    return $sb.ToString()
}

function Get-Title([IntPtr]$h) {
    if ($h -eq [IntPtr]::Zero) { return '' }
    $sb = New-Object System.Text.StringBuilder 256
    [Z.W]::GetWindowText($h, $sb, 256) | Out-Null
    return $sb.ToString()
}

function Get-WinPid([IntPtr]$h) {
    if ($h -eq [IntPtr]::Zero) { return 0 }
    $p = 0
    [Z.W]::GetWindowThreadProcessId($h, [ref]$p) | Out-Null
    return $p
}

function Get-Rect([IntPtr]$h) {
    $r = New-Object Z.W+RECT
    [Z.W]::GetWindowRect($h, [ref]$r) | Out-Null
    return $r
}

# The Z-order list: visible top-level windows, top first.
function Get-ZOrder {
    $list = New-Object System.Collections.ArrayList
    $cb = [Z.W+EnumProc]{
        param([IntPtr]$h, [IntPtr]$p)
        if ([Z.W]::IsWindowVisible($h)) { [void]$list.Add($h) }
        return $true
    }
    [Z.W]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
    return $list
}

function Get-Index([System.Collections.ArrayList]$list, [IntPtr]$h) {
    for ($i = 0; $i -lt $list.Count; $i++) { if ($list[$i] -eq $h) { return $i } }
    return -1
}

# The monitor the tests should use: the smallest one that is not the primary.
#
# The covering window has to be placed over the widget, so the widget's monitor decides
# where this test happens. Left alone that is the primary screen, and the check opens
# Paint over whatever the user is doing. Moving the widget first puts the whole test on a
# screen nobody is looking at.
function Get-TestMonitor {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
    $screens = [System.Windows.Forms.Screen]::AllScreens
    if ($screens.Count -lt 2) { return $null }
    $others = @($screens | Where-Object { -not $_.Primary })
    if ($others.Count -eq 0) { return $null }
    return ($others | Sort-Object { $_.Bounds.Width * $_.Bounds.Height } | Select-Object -First 1)
}

# Click a display chip in Luma Studio, which is how the widget is moved.
#
# Returns $true when the click was made. The chip is matched by its label, which starts
# with the device name ("DISPLAY3"), so the same code works whatever the display is
# called and whatever language the app is in.
function Move-TimerTo([string]$deviceShort) {
    try {
        Add-Type -AssemblyName UIAutomationClient
        Add-Type -AssemblyName UIAutomationTypes
        $auto = [System.Windows.Automation.AutomationElement]
        $scope = [System.Windows.Automation.TreeScope]
        $ctrl = [System.Windows.Automation.ControlType]
        $win = $auto::RootElement.FindFirst($scope::Children,
            (New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')))
        if (-not $win) { return $false }

        $bcond = New-Object System.Windows.Automation.PropertyCondition(
            $auto::ControlTypeProperty, $ctrl::Button)
        foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
            if ($b.Current.Name -eq 'Luma Studio') {
                $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
                Start-Sleep -Milliseconds 1600
                break
            }
        }

        # The chips sit low on a long page, so scroll them into view first.
        $scond = New-Object System.Windows.Automation.PropertyCondition(
            $auto::IsScrollPatternAvailableProperty, $true)
        $best = $null
        foreach ($pane in $win.FindAll($scope::Descendants, $scond)) {
            $sp = $pane.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
            if (-not $sp.Current.VerticallyScrollable) { continue }
            $r = $pane.Current.BoundingRectangle
            if (-not $best -or $r.Height -gt $best.Height) {
                $best = [pscustomobject]@{ Pat = $sp; Height = $r.Height }
            }
        }
        if ($best) { $best.Pat.SetScrollPercent(
            [System.Windows.Automation.ScrollPattern]::NoScroll, 85); Start-Sleep -Milliseconds 900 }

        foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
            $name = $b.Current.Name
            if ($name -eq $deviceShort -or $name.StartsWith($deviceShort + ' ')) {
                $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
                Start-Sleep -Milliseconds 1500
                return $true
            }
        }
        return $false
    } catch {
        Write-Output ('  could not move the timer: ' + $_.Exception.Message)
        return $false
    }
}

# 1. Find the timer: a small visible window owned by LumaWall.
$luma = Get-Process LumaWall -ErrorAction SilentlyContinue
if (-not $luma) { Write-Output '  FAIL LumaWall is not running'; exit 1 }
$lumaPids = @($luma | ForEach-Object { $_.Id })
Write-Output ('  LumaWall pids: {0}' -f ($lumaPids -join ', '))

# Switch the timer on if it is off, through the app's own UI.
#
# Without this the checker fails with "no small LumaWall window found - is the timer
# switched on?" whenever the user has the timer off - which is a perfectly normal state and
# says nothing about whether the timer can cover an application. The check is about
# z-order, so it has to arrange the thing it measures.
#
# Writing config.json does NOT work: the app reads its settings at startup and rebuilds the
# timer only from the UI (StartDesktopTimer on load, timerRefresh from the Studio page).
# Editing the file leaves a running app that never notices. So the Studio page's timer
# switch is toggled instead, which is also what a person would do.
$configPath = Join-Path $env:LOCALAPPDATA 'LumaWall\config.json'
$script:restoreTimer = $null

function Get-TimerEnabled {
    try {
        $raw = [System.IO.File]::ReadAllText($configPath)
        return [bool](($raw | ConvertFrom-Json).Timer.Enabled)
    } catch { return $null }
}

# Every label the timer's switch can have, one per language the app speaks.
#
# The CJK entries are assembled from code points instead of being written into the file.
# PowerShell 5.1 reads a BOM-less .ps1 as ANSI, so a literal Chinese or Japanese string
# arrives as mojibake and the whole script fails to parse - measured, with the error
# "Unexpected token" pointing at the label. Building them here keeps the file pure ASCII
# and the labels exact.
#
# These are the timer.enable values in MainWindow's copy table; a language added there
# has to be added here too.
function Get-TimerSwitchLabels {
    $zh = -join (0x663E, 0x793A, 0x8BA1, 0x65F6, 0x5668 | ForEach-Object { [char]$_ })
    $ja = -join (0x30BF, 0x30A4, 0x30DE, 0x30FC, 0x3092, 0x8868, 0x793A | ForEach-Object { [char]$_ })
    return @('Tampilkan timer', 'Show a timer', $zh, $ja)
}

if ((Get-TimerEnabled) -eq $false) {
    Write-Output '  the timer is switched off; switching it on through the Studio page'
    try {
        Add-Type -AssemblyName UIAutomationClient
        Add-Type -AssemblyName UIAutomationTypes
        $auto = [System.Windows.Automation.AutomationElement]
        $scope = [System.Windows.Automation.TreeScope]
        $ctrl = [System.Windows.Automation.ControlType]
        $win = $auto::RootElement.FindFirst($scope::Children,
            (New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')))

        if ($win) {
            # Open Luma Studio, where the timer switch lives.
            $bcond = New-Object System.Windows.Automation.PropertyCondition(
                $auto::ControlTypeProperty, $ctrl::Button)
            foreach ($b in $win.FindAll($scope::Descendants, $bcond)) {
                if ($b.Current.Name -eq 'Luma Studio') {
                    $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
                    Start-Sleep -Milliseconds 1600
                    break
                }
            }

            # The switch is a CheckBox, matched by its own label.
            #
            # Toggling "the first switch that is off" is what this did, and it turned on
            # Tone mapping instead: the switches come back in tree order and the timer's
            # is not the first one.
            #
            # The Chinese and Japanese labels are built from code points rather than
            # written literally, and that is not decoration: PowerShell 5.1 reads a
            # BOM-less script as ANSI, so a CJK literal in the file arrives as mojibake
            # and the script fails to parse at all ("Unexpected token"). The four names
            # are the timer.enable copy entry, so a language added there has to be added
            # here too.
            $ccond = New-Object System.Windows.Automation.PropertyCondition(
                $auto::ControlTypeProperty, $ctrl::CheckBox)
            $labels = Get-TimerSwitchLabels
            $toggled = $false
            foreach ($c in $win.FindAll($scope::Descendants, $ccond)) {
                if ($labels -notcontains $c.Current.Name) { continue }
                try {
                    $tp = $c.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
                    if ($tp.Current.ToggleState -eq [System.Windows.Automation.ToggleState]::Off) {
                        $tp.Toggle()
                        $toggled = $true
                        Start-Sleep -Milliseconds 1200
                    }
                } catch { }
                break
            }
            if ($toggled) {
                Write-Output '  toggled a switch on the Studio page'
            } else {
                Write-Output '  no switch to toggle was found on the Studio page'
            }
        } else {
            Write-Output '  the LumaWall window was not found'
        }
    } catch {
        Write-Output ('  could not drive the UI: ' + $_.Exception.Message)
    }
    Start-Sleep -Seconds 2
}

# Move the widget onto a monitor the user is not working on, so the covering window is
# opened there too. Put back at the end, through the UI.
$testScreen = Get-TestMonitor
$movedForTest = $false
if ($testScreen) {
    # "\\\\.\\DISPLAY3" -> "DISPLAY3", which is what the chip label starts with.
    $short = $testScreen.DeviceName.Split('\')[-1]
    Write-Output ('  moving the timer to {0} so the test stays off the primary screen' -f $testScreen.DeviceName)
    if (Move-TimerTo $short) {
        $movedForTest = $true
        Start-Sleep -Seconds 2
    } else {
        Write-Output '  could not move the timer; the test will run on the primary screen'
    }
}

function Restore-TimerScreen {
    if (-not $movedForTest) { return }
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
    $primary = [System.Windows.Forms.Screen]::PrimaryScreen
    $short = $primary.DeviceName.Split('\')[-1]
    if (Move-TimerTo $short) {
        Write-Output '  the timer was moved back to the primary screen'
    }
}

$script:timer = [IntPtr]::Zero
$script:found = @()
$cb = [Z.W+EnumProc]{
    param([IntPtr]$h, [IntPtr]$p)
    if (-not [Z.W]::IsWindowVisible($h)) { return $true }
    if ($lumaPids -notcontains (Get-WinPid $h)) { return $true }
    $r = Get-Rect $h
    $w = $r.Right - $r.Left
    $ht = $r.Bottom - $r.Top
    $cls = Get-Class $h
    $ttl = Get-Title $h
    $short = if ($ttl.Length -gt 26) { $ttl.Substring(0, 26) } else { $ttl }
    $script:found += ('    {0,-32} {1,-28} {2}x{3} @{4},{5}' -f $cls, $short, $w, $ht, $r.Left, $r.Top)
    if ($w -gt 40 -and $w -lt 700 -and $ht -gt 30 -and $ht -lt 400) { $script:timer = $h }
    return $true
}
[Z.W]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null

Write-Output '  LumaWall windows:'
$script:found | ForEach-Object { Write-Output $_ }

if ($script:timer -eq [IntPtr]::Zero) {
    Write-Output '  FAIL no small LumaWall window found - is the timer switched on?'
    exit 1
}
$timer = $script:timer
$timerRect = Get-Rect $timer
$tw = $timerRect.Right - $timerRect.Left
$th = $timerRect.Bottom - $timerRect.Top
Write-Output ('  timer: {0} at {1},{2} {3}x{4}' -f (Get-Class $timer), $timerRect.Left, $timerRect.Top, $tw, $th)

$before = Get-ZOrder
$timerIdx = Get-Index $before $timer
Write-Output ('  timer Z-index: {0} of {1} (0 = topmost on screen)' -f $timerIdx, $before.Count)
if ($timerIdx -lt 0) { Write-Output '  FAIL the timer is not in the Z-order list'; exit 1 }

# THE DIRECT CHECK: WS_EX_TOPMOST is the flag that makes a window float above every
# other window, including the user's applications. If it is set, the widget WILL cover
# whatever is open, no matter what the z-order happens to look like at this instant.
# This is checked first because it cannot be fooled by a window that was just focused.
$timerEx = [Z.W]::GetWindowLong($timer, -20)
$isTopmost = ($timerEx -band $WS_EX_TOPMOST) -ne 0
Write-Output ('  timer ex-style: 0x{0:X}   WS_EX_TOPMOST: {1}' -f $timerEx, $isTopmost)
if ($isTopmost) {
    Write-Output '  FAIL the timer is a topmost window - it will float over the applications'
    exit 1
}
Write-Output '  the timer is not topmost, so applications can cover it'

# 2. Open a real window and move it to cover the timer exactly.
#
# Which application matters, and this list is not arbitrary:
#   notepad  is a packaged app on Windows 11 - "Start-Process notepad" fails outright with
#            "the system cannot find all the information required", so it can never work here;
#   calc     launches but as a packaged app it has no MainWindowHandle at the moment it is
#            started, so the handle is zero and the window cannot be positioned;
#   mspaint  is a desktop app, starts with a real handle, and is what this test uses.
#
# Trying only the first two would make this checker report "cannot test the z-order" on a
# healthy machine - a failure that says nothing about the app. That is what happened.
#
# The covering window is opened on the monitor the widget is on, which is the monitor the
# user is not working on when the timer has been moved there. Without that this test opens
# Paint in the middle of the primary screen and takes it over for as long as it runs.
$app = $null
$h = [IntPtr]::Zero
foreach ($name in @('mspaint', 'notepad', 'calc')) {
    try {
        $p = Start-Process $name -PassThru -ErrorAction Stop
        Start-Sleep -Seconds 3
        if ($p.MainWindowHandle -ne [IntPtr]::Zero) { $app = $p; $h = $p.MainWindowHandle; break }
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    } catch { }
}
if ($h -eq [IntPtr]::Zero) {
    Write-Output '  FAIL no application window could be opened; cannot test the z-order'
    exit 1
}

[Z.W]::ShowWindow($h, 9) | Out-Null      # SW_RESTORE
[Z.W]::SetWindowPos($h, [IntPtr]::Zero, $timerRect.Left - 40, $timerRect.Top - 60,
                    $tw + 80, $th + 120, 0x0040) | Out-Null
Start-Sleep -Milliseconds 700
[Z.W]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 1500

$appRect = Get-Rect $h
Write-Output ('  covering window: "{0}" at {1},{2} {3}x{4}' -f (Get-Title $h), $appRect.Left, $appRect.Top,
              ($appRect.Right - $appRect.Left), ($appRect.Bottom - $appRect.Top))

# 3. The covering window must actually overlap the timer, or the result means nothing.
$overlapX = [Math]::Min($timerRect.Right, $appRect.Right) - [Math]::Max($timerRect.Left, $appRect.Left)
$overlapY = [Math]::Min($timerRect.Bottom, $appRect.Bottom) - [Math]::Max($timerRect.Top, $appRect.Top)
if ($overlapX -lt 20 -or $overlapY -lt 20) {
    Write-Output ('  FAIL the covering window does not overlap the timer (overlap {0}x{1}) - the test would prove nothing' -f $overlapX, $overlapY)
    Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
Write-Output ('  overlap: {0}x{1} pixels - the test measures something real' -f $overlapX, $overlapY)

$after = Get-ZOrder
$timerIdx2 = Get-Index $after $timer
$appIdx = Get-Index $after $h
Write-Output ('  Z-index now: covering window {0}, timer {1}' -f $appIdx, $timerIdx2)

Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue

# Put the timer back the way it was found. Running a check must not change the app's
# configuration: a user who keeps the timer off would find it switched on after the suite.
#
# Restored through the UI for the same reason it was switched on that way, and because the
# app must be the one to write its config - a file written by PowerShell 5.1's
# "Set-Content -Encoding UTF8" carries a BOM, and the app's JSON reader rejects it.
function Restore-Timer {
    if ((Get-TimerEnabled) -ne $true) { return }
    try {
        Add-Type -AssemblyName UIAutomationClient
        Add-Type -AssemblyName UIAutomationTypes
        $auto = [System.Windows.Automation.AutomationElement]
        $scope = [System.Windows.Automation.TreeScope]
        $ctrl = [System.Windows.Automation.ControlType]
        $win = $auto::RootElement.FindFirst($scope::Children,
            (New-Object System.Windows.Automation.PropertyCondition($auto::NameProperty, 'LumaWall')))
        if (-not $win) { return }
        $ccond = New-Object System.Windows.Automation.PropertyCondition(
            $auto::ControlTypeProperty, $ctrl::CheckBox)
        # Matched by label, for the same reason the switch-on above is: toggling "the
        # first switch that is on" would switch off Tone mapping instead.
        $labels = Get-TimerSwitchLabels
        foreach ($c in $win.FindAll($scope::Descendants, $ccond)) {
            if ($labels -notcontains $c.Current.Name) { continue }
            try {
                $tp = $c.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
                if ($tp.Current.ToggleState -eq [System.Windows.Automation.ToggleState]::On) {
                    $tp.Toggle()
                    Start-Sleep -Milliseconds 1200
                    if ((Get-TimerEnabled) -eq $false) {
                        Write-Output '  the timer was switched back off'
                    } else {
                        Write-Output '  the timer setting could not be restored'
                    }
                }
            } catch { }
            return
        }
    } catch {
        Write-Output ('  could not restore the timer setting: ' + $_.Exception.Message)
    }
}

if ($appIdx -lt 0) {
    Write-Output '  FAIL the covering window is not in the Z-order list'
    Restore-TimerScreen
    Restore-Timer
    exit 1
}
if ($timerIdx2 -lt 0) {
    Write-Output '  FAIL the timer vanished from the Z-order list'
    Restore-TimerScreen
    Restore-Timer
    exit 1
}

# Lower index = higher on screen. The application must be above the timer.
if ($appIdx -lt $timerIdx2) {
    Write-Output ('  PASS the application is above the timer ({0} < {1}); the timer cannot cover it' -f $appIdx, $timerIdx2)
    Restore-TimerScreen
    Restore-Timer
    exit 0
}

Write-Output ('  FAIL the timer is above the application ({0} < {1}) - it would cover the window' -f $timerIdx2, $appIdx)
Restore-TimerScreen
Restore-Timer
exit 1
