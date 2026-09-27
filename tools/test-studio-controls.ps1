# Exercise every control on the Luma Studio page and report what breaks.
#
# Why this exists: the page crashed on open once (SectionHeader with a null handler) and
# nothing caught it - the build passed, the log was clean at startup, and a smoke test
# that never opened the page saw nothing wrong. The only way to know a settings page
# works is to press its controls.
#
# Clicks go through tools/ui-press.ps1, which falls back to a real mouse click for the
# controls that are Borders rather than Buttons. Those are the display rows, the shape
# tiles, the position dots and the switches - exactly the controls a pattern-only test
# would skip.
#
# After each press the process is checked and the log is scanned for a new
# "UNHANDLED UI EXCEPTION": a WPF exception inside a click handler is caught by the
# dispatcher and logged, so the window survives a crash in its own UI code and only the
# log knows.

param(
    [string]$LogPath = "$env:LOCALAPPDATA\LumaWall\logs\lumawall.log"
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\ui-press.ps1"

Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes

$proc = Get-Process LumaWall -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $proc) { Write-Output '  FAIL  LumaWall is not running'; exit 1 }

# The log stamps every line with the process id, so it is how one session is told from
# the next in a file that is appended to forever.
$script:pidTag = $proc.Id

function Get-ExceptionCount {
    # Counted per process id, not per file. The log is appended to across runs, so a
    # file-wide count starts above zero and every run reports a failure that happened in
    # a previous session - which is how this check first reported a crash in a session
    # that had already exited.
    if (-not (Test-Path $LogPath)) { return 0 }
    return (Select-String -Path $LogPath -Pattern ('\[' + $script:pidTag + '\]') -ErrorAction SilentlyContinue |
        Where-Object { $_.Line -match 'UNHANDLED UI EXCEPTION' }).Count
}

$before = Get-ExceptionCount
Write-Output ('  pid {0}, exceptions before: {1}' -f $proc.Id, $before)
$root = [System.Windows.Automation.AutomationElement]::RootElement
$condition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $proc.Id)

$window = $null
for ($i = 0; $i -lt 40 -and -not $window; $i++) {
    $window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $condition)
    if (-not $window) { Start-Sleep -Milliseconds 500 }
}
if (-not $window) { Write-Output '  FAIL  no window'; exit 1 }

# The window has to be in front: a fallback click lands on whatever is at those screen
# coordinates, and if the app is behind another window the click goes to the wrong place
# and the test would report a pass for a control it never pressed.
[Mouse]::SetForegroundWindow($window.Current.NativeWindowHandle) | Out-Null
Start-Sleep -Milliseconds 600

$studio = Find-Element $window 'Luma Studio'
if (-not $studio) { Write-Output '  FAIL  the Luma Studio nav entry is missing'; exit 1 }
Invoke-Element $studio | Out-Null
Start-Sleep -Seconds 2
Write-Output '  opened Luma Studio'

# Everything on the page a user can press, by the text shown on it.
$targets = @(
    'DISPLAY1', 'DISPLAY2', 'DISPLAY3',
    'Natural', 'Vivid', 'Cinema', 'Warm', 'Night', 'Soft',
    'Grayscale', 'Sepia', 'Noir', 'Dream',
    'Stretch to the screen', 'Actual size, centred',
    'Left to right', 'Top to bottom',
    '0.25x', '0.5x', '1.5x', '2x',
    'Reset this display'
)

$pressed = 0
$skipped = @()

foreach ($name in $targets) {
    $element = Test-Flatten $window $name
    if (-not $element) { $skipped += $name; continue }

    try {
        Invoke-Element $element | Out-Null
        $pressed++
        Start-Sleep -Milliseconds 300
    } catch {
        Write-Output ('  FAIL  could not press "' + $name + '": ' + $_.Exception.Message)
        exit 1
    }

    if (-not (Get-Process -Id $proc.Id -ErrorAction SilentlyContinue)) {
        Write-Output ('  FAIL  the process exited after pressing "' + $name + '"')
        exit 1
    }

    $now = Get-ExceptionCount
    if ($now -gt $before) {
        Write-Output ('  FAIL  an exception was logged after pressing "' + $name + '"')
        Get-Content $LogPath -Tail 24 | ForEach-Object { Write-Output ('    ' + $_) }
        exit 1
    }
}

Write-Output ('  pressed {0} controls' -f $pressed)
if ($skipped.Count) {
    Write-Output ('  not found ({0}): {1}' -f $skipped.Count, ($skipped -join ', '))
}

# ── the timer, which only exists once it is switched on ──────────────────────
$timerOn = Test-Flatten $window 'Show a timer'
if ($timerOn) {
    Invoke-Element $timerOn | Out-Null
    Start-Sleep -Seconds 2

    if (Get-ExceptionCount -gt $before) {
        Write-Output '  FAIL  switching the timer on raised an exception'
        Get-Content $LogPath -Tail 24 | ForEach-Object { Write-Output ('    ' + $_) }
        exit 1
    }

    foreach ($name in @('Countdown', 'Clock', 'Stopwatch', 'Pill', 'Circle', 'Square', 'No background',
                        'Restart', 'Pause', 'Berkedip')) {
        $element = Test-Flatten $window $name
        if (-not $element) { continue }
        try {
            Invoke-Element $element | Out-Null
            $pressed++
            Start-Sleep -Milliseconds 300
        } catch { }

        if (Get-ExceptionCount -gt $before) {
            Write-Output ('  FAIL  an exception was logged after pressing the timer''s "' + $name + '"')
            Get-Content $LogPath -Tail 24 | ForEach-Object { Write-Output ('    ' + $_) }
            exit 1
        }
    }

    # The nine position dots have no text, so they are found by their container and
    # pressed by coordinate - which is the only way to reach them.
    $pad = Test-Flatten $window 'Placement'
    if ($pad) {
        $rect = $pad.Current.BoundingRectangle
        if ($rect.Width -gt 200) {
            $gridLeft = $rect.Left + 17
            $gridTop = $rect.Top + 26
            foreach ($offset in @(@(21, 15), @(63, 15), @(105, 15), @(63, 47), @(63, 79))) {
                [Mouse]::Click([int]($gridLeft + $offset[0]), [int]($gridTop + $offset[1]))
                Start-Sleep -Milliseconds 250
                $pressed++
                if (Get-ExceptionCount -gt $before) {
                    Write-Output '  FAIL  a position dot raised an exception'
                    Get-Content $LogPath -Tail 24 | ForEach-Object { Write-Output ('    ' + $_) }
                    exit 1
                }
            }
        }
    }

    Write-Output '  timer controls exercised'

    # Leave the timer as it was found: a test must not change the user's settings.
    $timerOn = Test-Flatten $window 'Show a timer'
    if ($timerOn) { Invoke-Element $timerOn | Out-Null; Start-Sleep -Milliseconds 600 }
}

$after = Get-ExceptionCount
Write-Output ('  pressed {0} controls in total; exceptions {1} -> {2}' -f $pressed, $before, $after)
if ($after -gt $before) { Write-Output '  FAIL'; exit 1 }
Write-Output '  OK'
exit 0
