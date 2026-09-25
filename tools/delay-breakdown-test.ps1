# Splits the resume delay into its two parts, because they have different fixes:
#
#   detection delay = when the cover closes -> when the app decides to resume
#                     (a hook/event problem, fixed in C#)
#   decode delay    = when the app decides to resume -> when pixels actually move
#                     (a video pipeline problem, fixed in JS)
#
# Measuring only the total, as the earlier test did, cannot tell which one is at
# fault.

$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class W5 {
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
}
'@

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Info($t)    { Write-Host "   $t" }

$log = "$env:LOCALAPPDATA\LumaWall\Logs\lumawall.log"
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$step = 40

function GrabFrame {
    $bmp = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($screen.X, $screen.Y, 0, 0, $bmp.Size)
    $g.Dispose()
    return $bmp
}
function FrameDiff($a, $b) {
    $changed = 0; $sampled = 0
    for ($y = 0; $y -lt $a.Height; $y += $step) {
        for ($x = 0; $x -lt $a.Width; $x += $step) {
            $ca = $a.GetPixel($x, $y); $cb = $b.GetPixel($x, $y)
            $sampled++
            if ([math]::Abs($ca.R-$cb.R) + [math]::Abs($ca.G-$cb.G) + [math]::Abs($ca.B-$cb.B) -gt 20) { $changed++ }
        }
    }
    if ($sampled -eq 0) { return 0 }
    return 100 * $changed / $sampled
}

# Hide desktop icons so they do not count as motion.
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public class Dz5 {
  [DllImport("user32.dll")] public static extern IntPtr FindWindow(string c, string t);
  [DllImport("user32.dll")] public static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string t);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
}
'@
$dv = [Dz5]::FindWindowEx([Dz5]::FindWindow('Progman', $null), [IntPtr]::Zero, 'SHELLDLL_DefView', $null)
$lv = [Dz5]::FindWindowEx($dv, [IntPtr]::Zero, 'SysListView32', $null)
if ($lv -ne [IntPtr]::Zero) { [Dz5]::ShowWindow($lv, 0) | Out-Null }

$cover = Join-Path $PSScriptRoot 'FullscreenCover.exe'

Section "Baseline"
try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 5
$a = GrabFrame; Start-Sleep -Milliseconds 700; $b = GrabFrame
$motion = FrameDiff $a $b; $a.Dispose(); $b.Dispose()
Info ("motion: " + [math]::Round($motion,1) + "%")
if ($motion -lt 0.5) { Write-Host "  wallpaper not animating - abort" -ForegroundColor Yellow; exit 1 }

# ── RESUME: full breakdown ───────────────────────────────────────────────────
Section "RESUME breakdown"
$before = (Get-Item $log).Length
$proc = Start-Process -FilePath $cover -ArgumentList $screen.X, $screen.Y, $screen.Width, $screen.Height, '8' -PassThru
Start-Sleep -Seconds 5   # let the pause settle
$proc.WaitForExit(20000) | Out-Null
$tClose = Get-Date

# 1) when does the app log the resume?
$logMs = $null; $logStamp = $null
$deadline = $tClose.AddSeconds(6)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 25
    $fs = [System.IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
    try {
        $fs.Seek($before, 'Begin') | Out-Null
        $r = New-Object System.IO.StreamReader($fs); $t = $r.ReadToEnd(); $r.Dispose()
    } finally { $fs.Dispose() }
    $m = [regex]::Matches($t, '(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}).*?resumed \[')
    if ($m.Count -gt 0) {
        $logStamp = $m[$m.Count-1].Groups[1].Value
        $logMs = ((Get-Date) - $tClose).TotalMilliseconds
        break
    }
}
if ($logMs) {
    Info ("app decided to resume after " + [math]::Round($logMs) + " ms   (log time $logStamp)")
} else {
    Info "app never logged a resume within 6 s"
}

# 2) when do pixels move?
$motionMs = $null
$prev = GrabFrame
$deadline = $tClose.AddSeconds(8)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 30
    $cur = GrabFrame
    $d = FrameDiff $prev $cur
    $prev.Dispose(); $prev = $cur
    if ($d -gt 1.0) { $motionMs = ((Get-Date) - $tClose).TotalMilliseconds; break }
}
$prev.Dispose()
if ($motionMs) { Info ("pixels moved again after " + [math]::Round($motionMs) + " ms") }
else { Info "pixels never moved within 8 s" }

Section "Where the delay is"
if ($logMs -and $motionMs) {
    $decode = $motionMs - $logMs
    Info ("detection (hook -> decision) : " + [math]::Round($logMs) + " ms")
    Info ("decode    (decision -> pixels): " + [math]::Round($decode) + " ms")
    Write-Host ""
    if ($logMs -gt 250) {
        Write-Host "  The hook is slow. Fix in C# (WinEvent hook range / polling)." -ForegroundColor Yellow
    } elseif ($decode -gt 250) {
        Write-Host "  The video pipeline is slow. Fix in JS (decoder was released)." -ForegroundColor Yellow
    } else {
        Write-Host "  Both stages are fast." -ForegroundColor Green
    }
}

# ── PAUSE breakdown ──────────────────────────────────────────────────────────
Section "PAUSE breakdown"
$before = (Get-Item $log).Length
$proc = Start-Process -FilePath $cover -ArgumentList $screen.X, $screen.Y, $screen.Width, $screen.Height, '6' -PassThru
$tShow = Get-Date

$logMs = $null
$deadline = $tShow.AddSeconds(6)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 25
    $fs = [System.IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
    try {
        $fs.Seek($before, 'Begin') | Out-Null
        $r = New-Object System.IO.StreamReader($fs); $t = $r.ReadToEnd(); $r.Dispose()
    } finally { $fs.Dispose() }
    if ($t -match 'paused \[') { $logMs = ((Get-Date) - $tShow).TotalMilliseconds; break }
}
if ($logMs) { Info ("app decided to pause after " + [math]::Round($logMs) + " ms") } else { Info "never paused" }

$stopMs = $null
$prev = GrabFrame
$deadline = $tShow.AddSeconds(6)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 30
    $cur = GrabFrame
    $d = FrameDiff $prev $cur
    $prev.Dispose(); $prev = $cur
    if ($d -lt 0.3) {
        Start-Sleep -Milliseconds 50
        $nxt = GrabFrame
        if ((FrameDiff $cur $nxt) -lt 0.3) { $stopMs = ((Get-Date) - $tShow).TotalMilliseconds; $nxt.Dispose(); break }
        $nxt.Dispose()
    }
}
$prev.Dispose()
if ($stopMs) { Info ("pixels stopped after " + [math]::Round($stopMs) + " ms") } else { Info "never stopped" }

if ($logMs -and $stopMs) {
    Info ("detection : " + [math]::Round($logMs) + " ms")
    Info ("freeze    : " + [math]::Round($stopMs - $logMs) + " ms")
}

$proc.WaitForExit(20000) | Out-Null
if ($lv -ne [IntPtr]::Zero) { [Dz5]::ShowWindow($lv, 5) | Out-Null }
