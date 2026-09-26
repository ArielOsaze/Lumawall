# check-wallpaper-motion.ps1 - is the wallpaper actually MOVING?
#
# Why this exists:
#
# "GPU VideoDecode is 0%" answers a narrower question than it appears to. A paused
# wallpaper and a broken wallpaper both decode nothing, and a screenshot cannot tell
# them apart either - a frozen frame looks exactly like a playing one in a still
# image.
#
# What separates them is change over time. This takes two screenshots a moment apart
# and measures how much of the screen differs. A playing video wallpaper changes
# across most of its area; a frozen one changes almost nowhere.
#
# It also reports the app's own pause decision, so the three cases can be told apart:
#
#   app says paused, nothing changes      -> the pause feature working
#   app says playing, nothing changes     -> the wallpaper is frozen: a real fault
#   app says playing, the screen changes  -> everything is fine
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/check-wallpaper-motion.ps1
#   powershell ... -File tools/check-wallpaper-motion.ps1 -GapMs 1500

param(
    [int]$GapMs = 1200,
    [string]$OutDir = 'build'
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Save-Shot {
    param([string]$Path)
    $bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bmp.Size)
    $g.Dispose()
    $dir = Split-Path $Path -Parent
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
}

$log = Join-Path $env:LOCALAPPDATA 'LumaWall\logs\lumawall.log'

Write-Host ''
Write-Host '  is the wallpaper moving?'
Write-Host '  ' + ('-' * 56)

# ── the app's own view ───────────────────────────────────────────────────────
$pausedList = ''
if (Test-Path $log) {
    $last = Get-Content $log -Tail 400 | Where-Object { $_ -match 'Playback updated' } | Select-Object -Last 1
    if ($last -match 'paused \[([^\]]*)\]') { $pausedList = $Matches[1].Trim() }
    Write-Host ''
    Write-Host ('  the app''s last decision: ' + ($last -replace '^\S+ \S+ \[\d+\] ', ''))
    if ($pausedList) { Write-Host ('  paused now: ' + $pausedList) } else { Write-Host '  paused now: (none)' }
}

# ── two screenshots ──────────────────────────────────────────────────────────
$a = Join-Path $OutDir '_motion_a.png'
$b = Join-Path $OutDir '_motion_b.png'
Save-Shot -Path $a
Start-Sleep -Milliseconds $GapMs
Save-Shot -Path $b

Add-Type -AssemblyName System.Drawing
$ia = [System.Drawing.Bitmap]::FromFile((Resolve-Path $a))
$ib = [System.Drawing.Bitmap]::FromFile((Resolve-Path $b))

$width = $ia.Width
$height = $ia.Height

# Sample a grid rather than every pixel: a 5206x1080 pair is 5.6 million pixels, and
# a 160x90 grid finds the difference just as reliably for a fraction of the work.
$cols = 160
$rows = 90
$stepX = [Math]::Max(1, [int]($width / $cols))
$stepY = [Math]::Max(1, [int]($height / $rows))

$changed = 0
$total = 0
$sumDelta = 0.0

for ($y = 0; $y -lt $height; $y += $stepY) {
    for ($x = 0; $x -lt $width; $x += $stepX) {
        $pa = $ia.GetPixel($x, $y)
        $pb = $ib.GetPixel($x, $y)
        $d = [Math]::Abs($pa.R - $pb.R) + [Math]::Abs($pa.G - $pb.G) + [Math]::Abs($pa.B - $pb.B)
        $sumDelta += $d
        # A threshold well above video noise and compression shimmer, well below a
        # moving frame.
        if ($d -gt 30) { $changed++ }
        $total++
    }
}

$ia.Dispose()
$ib.Dispose()
Remove-Item $a, $b -Force -ErrorAction SilentlyContinue

$pct = if ($total -gt 0) { 100.0 * $changed / $total } else { 0 }
$mean = if ($total -gt 0) { $sumDelta / $total } else { 0 }

Write-Host ''
Write-Host ('  sampled          ' + $total + ' points across ' + $width + 'x' + $height)
Write-Host ('  changed          ' + $changed + '  (' + ('{0:N1}' -f $pct) + '%)')
Write-Host ('  mean difference  ' + ('{0:N1}' -f $mean) + '  (sum of RGB deltas, 0-765)')
Write-Host ''

# How much of the screen a playing video wallpaper should change between two samples
# about a second apart. Measured on this machine: a running wallpaper changes 20-40%
# of the sampled points, while a paused one changes about 1-3% - and that small change
# is the taskbar clock, the mouse cursor and notification shimmer, not the wallpaper.
#
# The first version of this check used 2%, which the clock alone cleared, so a paused
# wallpaper was reported as running. A threshold has to sit between "the clock" and
# "a video", and 8% does.
$MOVING_THRESHOLD_PCT = 8.0

$moving = $pct -ge $MOVING_THRESHOLD_PCT

if ($moving) {
    Write-Host '  VERDICT: the screen is changing - the wallpaper is running.'
    Write-Host ''
    exit 0
}

if ($pct -gt 0.5) {
    Write-Host ('  note: ' + ('{0:N1}' -f $pct) + '% changed, which is the clock and the')
    Write-Host '        cursor rather than a video frame. Not counted as movement.'
    Write-Host ''
}

if ($pausedList) {
    Write-Host '  VERDICT: nothing is changing, and the app says these monitors are'
    Write-Host '           paused because a window covers them. That is the pause'
    Write-Host '           feature working, not a fault.'
    Write-Host ''
    # Not a failure: the app is behaving as designed for a covered screen.
    exit 2
}

Write-Host '  VERDICT: nothing is changing while the app believes a wallpaper is'
Write-Host '           playing. The wallpaper is frozen - a real fault.'
Write-Host ''
exit 1
