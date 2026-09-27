# check-decode.ps1 - is the wallpaper video actually being decoded right now?
#
# Why this exists:
#
# "The wallpaper is static" has two completely different causes, and the fix for one is
# wrong for the other:
#
#   * the app has paused it (correct when a window covers the monitor), or
#   * the app believes it is playing, and the video is not advancing.
#
# The second case is the one that is invisible: the window holds a decoded frame, the
# page reports `paused=false`, and nothing is moving. The GPU's VideoDecode engine
# counter settles it - if the app's own WebView2 GPU process is not decoding, no amount
# of looking at the window will tell you why.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/check-decode.ps1
#   ... -Seconds 6      sample over a longer window (a paused video decodes nothing
#                       even if it decoded a moment ago)

param([int]$Seconds = 5)

$ErrorActionPreference = 'Continue'

Write-Host ''
Write-Host '  is the wallpaper video being decoded?'
Write-Host '   + --------------------------------------------------------'

$lumaPids = @(Get-Process LumaWall -ErrorAction SilentlyContinue | ForEach-Object { [int]$_.Id })
if ($lumaPids.Count -eq 0) {
    Write-Host ''
    Write-Host '  LumaWall is not running.'
    Write-Host ''
    exit 2
}

# The WebView2 processes are children of LumaWall, and the GPU process among them is the
# one that owns hardware decode. Walking the parent chain is what separates this app's
# decode from every other application's.
$owned = New-Object 'System.Collections.Generic.HashSet[int]'
foreach ($id in $lumaPids) { [void]$owned.Add($id) }

$children = @(Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" -ErrorAction SilentlyContinue)
$added = $true
while ($added) {
    $added = $false
    foreach ($c in $children) {
        if ($owned.Contains([int]$c.ParentProcessId) -and -not $owned.Contains([int]$c.ProcessId)) {
            [void]$owned.Add([int]$c.ProcessId)
            $added = $true
        }
    }
}

Write-Host ("  LumaWall process tree: {0} process(es)" -f $owned.Count)

# What the app itself believes, from its own log.
$logPath = Join-Path $env:LOCALAPPDATA 'LumaWall\logs\lumawall.log'
if (Test-Path $logPath) {
    $lastDecision = Get-Content $logPath -Tail 500 |
        Where-Object { $_ -match 'Playback updated' } |
        Select-Object -Last 1
    if ($lastDecision) {
        Write-Host ('  app decision: ' + ($lastDecision -replace '^\S+ \S+ \[\d+\] ', ''))
    }

    $recentPause = @(Get-Content $logPath -Tail 60 | Where-Object { $_ -match 'pause-ack' })
    $recentResume = @(Get-Content $logPath -Tail 60 | Where-Object { $_ -match 'resume-frame|resume-rejected' })
    Write-Host ("  recent pause-ack: {0}, recent resume-frame: {1}" -f $recentPause.Count, $recentResume.Count)
}

# Sample the decode counter over a window rather than once: a single reading can catch a
# paused video between frames.
Write-Host ''
Write-Host ("  sampling the GPU VideoDecode engine for {0}s ..." -f $Seconds)

$sawOurDecode = $false
$sawAnyDecode = $false
$bestOur = 0
$other = @{}

$deadline = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $deadline) {
    try {
        $engines = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction Stop |
            Where-Object { $_.Name -like '*VideoDecode*' -and $_.UtilizationPercentage -gt 0 }
        foreach ($e in $engines) {
            $owner = if ($e.Name -match 'pid_(\d+)_') { [int]$Matches[1] } else { 0 }
            if ($owned.Contains($owner)) {
                $sawOurDecode = $true
                if ($e.UtilizationPercentage -gt $bestOur) { $bestOur = $e.UtilizationPercentage }
            } else {
                $sawAnyDecode = $true
                $name = (Get-Process -Id $owner -ErrorAction SilentlyContinue).ProcessName
                $other["$owner $name"] = $e.UtilizationPercentage
            }
        }
    } catch { }
    Start-Sleep -Milliseconds 400
}

Write-Host ''
if ($sawOurDecode) {
    Write-Host ("  LumaWall is DECODING VIDEO (peak {0}% on a VideoDecode engine)." -f $bestOur)
    Write-Host '  The wallpaper is playing. If it looks static on screen, the fault is in'
    Write-Host '  presentation - the compositor or the window - not in playback.'
} else {
    Write-Host '  LumaWall is NOT decoding any video.'
    Write-Host '  Every wallpaper is either stopped or not playing its element, whatever'
    Write-Host '  the app believes. This is what a static wallpaper looks like from here.'
}

if ($other.Count -gt 0) {
    Write-Host ''
    Write-Host '  other applications decoding video (for context):'
    foreach ($key in $other.Keys) {
        Write-Host ("    {0}  {1}%" -f $key, $other[$key])
    }
}

Write-Host ''
if ($sawOurDecode) { exit 0 } else { exit 1 }
