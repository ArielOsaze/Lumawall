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

# 1. Find the timer: a small visible window owned by LumaWall.
$luma = Get-Process LumaWall -ErrorAction SilentlyContinue
if (-not $luma) { Write-Output '  FAIL LumaWall is not running'; exit 1 }
$lumaPids = @($luma | ForEach-Object { $_.Id })
Write-Output ('  LumaWall pids: {0}' -f ($lumaPids -join ', '))

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
$app = $null
$h = [IntPtr]::Zero
foreach ($name in @('notepad', 'mspaint', 'calc')) {
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

if ($appIdx -lt 0) {
    Write-Output '  FAIL the covering window is not in the Z-order list'
    exit 1
}
if ($timerIdx2 -lt 0) {
    Write-Output '  FAIL the timer vanished from the Z-order list'
    exit 1
}

# Lower index = higher on screen. The application must be above the timer.
if ($appIdx -lt $timerIdx2) {
    Write-Output ('  PASS the application is above the timer ({0} < {1}); the timer cannot cover it' -f $appIdx, $timerIdx2)
    exit 0
}

Write-Output ('  FAIL the timer is above the application ({0} < {1}) - it would cover the window' -f $timerIdx2, $appIdx)
exit 1
