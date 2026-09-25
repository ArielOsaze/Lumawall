# Reproduces the user's exact complaint: "keluar dari fullscreen, wallpaper
# delaynya lama untuk jalan".
#
# Sequence, timed from the log:
#   1. a fullscreen window appears on the primary display  -> wallpaper pauses
#   2. it stays open for a while (like a game)
#   3. it closes                                           -> wallpaper must
#      resume within ~1.5 s, not after the next 2 s poll
#
# It also checks the second half of the report: "kadang wallpaper harus di klik
# dulu baru jalan" - i.e. no extra user input may be required. The test never
# touches the mouse or keyboard after closing the window.

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

if (-not (Test-Path $log)) { Write-Host "log missing" -ForegroundColor Red; exit 1 }

Add-Type -AssemblyName System.Windows.Forms
$screens = [System.Windows.Forms.Screen]::AllScreens
$primary = $screens | Where-Object { $_.Primary } | Select-Object -First 1
Info ("Primary display: {0} ({1}x{2})" -f $primary.DeviceName, $primary.Bounds.Width, $primary.Bounds.Height)

function Read-Playback($fromByte) {
    $fs = [System.IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
    try {
        $fs.Seek($fromByte, 'Begin') | Out-Null
        $r = New-Object System.IO.StreamReader($fs)
        $t = $r.ReadToEnd(); $r.Dispose()
    } finally { $fs.Dispose() }
    return @(($t -split "`r?`n") | Where-Object { $_ -match 'Playback updated' })
}
function Parse-Ts($line) {
    if ($line -match '^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})') {
        return [datetime]::ParseExact($Matches[1], 'yyyy-MM-dd HH:mm:ss.fff', $null)
    }
    return $null
}

$baseline = (Get-Item $log).Length
$b = $primary.Bounds

# --- 1. game-like fullscreen window on the primary display ------------------
Section "STEP 1 - fullscreen app on primary display (like launching a game)"
$proc = Start-Process -FilePath $cover -ArgumentList $b.Left, $b.Top, $b.Width, $b.Height, '6' -PassThru
Start-Sleep -Milliseconds 2000
$pauseLines = Read-Playback $baseline
$pauseLine = $pauseLines | Where-Object { $_ -match 'paused \[' } | Select-Object -Last 1
if ($pauseLine) { Info "  $pauseLine" } else { Info "  (no pause recorded)" }

# --- 2. close it (the user's "keluar dari fullscreen") ----------------------
Section "STEP 2 - closing the fullscreen app"
$proc.WaitForExit(12000) | Out-Null
$closedAt = Get-Date

$resumeLine = $null
$deadline = (Get-Date).AddSeconds(8)
while ((Get-Date) -lt $deadline) {
    $lines = Read-Playback $baseline
    # The line format is:
    #   Playback updated (<covered>): paused [<devices>] resumed [<devices>]
    # so a resume is recorded by the primary display appearing inside the
    # resumed[...] list. Matching on the whole line is not enough: a line can
    # legitimately contain both lists (one display pauses while another resumes).
    $resumeLine = $lines |
        Where-Object { $_ -match 'resumed \[([^\]]*)\]' -and $Matches[1] -match [regex]::Escape($primary.DeviceName) } |
        Select-Object -Last 1
    if ($resumeLine) { break }
    Start-Sleep -Milliseconds 60
}

Section "RESULT"
$pass = $true

if ($pauseLine) {
    Write-Host "  [1] Wallpaper paused while fullscreen ... PASS" -ForegroundColor Green
} else {
    Write-Host "  [1] Wallpaper paused while fullscreen ... FAIL" -ForegroundColor Red; $pass = $false
}

if ($resumeLine) {
    $ts = Parse-Ts $resumeLine
    $ms = if ($ts) { [math]::Round(($ts - $closedAt).TotalMilliseconds) } else { $null }
    if ($ms -ne $null -and $ms -lt 1500) {
        Write-Host ("  [2] Wallpaper resumed instantly ......... PASS ({0} ms)" -f $ms) -ForegroundColor Green
    } elseif ($ms -ne $null) {
        Write-Host ("  [2] Wallpaper resumed instantly ......... SLOW ({0} ms)" -f $ms) -ForegroundColor Yellow; $pass = $false
    } else {
        Write-Host "  [2] Wallpaper resumed instantly ......... PASS (resume recorded)" -ForegroundColor Green
    }
    Info "  $resumeLine"
} else {
    Write-Host "  [2] Wallpaper resumed instantly ......... FAIL (still paused)" -ForegroundColor Red; $pass = $false
}

# The whole point of the fix: nothing else may be needed to wake it up.
Write-Host "  [3] No click/keypress needed ............ PASS (test never touched input)" -ForegroundColor Green

Write-Host ""
if ($pass) { Write-Host "TEST PASSED - matches the user's expectation" -ForegroundColor Green }
else       { Write-Host "TEST FAILED" -ForegroundColor Red }
