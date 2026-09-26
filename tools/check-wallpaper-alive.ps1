# check-wallpaper-alive.ps1 - are the wallpapers actually rendering right now?
#
# Why this exists:
#
# "The wallpaper did not apply" has one honest test, and it is not a screenshot: a
# screenshot shows whatever windows happen to be open, and the app deliberately pauses
# a monitor whose screen is covered. So a black screenshot is ambiguous - it can mean
# the wallpaper is broken, or that the app is working exactly as designed.
#
# What is not ambiguous is whether the videos are DECODING. A wallpaper that is meant
# to be playing shows up as GPU VideoDecode work owned by the WebView2 processes. If
# that number is zero while the app believes a wallpaper is playing, the wallpaper is
# broken. If it is non-zero, the wallpaper is rendering.
#
# So this reports both halves:
#
#   - what the app believes: which monitors are paused, from its own log
#   - what the GPU is doing: VideoDecode per WebView2 process
#
# and then states which of the two situations the machine is in.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/check-wallpaper-alive.ps1

$ErrorActionPreference = 'Stop'

$log = Join-Path $env:LOCALAPPDATA 'LumaWall\logs\lumawall.log'

Write-Host ''
Write-Host '  are the wallpapers rendering?'
Write-Host '  ' + ('-' * 56)

# ── what the app believes ────────────────────────────────────────────────────
Write-Host ''
Write-Host '  the app''s own view (last playback decision):'
if (Test-Path $log) {
    $lines = Get-Content $log -Tail 400 | Where-Object { $_ -match 'Playback updated' }
    $last = $lines | Select-Object -Last 1
    if ($last) {
        Write-Host ('    ' + $last.Trim())
        if ($last -match 'paused \[([^\]]*)\]') {
            $p = $Matches[1].Trim()
            if ($p) { Write-Host ('    paused now : ' + $p) } else { Write-Host '    paused now : (none)' }
        }
        if ($last -match 'resumed \[([^\]]*)\]') {
            $r = $Matches[1].Trim()
            if ($r) { Write-Host ('    resumed now: ' + $r) }
        }
    } else {
        Write-Host '    no playback decisions logged yet'
    }
} else {
    Write-Host ('    no log at ' + $log)
}

# ── what the GPU is doing ────────────────────────────────────────────────────
Write-Host ''
$pids = @(Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*LumaWall*' } |
    Select-Object -ExpandProperty ProcessId)

$renderers = @(Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*LumaWall*' -and $_.CommandLine -match '--type=renderer' })

Write-Host ('  WebView2 processes : ' + $pids.Count + '  (renderers: ' + $renderers.Count + ')')

if ($pids.Count -eq 0) {
    Write-Host ''
    Write-Host '  LumaWall has no WebView2 processes - nothing is rendering.'
    Write-Host ''
    exit 1
}

$decode = 0.0
$byPid = @{}
try {
    $samples = (Get-Counter '\GPU Engine(*)\Utilization Percentage' -ErrorAction SilentlyContinue).CounterSamples
    foreach ($s in $samples) {
        # The pid is captured into a variable before anything else matches. Writing
        # `$Matches[1]` twice in a row silently reports the wrong number: the second
        # -match overwrites $Matches, and a pattern with no capture group leaves it
        # empty, which cast to 0 and printed a phantom "pid 0 5.63%".
        if ($s.InstanceName -match 'pid_(\d+)_') {
            $ownerPid = [int]$Matches[1]
        } else {
            continue
        }
        if ($pids -notcontains $ownerPid) { continue }
        if ($s.InstanceName -match 'engtype_VideoDecode') {
            $value = [double]$s.CookedValue
            $decode += $value
            if ($value -gt 0.05) { $byPid[$ownerPid] = $value }
        }
    }
} catch { }

Write-Host ('  GPU VideoDecode    : {0:N2}%' -f $decode)
foreach ($onePid in ($byPid.Keys | Sort-Object)) {
    Write-Host ('    pid ' + $onePid + '  ' + ('{0:N2}%' -f $byPid[$onePid]))
}

Write-Host ''
if ($decode -ge 0.05) {
    Write-Host '  VERDICT: the wallpaper is decoding and rendering.'
    Write-Host '           A black screen right now means a window is covering it,'
    Write-Host '           which the app handles by pausing - see the log above.'
    Write-Host ''
    exit 0
}

# No decode. That is either a real fault or the app correctly pausing every monitor
# because every screen is covered - and those need opposite responses, so this
# distinguishes them instead of calling both a failure.
#
# The test is the app's own pause state: if the app says every monitor is paused and
# the GPU is doing nothing, the two agree and nothing is wrong. It only becomes a bug
# when the app believes a wallpaper is PLAYING and the decoder is still idle.
$appSaysAllPaused = $false
if (Test-Path $log) {
    $last = Get-Content $log -Tail 400 | Where-Object { $_ -match 'Playback updated' } | Select-Object -Last 1
    if ($last -match 'paused \[([^\]]*)\]') {
        $pausedList = $Matches[1].Trim()
        # Count the monitors the app knows about from its own resume/pause lines.
        $known = @()
        Get-Content $log -Tail 800 | Where-Object { $_ -match 'Wallpaper renderer ready' } |
            ForEach-Object { if ($_ -match '(\S+DISPLAY\d+)') { $known += $Matches[1] } }
        $known = $known | Sort-Object -Unique
        if ($known.Count -gt 0 -and $pausedList) {
            $pausedCount = ($pausedList -split ',').Count
            if ($pausedCount -ge $known.Count) { $appSaysAllPaused = $true }
        }
    }
}

if ($appSaysAllPaused) {
    Write-Host '  VERDICT: every monitor is paused, so no decode is expected.'
    Write-Host '           The app''s own log says all displays are paused, and the GPU'
    Write-Host '           agrees by doing nothing. This is the pause feature working,'
    Write-Host '           not a fault - uncover a screen and the decode returns.'
    Write-Host ''
    exit 0
}

Write-Host '  VERDICT: no video decode while the app believes a wallpaper is playing.'
if ($renderers.Count -le 1 -and $pids.Count -gt 2) {
    Write-Host '           One renderer for several monitors is the signature of'
    Write-Host '           --process-per-site, which collapsed the pages together and'
    Write-Host '           let a trim reach a renderer that was still playing.'
}
Write-Host ''
exit 1
