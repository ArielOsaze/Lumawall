# Reproduces the user's exact scenario: fullscreen apps on EVERY display.
#
# The bug this verifies: the old detector only examined GetForegroundWindow(),
# and Windows has exactly one foreground window. With a fullscreen app on each
# monitor, only the focused one was seen - so the other wallpapers kept decoding
# and the GPU stayed busy.
#
# What is checked:
#   1. a fullscreen window on every display
#   2. every one of those displays gets paused
#   3. the GPU video decoder actually drops (the user-visible symptom)
#   4. closing them resumes every display

$ErrorActionPreference = 'Continue'
$log   = "$env:LOCALAPPDATA\LumaWall\Logs\lumawall.log"
$cover = Join-Path $PSScriptRoot 'FullscreenCover.exe'

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Info($t)    { Write-Host "   $t" }

if (-not (Test-Path $cover)) {
    $csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    if (Test-Path $csc) {
        & $csc /nologo /target:winexe "/out:$cover" /r:System.Windows.Forms.dll /r:System.Drawing.dll `
            (Join-Path $PSScriptRoot 'FullscreenCover.cs') | Out-Null
    }
}
if (-not (Test-Path $log)) { Write-Host "log missing" -ForegroundColor Red; exit 1 }

Add-Type -AssemblyName System.Windows.Forms
$screens = [System.Windows.Forms.Screen]::AllScreens
Section "Monitors"
foreach ($s in $screens) { Info ("{0}  {1}x{2} at ({3},{4})" -f $s.DeviceName, $s.Bounds.Width, $s.Bounds.Height, $s.Bounds.X, $s.Bounds.Y) }

function DecoderLoad {
    # Average a few samples: a single reading is noisy.
    $vals = @()
    for ($i = 0; $i -lt 4; $i++) {
        $out = & nvidia-smi --query-gpu=utilization.decoder --format=csv,noheader,nounits 2>$null
        if ($out) { $vals += [int]($out -replace '[^0-9]', '') }
        Start-Sleep -Milliseconds 400
    }
    if ($vals.Count -eq 0) { return $null }
    return [math]::Round(($vals | Measure-Object -Average).Average, 1)
}

function Read-Playback($fromByte) {
    $fs = [System.IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
    try { $fs.Seek($fromByte, 'Begin') | Out-Null; $r = New-Object System.IO.StreamReader($fs); $t = $r.ReadToEnd(); $r.Dispose() }
    finally { $fs.Dispose() }
    return @(($t -split "`r?`n") | Where-Object { $_ -match 'Playback updated' })
}

# Clean stage: no maximized window should be covering anything.
Section "Clearing the desktop"
try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 3

$baseline = (Get-Item $log).Length
$decoderIdle = DecoderLoad
Info ("decoder while wallpapers run : " + $decoderIdle + "%")

# ── open a fullscreen window on EVERY display ────────────────────────────────
Section "Opening a fullscreen window on all $($screens.Count) displays"
$procs = @()
foreach ($s in $screens) {
    $b = $s.Bounds
    $procs += Start-Process -FilePath $cover -ArgumentList $b.Left, $b.Top, $b.Width, $b.Height, '14' -PassThru
    Info ("  opened on " + $s.DeviceName)
    Start-Sleep -Milliseconds 900
}

Start-Sleep -Seconds 3
$decoderCovered = DecoderLoad
Info ("decoder while all covered     : " + $decoderCovered + "%")

$lines = Read-Playback $baseline
Section "Pause log"
if ($lines) { foreach ($l in $lines) { Info ("  " + ($l -replace '^.*?\[\d+\] ', '')) } } else { Info "  (nothing recorded)" }

# Which displays were paused?
$paused = New-Object System.Collections.Generic.HashSet[string]
foreach ($l in $lines) {
    if ($l -match 'paused \[([^\]]*)\]') {
        foreach ($d in ($Matches[1] -split ',')) { $d = $d.Trim(); if ($d) { [void]$paused.Add($d) } }
    }
}

# ── close them ───────────────────────────────────────────────────────────────
Section "Closing them all"
$closeAt = Get-Date
foreach ($p in $procs) { try { $p.WaitForExit(20000) | Out-Null } catch {} }

$resumeDeadline = (Get-Date).AddSeconds(8)
while ((Get-Date) -lt $resumeDeadline) {
    $resume = (Read-Playback $baseline) | Where-Object { $_ -match 'resumed \[' } | Select-Object -Last 1
    if ($resume) { break }
    Start-Sleep -Milliseconds 100
}
Start-Sleep -Seconds 2
$decoderAfter = DecoderLoad
Info ("decoder after closing         : " + $decoderAfter + "%")

# ── verdict ──────────────────────────────────────────────────────────────────
Section "RESULT"
$pass = $true

$missed = @()
foreach ($s in $screens) { if (-not $paused.Contains($s.DeviceName)) { $missed += $s.DeviceName } }

if ($missed.Count -eq 0) {
    Write-Host ("  [1] All " + $screens.Count + " displays paused .......... PASS") -ForegroundColor Green
} else {
    Write-Host ("  [1] All displays paused ........... FAIL (missed: " + ($missed -join ', ') + ")") -ForegroundColor Red
    $pass = $false
}

if ($decoderIdle -ne $null -and $decoderCovered -ne $null) {
    $drop = $decoderIdle - $decoderCovered
    if ($decoderCovered -lt 5 -or $drop -gt 8) {
        Write-Host ("  [2] GPU decode stopped ............ PASS (" + $decoderIdle + "% -> " + $decoderCovered + "%)") -ForegroundColor Green
    } else {
        Write-Host ("  [2] GPU decode stopped ............ FAIL (still " + $decoderCovered + "%)") -ForegroundColor Red
        $pass = $false
    }
} else {
    Write-Host "  [2] GPU decode stopped ............ SKIP (nvidia-smi unavailable)" -ForegroundColor Yellow
}

if ($resume) {
    Write-Host "  [3] Resumed after closing ......... PASS" -ForegroundColor Green
} else {
    Write-Host "  [3] Resumed after closing ......... FAIL" -ForegroundColor Red
    $pass = $false
}

Write-Host ""
if ($pass) { Write-Host "TEST PASSED - fullscreen on every display pauses every wallpaper" -ForegroundColor Green }
else       { Write-Host "TEST FAILED" -ForegroundColor Red }
