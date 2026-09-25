# Measures the app's true pause/resume latency, free of measurement artefacts.
#
# Two earlier attempts gave wrong numbers and the reasons matter:
#
#   1. The clock started when the cover process EXITED, but its window is
#      destroyed earlier, inside form.Close(). Process teardown added 100-300 ms
#      that was wrongly charged to the app.
#
#   2. A screen-diff test measured the video's CONTENT, not the app's latency.
#      A video resumes from the frame it paused on, so in a calm scene the pixels
#      barely change for seconds even though playback restarted instantly.
#      Instrumentation inside the page proved this: it reported a fresh frame
#      0-23 ms after play(), while the screen test claimed 5000 ms.
#
# This test uses the probe's own timestamps (it writes them to a file, because a
# winexe has no console) and compares them with the app's log timestamps.

$ErrorActionPreference = 'Continue'

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Info($t)    { Write-Host "   $t" }

$log = "$env:LOCALAPPDATA\LumaWall\Logs\lumawall.log"
$cover = Join-Path $PSScriptRoot 'FullscreenCover.exe'
$stamps = Join-Path $env:TEMP 'lw-latency-stamps.txt'
Add-Type -AssemblyName System.Windows.Forms

# Pick a display that no application window is currently covering, so the
# resume is observable. Any display that is already covered stays covered when
# the probe closes, and the app rightly does not resume it.
function Get-FreeScreen {
    $covered = @()
    $audit = Join-Path $PSScriptRoot 'WindowAudit.exe'
    if (Test-Path $audit) {
        & $audit 2>$null | ForEach-Object {
            if ($_ -match 'covers=(\.\DISPLAY\d+)') { $covered += $Matches[1] }
        }
    }
    $candidates = [System.Windows.Forms.Screen]::AllScreens | Sort-Object { $_.Primary } -Descending
    foreach ($s in $candidates) {
        if ($covered -notcontains $s.DeviceName) { return $s }
    }
    return $null
}

$screen = Get-FreeScreen
if (-not $screen) {
    Write-Host "Every display is covered by an application - cannot measure." -ForegroundColor Yellow
    Write-Host "Minimize your windows and run again." -ForegroundColor Yellow
    exit 1
}
Write-Host ("Using display " + $screen.DeviceName + " at " + $screen.Bounds.ToString())
$b = $screen.Bounds

function Read-LogTail {
    $fs = [System.IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
    try { $r = New-Object System.IO.StreamReader($fs); $t = $r.ReadToEnd(); $r.Dispose() }
    finally { $fs.Dispose() }
    return $t
}

# Newest log timestamp matching a pattern, at or after $notBefore.
function Newest-EventTime($text, $pattern, $notBefore) {
    $best = $null
    foreach ($line in ($text -split "`r?`n")) {
        if ($line -match $pattern) {
            $m = [regex]::Match($line, '^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})')
            if ($m.Success) {
                $t = [datetime]::ParseExact($m.Groups[1].Value, 'yyyy-MM-dd HH:mm:ss.fff', $null)
                if ($t -ge $notBefore) { if (-not $best -or $t -gt $best) { $best = $t } }
            }
        }
    }
    return $best
}

# Only a NON-EMPTY pause list counts: "paused []" is the resume line, and
# matching it made the earlier test report pauses that never happened.
# Match only lines that mention the display under test, so a pause on another
# monitor cannot be mistaken for this one.
$esc = [regex]::Escape($screen.DeviceName)
$PAUSE_RX  = 'paused \[[^\]]*' + $esc
$RESUME_RX = 'resumed \[[^\]]*' + $esc

Section "Baseline"
try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 5
$last = (Read-LogTail) -split "`r?`n" | Where-Object { $_ -match 'Playback updated' } | Select-Object -Last 1
Info ("state: " + ($last -replace '^.*?\] ', ''))
if ($last -match $PAUSE_RX) { Start-Sleep -Seconds 7 }

$results = @()

foreach ($i in 1..5) {
    Section "Run $i"
    if (Test-Path $stamps) { Remove-Item $stamps -Force }
    $before = Get-Date

    Start-Process -FilePath $cover -ArgumentList `
        $b.X, $b.Y, $b.Width, $b.Height, '4', $stamps -Wait

    Start-Sleep -Milliseconds 600
    $text = Read-LogTail

    $shown = $null; $closing = $null
    foreach ($l in (Get-Content $stamps -ErrorAction SilentlyContinue)) {
        if ($l -match '^shown\s+(.+)$')   { $shown   = [datetime]::ParseExact($Matches[1].Trim(), 'yyyy-MM-dd HH:mm:ss.fff', $null) }
        if ($l -match '^closing\s+(.+)$') { $closing = [datetime]::ParseExact($Matches[1].Trim(), 'yyyy-MM-dd HH:mm:ss.fff', $null) }
    }
    if (-not $shown -or -not $closing) { Info "no stamps - skipping"; continue }

    $pauseAt  = Newest-EventTime $text $PAUSE_RX  $shown.AddSeconds(-1)
    $resumeAt = Newest-EventTime $text $RESUME_RX $closing.AddSeconds(-1)

    $pauseMs  = if ($pauseAt)  { [math]::Round(($pauseAt  - $shown).TotalMilliseconds) }   else { $null }
    $resumeMs = if ($resumeAt) { [math]::Round(($resumeAt - $closing).TotalMilliseconds) } else { $null }

    if ($pauseMs  -ne $null) { Info ("window shown  -> paused  : $pauseMs ms") }  else { Info "window shown  -> paused  : NOT DETECTED" }
    if ($resumeMs -ne $null) { Info ("window closed -> resumed : $resumeMs ms") } else { Info "window closed -> resumed : NOT DETECTED" }

    $results += [pscustomobject]@{ pause = $pauseMs; resume = $resumeMs }
    Start-Sleep -Seconds 2
}

Section "RESULT"
$valid = @($results | Where-Object { $_.pause -ne $null -and $_.resume -ne $null })
if ($valid.Count -eq 0) { Write-Host "  no complete runs" -ForegroundColor Red; exit 1 }

$avgPause  = [math]::Round(($valid | Measure-Object pause  -Average).Average)
$avgResume = [math]::Round(($valid | Measure-Object resume -Average).Average)
$maxPause  = [math]::Round(($valid | Measure-Object pause  -Maximum).Maximum)
$maxResume = [math]::Round(($valid | Measure-Object resume -Maximum).Maximum)

Info ("pause  : avg $avgPause ms   worst $maxPause ms")
Info ("resume : avg $avgResume ms   worst $maxResume ms")
Write-Host ""

# The page reports its own work as 0-23 ms, so anything beyond that is hook and
# dispatch overhead. 150 ms is where a person stops noticing.
$pass = $true
if ($maxPause -lt 150)  { Write-Host "  [1] pause is immediate  ......... PASS" -ForegroundColor Green }
else { Write-Host "  [1] pause is immediate  ......... FAIL (worst $maxPause ms)" -ForegroundColor Red; $pass = $false }

if ($maxResume -lt 150) { Write-Host "  [2] resume is immediate ......... PASS" -ForegroundColor Green }
else { Write-Host "  [2] resume is immediate ......... FAIL (worst $maxResume ms)" -ForegroundColor Red; $pass = $false }

Write-Host ""
if ($pass) { Write-Host "NO PERCEPTIBLE DELAY IN EITHER DIRECTION" -ForegroundColor Green }
else       { Write-Host "DELAY PRESENT" -ForegroundColor Red }
