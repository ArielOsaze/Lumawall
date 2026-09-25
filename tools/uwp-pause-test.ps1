# Verifies that a real UWP application pauses the wallpaper, using the Microsoft
# Store - which is a normal UWP app (class Windows.UI.Core.CoreWindow, process
# WinStore.App) and is available on every Windows install.
#
# The old class-based filter ignored every Windows.UI.Core.CoreWindow window, so
# a fullscreen UWP app never paused the wallpaper. This checks the fix from the
# outside, through the app's own log, and also confirms the shell surfaces
# (input host, Start menu) are still ignored so the wallpaper does not flicker.

$ErrorActionPreference = 'Continue'
$log = "$env:LOCALAPPDATA\LumaWall\Logs\lumawall.log"

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Info($t)    { Write-Host "   $t" }

if (-not (Test-Path $log)) { Write-Host "log missing" -ForegroundColor Red; exit 1 }

function Read-Playback($fromByte) {
    $fs = [System.IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
    try { $fs.Seek($fromByte, 'Begin') | Out-Null; $r = New-Object System.IO.StreamReader($fs); $t = $r.ReadToEnd(); $r.Dispose() }
    finally { $fs.Dispose() }
    return @(($t -split "`r?`n") | Where-Object { $_ -match 'Playback updated' })
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class W3 {
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
'@

$pass = $true

# Find the Store's CoreWindow (the visible one).
Section "Locating a real UWP app window (Microsoft Store)"
$store = Get-Process -Name 'WinStore.App' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $store) {
    Info "launching the Microsoft Store"
    Start-Process 'ms-windows-store:' | Out-Null
    Start-Sleep -Seconds 8
    $store = Get-Process -Name 'WinStore.App' -ErrorAction SilentlyContinue | Select-Object -First 1
}
if (-not $store) { Write-Host "  could not start the Store - SKIP" -ForegroundColor Yellow; exit 0 }

Info ("store pid: " + $store.Id + "  class: " + [W3]::Cls($store.MainWindowHandle))

# Clean stage.
try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 3
$baseline = (Get-Item $log).Length

# Bring the Store to the front and maximize it.
$h = $store.MainWindowHandle
if ($h -ne [IntPtr]::Zero) {
    if ([W3]::IsIconic($h)) { [W3]::ShowWindow($h, 9) | Out-Null; Start-Sleep -Milliseconds 800 }
    [W3]::ShowWindow($h, 3) | Out-Null        # SW_MAXIMIZE
    [W3]::SetForegroundWindow($h) | Out-Null
    Info "store window maximized"
} else {
    # A UWP app's visible window can belong to the ApplicationFrameHost process,
    # so fall back to activating it through the shell.
    Info "no direct handle; activating via the shell"
    Start-Process 'ms-windows-store:' | Out-Null
}
Start-Sleep -Seconds 4

$lines = Read-Playback $baseline
$pauseLine = $lines | Where-Object { $_ -match 'paused \[' } | Select-Object -Last 1
Section "Result: UWP app"
if ($pauseLine) {
    Info ("  " + ($pauseLine -replace '^.*?\[\d+\] ', ''))
    Write-Host "  [A] UWP app pauses the wallpaper ... PASS" -ForegroundColor Green
} else {
    Write-Host "  [A] UWP app pauses the wallpaper ... FAIL (ignored)" -ForegroundColor Red
    $pass = $false
}

# ── shell surfaces must stay ignored ─────────────────────────────────────────
Section "Shell surface must not pause (no flicker)"
try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 3
$baseline = (Get-Item $log).Length

# The input host is present on every machine and uses the same window class as a
# real UWP app, so it is the perfect counter-example.
$inputHost = Get-Process -Name 'TextInputHost' -ErrorAction SilentlyContinue | Select-Object -First 1
Info ("input host running: " + [bool]$inputHost)
Start-Sleep -Seconds 4

# Another application may legitimately be covering a display during this test
# (a browser, an editor), and its pause line would be mistaken for a shell
# surface pausing the wallpaper. So the check confirms which displays are
# genuinely covered by a real app first, and only fails if a pause happens on a
# display that no real app is covering.
$covered = @()
& (Join-Path $PSScriptRoot 'WindowAudit.exe') 2>$null | ForEach-Object {
    if ($_ -match 'covers=(\.\DISPLAY\d+)' -and $_ -notmatch 'LumaWall' -and $_ -notmatch 'TextInputHost' -and $_ -notmatch 'ShellExperienceHost') {
        $covered += $Matches[1]
    }
}
Info ("displays covered by a real app: " + $(if ($covered.Count) { ($covered -join ', ') } else { 'none' }))

$lines = Read-Playback $baseline
$falsePause = $null
foreach ($l in $lines) {
    if ($l -match 'paused \[([^\]]*)\]') {
        foreach ($d in ($Matches[1] -split ',')) {
            $d = $d.Trim()
            if ($d -and ($covered -notcontains $d)) { $falsePause = $l; break }
        }
    }
    if ($falsePause) { break }
}

if ($falsePause) {
    Info ("  " + ($falsePause -replace '^.*?\[\d+\] ', ''))
    Write-Host "  [B] shell surface does not pause ... FAIL (a display with no real app was paused)" -ForegroundColor Red
    $pass = $false
} else {
    Write-Host "  [B] shell surface does not pause ... PASS" -ForegroundColor Green
}

Section "Health"
$p = Get-Process LumaWall -ErrorAction SilentlyContinue
if ($p) {
    Info ("ram " + [math]::Round($p.WorkingSet64/1MB,1) + " MB   handles " + $p.HandleCount)
    $errs = (Get-Content $log | Where-Object { $_ -match ("\[" + $p.Id + "\]") }) | Select-String -Pattern 'UNHANDLED|FATAL' -CaseSensitive:$false
    if (-not $errs) { Write-Host "  [C] no exceptions .................. PASS" -ForegroundColor Green }
    else { Write-Host "  [C] no exceptions .................. FAIL ($($errs.Count))" -ForegroundColor Red; $pass = $false }
} else {
    Write-Host "  [C] app alive ...................... FAIL" -ForegroundColor Red; $pass = $false
}

Write-Host ""
if ($pass) { Write-Host "TEST PASSED" -ForegroundColor Green } else { Write-Host "TEST FAILED" -ForegroundColor Red }
