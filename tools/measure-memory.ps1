# measure-memory.ps1 - measures what the memory work actually saves.
#
# Why this exists:
#
# Every optimisation in this area is easy to claim and hard to see. "Working set
# trimming" sounds like it frees memory; it does not free commit, and a number that
# only reports the working set would let a trim look like a real release. And a
# WebView2 host's memory is not in the host process - it is in msedgewebview2.exe, so
# measuring the app's own process would report a small, meaningless number.
#
# So this measures three things at once, per phase:
#
#   working set  - what Task Manager's Processes tab shows, and what competes for
#                  physical RAM. This is the number a trim lowers.
#   commit       - what Task Manager's Details tab shows as "Commit size", and what
#                  actually has to fit in RAM plus pagefile. A trim does NOT lower
#                  this. Reporting both is the whole point.
#   processes    - how many browser processes exist. A change here means the
#                  process-level flags did something.
#
# Phases measured, in order:
#
#   playing      baseline with the wallpaper animating
#   paused       with a fullscreen window covering it - the state the trim targets
#   after-trim   re-sampled a few seconds into the paused state, so the trim and the
#                browser's own purge have both had time to run
#   resumed      after the fullscreen window closes, to confirm the memory comes back
#                and the wallpaper still plays
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/measure-memory.ps1
#   powershell ... -File tools/measure-memory.ps1 -Seconds 6 -SkipCover

param(
    [int]$Seconds = 5,
    [switch]$SkipCover
)

$ErrorActionPreference = 'Stop'

function Get-LumaWallProcesses {
    # Both kinds: the host itself, and the WebView2 group it spawned. Matching the
    # browser processes by command line is the only reliable way - several other
    # WebView2 apps can be running at the same time and counting theirs would inflate
    # every number below.
    $all = @()
    $all += Get-CimInstance Win32_Process -Filter "Name='LumaWall.exe'" -ErrorAction SilentlyContinue
    $all += Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*LumaWall*' }
    return $all
}

function Measure-Phase {
    param([string]$Label, [int]$Seconds)

    $samples = @()
    $end = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $end) {
        $procs = Get-LumaWallProcesses
        $workingSet = 0
        $commit = 0
        $count = 0
        foreach ($p in $procs) {
            try {
                $proc = Get-Process -Id $p.ProcessId -ErrorAction Stop
                $workingSet += $proc.WorkingSet64
                # PrivateMemorySize64 is the "Commit size" column in Task Manager's
                # Details tab. It is the number a working-set trim does not change.
                $commit += $proc.PrivateMemorySize64
                $count++
            } catch { }
        }
        if ($count -gt 0) {
            $samples += [pscustomobject]@{
                WorkingSet = $workingSet
                Commit     = $commit
                Processes  = $count
            }
        }
        Start-Sleep -Milliseconds 500
    }

    if ($samples.Count -eq 0) {
        return [pscustomobject]@{
            Label      = $Label
            WorkingSet = 0
            Commit     = 0
            Processes  = 0
            Samples    = 0
        }
    }

    # The mean, not the last sample: the browser's own housekeeping makes any single
    # reading jumpy, and a trim is a step change that a mean still shows clearly.
    $ws = ($samples | Measure-Object -Property WorkingSet -Average).Average
    $cm = ($samples | Measure-Object -Property Commit -Average).Average
    $pc = ($samples | Measure-Object -Property Processes -Average).Average

    return [pscustomobject]@{
        Label      = $Label
        WorkingSet = $ws
        Commit     = $cm
        Processes  = [int][Math]::Round($pc)
        Samples    = $samples.Count
    }
}

function Format-MB {
    param([double]$Bytes)
    return ('{0,8:N0} MB' -f ($Bytes / 1MB))
}

Write-Host ''
Write-Host '  LumaWall memory measurement'
Write-Host '  ----------------------------'

$running = Get-LumaWallProcesses
if (-not $running -or $running.Count -eq 0) {
    Write-Host ''
    Write-Host '  LumaWall is not running, so there is nothing to measure.'
    Write-Host '  Start it, apply a video wallpaper, then run this again.'
    Write-Host ''
    exit 1
}

Write-Host ('  found {0} process(es)' -f $running.Count)
Write-Host ''

$results = @()

# -- 1. playing ---------------------------------------------------------------
Write-Host ('  measuring playing for {0}s ...' -f $Seconds)
$results += Measure-Phase -Label 'playing' -Seconds $Seconds

# -- 2. paused behind a fullscreen window -------------------------------------
if (-not $SkipCover) {
    $cover = Join-Path $PSScriptRoot '..\FullscreenCover.exe'
    if (Test-Path $cover) {
        Write-Host '  covering the desktop with a fullscreen window ...'
        $coverProc = Start-Process -FilePath $cover -PassThru
        # The app reacts to the fullscreen window through its foreground hook, and the
        # trim then runs on a worker plus the browser's own purge. Three seconds is
        # enough for both to land; measuring immediately would catch the state before
        # the work happened and report that nothing changed.
        Start-Sleep -Seconds 3

        Write-Host ('  measuring paused for {0}s ...' -f $Seconds)
        $results += Measure-Phase -Label 'paused (after trim)' -Seconds $Seconds

        Write-Host '  closing the cover ...'
        try { $coverProc | Stop-Process -Force -ErrorAction SilentlyContinue } catch { }
        Start-Sleep -Seconds 3

        Write-Host ('  measuring resumed for {0}s ...' -f $Seconds)
        $results += Measure-Phase -Label 'resumed' -Seconds $Seconds
    } else {
        Write-Host '  FullscreenCover.exe not found; skipping the paused phases'
    }
}

# -- report -------------------------------------------------------------------
Write-Host ''
Write-Host '  phase                 working set      commit   processes'
Write-Host '  --------------------  ------------  ----------  ----------'
foreach ($r in $results) {
    Write-Host ('  {0,-20}  {1}  {2}  {3,10}' -f $r.Label, (Format-MB $r.WorkingSet), (Format-MB $r.Commit), $r.Processes)
}

Write-Host ''
$playing = $results | Where-Object { $_.Label -eq 'playing' }
$paused = $results | Where-Object { $_.Label -like 'paused*' }
if ($playing -and $paused -and $playing.WorkingSet -gt 0) {
    $wsDrop = $playing.WorkingSet - $paused.WorkingSet
    $cmDrop = $playing.Commit - $paused.Commit
    $wsPct = 100 * $wsDrop / $playing.WorkingSet
    Write-Host ('  working set released : {0} ({1:N0}%)' -f (Format-MB $wsDrop), $wsPct)
    if ($cmDrop -gt 0) {
        Write-Host ('  commit released      : {0}   <- this is the real release' -f (Format-MB $cmDrop))
    } else {
        Write-Host '  commit released      : none'
        Write-Host '    Expected. A working-set trim moves resident pages out without'
        Write-Host '    releasing commit, so the working-set drop above is what the trim'
        Write-Host '    buys: less physical RAM held, same reservation. Report both.'
    }
}
Write-Host ''
