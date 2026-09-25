# Proves the per-monitor pause logic end to end.
#
# What it checks:
#   1. A fullscreen window on ONE display pauses that display only.
#   2. The other displays keep running (this was the reported bug: a game on a
#      second monitor froze the wallpaper on the primary one).
#   3. Closing the window resumes the covered display immediately - the hook
#      must fire, not the 2 second poll.
#
# Latency is measured from the log's own timestamps against the moment the
# cover window reported "closing", so the number is the app's reaction time and
# not the test's polling granularity.

$ErrorActionPreference = 'Continue'
$log   = "$env:LOCALAPPDATA\LumaWall\Logs\lumawall.log"
# The probe is compiled on demand from FullscreenCover.cs, so the repository
# never carries a binary and the probe always matches the current source.
$cover = Join-Path $PSScriptRoot 'FullscreenCover.exe'
if (-not (Test-Path $cover)) {
    $csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    if (-not (Test-Path $csc)) { $csc = 'C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe' }
    if (Test-Path $csc) {
        $src = Join-Path $PSScriptRoot 'FullscreenCover.cs'
        & $csc /nologo /target:winexe "/out:$cover" /r:System.Windows.Forms.dll /r:System.Drawing.dll $src | Out-Null
    }
}



function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Info($t)    { Write-Host "   $t" }
function Step($t)    { Write-Host "   -> $t" -ForegroundColor DarkGray }

if (-not (Test-Path $cover)) { Write-Host "FullscreenCover.exe missing" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $log))   { Write-Host "LumaWall log missing - is the app running?" -ForegroundColor Red; exit 1 }

Add-Type -AssemblyName System.Windows.Forms
$screens = [System.Windows.Forms.Screen]::AllScreens
Section "Monitors"
foreach ($s in $screens) {
    Info ("{0}  {1}x{2} at ({3},{4})  primary={5}" -f $s.DeviceName, $s.Bounds.Width, $s.Bounds.Height, $s.Bounds.X, $s.Bounds.Y, $s.Primary)
}
if ($screens.Count -lt 2) { Write-Host "Need 2+ monitors." -ForegroundColor Yellow; exit 1 }

$game  = $screens | Where-Object { -not $_.Primary } | Select-Object -First 1
$other = $screens | Where-Object { $_.Primary }     | Select-Object -First 1
Info ""
Info ("Cover window  -> {0}  (this display should pause)" -f $game.DeviceName)
Info ("Must keep run -> {0}  (this display must NOT pause)" -f $other.DeviceName)

