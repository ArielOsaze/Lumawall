# Production robustness test: restarting Explorer destroys the WorkerW window
# every wallpaper is parented to. A healthy app must notice and re-attach, or
# the desktop stays black until the user restarts LumaWall manually.
#
# This is the exact failure users hit most often in the wild (Explorer crashes,
# "Restart Explorer" from Task Manager, a shell update), so it must self-heal.

$ErrorActionPreference = 'Continue'
$log = "$env:LOCALAPPDATA\LumaWall\Logs\lumawall.log"

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Info($t)    { Write-Host "   $t" }

if (-not (Test-Path $log)) { Write-Host "log missing" -ForegroundColor Red; exit 1 }

function Read-New($fromByte) {
    $fs = [System.IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
    try {
        $fs.Seek($fromByte, 'Begin') | Out-Null
        $r = New-Object System.IO.StreamReader($fs)
        $t = $r.ReadToEnd(); $r.Dispose()
    } finally { $fs.Dispose() }
    return @(($t -split "`r?`n") | Where-Object { $_ })
}

Section "Baseline"
$baseline = (Get-Item $log).Length
$lw = Get-Process LumaWall -ErrorAction SilentlyContinue
if (-not $lw) { Write-Host "LumaWall is not running - start it first" -ForegroundColor Red; exit 1 }
Info ("LumaWall pid " + $lw.Id)
$ex = Get-Process explorer -ErrorAction SilentlyContinue | Select-Object -First 1
Info ("explorer pid " + $ex.Id)

# --- kill explorer (the wallpaper host dies with it) ------------------------
Section "Killing explorer.exe (simulates a shell crash)"
Stop-Process -Id $ex.Id -Force
Info "explorer killed; WorkerW is now destroyed"

# Windows normally respawns explorer on its own for a killed shell, but not
# always - start it explicitly so the test measures LumaWall, not the shell.
Start-Sleep -Seconds 3
if (-not (Get-Process explorer -ErrorAction SilentlyContinue)) {
    Info "explorer did not respawn - starting it"
    Start-Process explorer.exe
    Start-Sleep -Seconds 3
}
Info "explorer is back"

# --- does LumaWall notice and re-attach? ------------------------------------
Section "Waiting for LumaWall to self-heal (max 15s)"
$deadline = (Get-Date).AddSeconds(15)
$repaired = $null
while ((Get-Date) -lt $deadline) {
    $lines = Read-New $baseline
    # A destroyed window cannot be re-parented - it must be rebuilt. Accept
    # either message: the rebuild path (window destroyed with the desktop) or
    # the re-attach path (window alive, host changed).
    $repaired = $lines | Where-Object { $_ -match 'was destroyed with the desktop; rebuilding|lost its desktop host' } | Select-Object -Last 1
    if ($repaired) { break }
    Start-Sleep -Milliseconds 250
}

Section "RESULT"
$pass = $true
if ($repaired) {
    Write-Host "  [1] Detected the broken wallpaper ...... PASS" -ForegroundColor Green
    Info "  $repaired"
} else {
    Write-Host "  [1] Detected the broken wallpaper ...... FAIL (never noticed)" -ForegroundColor Red
    $pass = $false
}

# Rebuild is asynchronous (a new window has to load the page and report ready),
# so wait for the attach instead of checking once.
$attach = $null
$attachDeadline = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $attachDeadline) {
    $attach = (Read-New $baseline) | Where-Object { $_ -match 'Desktop host attached' } | Select-Object -Last 1
    if ($attach) { break }
    Start-Sleep -Milliseconds 250
}
if ($attach) {
    Write-Host "  [2] Re-attached to the new desktop host  PASS" -ForegroundColor Green
    Info "  $attach"
} else {
    Write-Host "  [2] Re-attached to the new desktop host  FAIL" -ForegroundColor Red
    $pass = $false
}

$stillAlive = Get-Process LumaWall -ErrorAction SilentlyContinue
if ($stillAlive) {
    Write-Host "  [3] App survived the shell crash ....... PASS" -ForegroundColor Green
} else {
    Write-Host "  [3] App survived the shell crash ....... FAIL (process died)" -ForegroundColor Red
    $pass = $false
}

Section "Log from this test"
foreach ($l in (Read-New $baseline)) { Info "  $l" }

Write-Host ""
if ($pass) { Write-Host "TEST PASSED - app self-heals after an Explorer crash" -ForegroundColor Green }
else       { Write-Host "TEST FAILED" -ForegroundColor Red }