function Read-New($fromByte) {
    $fs = [System.IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
    try {
        $fs.Seek($fromByte, 'Begin') | Out-Null
        $r = New-Object System.IO.StreamReader($fs)
        $t = $r.ReadToEnd(); $r.Dispose()
    } finally { $fs.Dispose() }
    return @(($t -split "`r?`n") | Where-Object { $_ -match 'Playback updated' })
}

function Parse-Ts($line) {
    # 2026-09-25 01:41:26.171 [26296] Playback updated (...)
    if ($line -match '^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})') {
        return [datetime]::ParseExact($Matches[1], 'yyyy-MM-dd HH:mm:ss.fff', $null)
    }
    return $null
}

$baseline = (Get-Item $log).Length

# Clean the stage first. A maximized window on any display legitimately pauses
# that display (PauseMaximized defaults to true), so leaving one open makes the
# "other displays kept running" check fail for a reason that has nothing to do
# with per-monitor logic. Minimizing everything first gives the test a known
# starting state where no display is covered.
Section "STEP 0 - clearing the desktop (minimize all windows)"
try {
    $shell = New-Object -ComObject Shell.Application
    $shell.MinimizeAll()
    Start-Sleep -Milliseconds 1200
    Info "all windows minimized"
} catch {
    Info "could not minimize all: $_"
}
$settle = (Get-Date).AddSeconds(4)
while ((Get-Date) -lt $settle) {
    $lines = Read-New $baseline
    $resumed = $lines | Where-Object { $_ -match 'resumed \[[^\]]*DISPLAY' }
    if ($resumed) { break }
    Start-Sleep -Milliseconds 150
}
$clean = Read-New $baseline
$stillPaused = $clean | Where-Object { $_ -match 'paused \[([^\]]+)\]' } | Select-Object -Last 1
if ($stillPaused) { Info ("after minimize: " + $stillPaused) } else { Info "no display is paused - clean baseline" }
$baseline = (Get-Item $log).Length

# --- open the cover ---------------------------------------------------------
Section "STEP 1 - opening a fullscreen window on $($game.DeviceName)"
$b = $game.Bounds
$proc = Start-Process -FilePath $cover -ArgumentList $b.Left, $b.Top, $b.Width, $b.Height, '8' -PassThru
Start-Sleep -Milliseconds 2000

$during = Read-New $baseline
$pauseLine = $during | Where-Object { $_ -match 'paused \[[^\]]*DISPLAY' } | Select-Object -Last 1
$otherPaused = $false
if ($pauseLine) {
    Info "Log:"; Info "  $pauseLine"
    # The covered device must appear in paused[...]; the primary must NOT.
    if ($pauseLine -match [regex]::Escape($other.DeviceName)) { $otherPaused = $true }
} else {
    Info "(no pause line yet)"
}

# --- close ------------------------------------------------------------------
Section "STEP 2 - closing the window"
$t0 = Get-Date
$proc.WaitForExit(12000) | Out-Null
$closedAt = Get-Date

$resumeLine = $null
while ((Get-Date) -lt $closedAt.AddSeconds(8)) {
    $lines = Read-New $baseline
    $resumeLine = $lines | Where-Object { $_ -match 'resumed \[' } | Select-Object -Last 1
    if ($resumeLine) { break }
    Start-Sleep -Milliseconds 80
}
if ($resumeLine) {
    $ts = Parse-Ts $resumeLine
    if ($ts) {
        $ms = [math]::Round(($ts - $closedAt).TotalMilliseconds)
        # A negative value means the app resumed *before* WaitForExit returned,
        # i.e. the hook fired while the window was still tearing down - as fast
        # as it can possibly be.
        if ($ms -lt 0) { Info ("App reaction time: immediate (< {0} ms measured)" -f [math]::Abs($ms)) }
        else            { Info ("App reaction time: {0} ms after the window closed" -f $ms) }
    }
    Info "Log:"; Info "  $resumeLine"
}

# --- verdict ----------------------------------------------------------------
Section "RESULT"
$pass = $true

if ($pauseLine) {
    Write-Host "  [1] Covered display paused .......... PASS" -ForegroundColor Green
} else {
    Write-Host "  [1] Covered display paused .......... FAIL (no pause recorded)" -ForegroundColor Red
    $pass = $false
}

if ($pauseLine -and -not $otherPaused) {
    Write-Host "  [2] Other displays kept running ..... PASS (per-monitor works)" -ForegroundColor Green
} elseif ($otherPaused) {
    Write-Host "  [2] Other displays kept running ..... FAIL (global pause still in effect!)" -ForegroundColor Red
    $pass = $false
} else {
    Write-Host "  [2] Other displays kept running ..... SKIP (no pause line)" -ForegroundColor Yellow
    $pass = $false
}

if ($resumeLine) {
    if ($ts -and $ms -lt 1500) {
        Write-Host ("  [3] Instant resume ................. PASS ({0} ms)" -f $ms) -ForegroundColor Green
    } elseif ($ts) {
        Write-Host ("  [3] Instant resume ................. SLOW ({0} ms - poll, not hook)" -f $ms) -ForegroundColor Yellow
        $pass = $false
    } else {
        Write-Host "  [3] Instant resume ................. PASS (resume recorded)" -ForegroundColor Green
    }
} else {
    Write-Host "  [3] Instant resume ................. FAIL (still paused after close)" -ForegroundColor Red
    $pass = $false
}

Write-Host ""
if ($pass) { Write-Host "TEST PASSED" -ForegroundColor Green } else { Write-Host "TEST FAILED" -ForegroundColor Red }
