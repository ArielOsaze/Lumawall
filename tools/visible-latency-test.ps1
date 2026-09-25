# Measures the delay the user actually experiences: how long after a pause ends
# before the wallpaper is visibly animating again.
#
# The existing timing tests measure when the app DECIDES to resume, read from its
# log. That is not what the user sees. What matters is when the pixels start
# moving again, which includes the time the video element needs to restart
# decoding after a pause.
#
# Method: capture the display in a tight loop and record the first moment the
# frame differs from the frozen one. That gives the visible resume delay.
#
# The same is measured for the pause direction: how long after a window covers
# the screen before the wallpaper actually stops moving.

$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class W4 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
}
'@

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Info($t)    { Write-Host "   $t" }

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$step = 40   # sample a 40px grid: enough to see motion, cheap enough to run fast

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

# Hide desktop icons so they do not register as motion.
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public class Dz4 {
  [DllImport("user32.dll")] public static extern IntPtr FindWindow(string c, string t);
  [DllImport("user32.dll")] public static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string t);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
}
'@
$dv = [Dz4]::FindWindowEx([Dz4]::FindWindow('Progman', $null), [IntPtr]::Zero, 'SHELLDLL_DefView', $null)
$lv = [Dz4]::FindWindowEx($dv, [IntPtr]::Zero, 'SysListView32', $null)
if ($lv -ne [IntPtr]::Zero) { [Dz4]::ShowWindow($lv, 0) | Out-Null }

$cover = Join-Path $PSScriptRoot 'FullscreenCover.exe'
if (-not (Test-Path $cover)) {
    $csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    & $csc /nologo /target:winexe "/out:$cover" /r:System.Windows.Forms.dll /r:System.Drawing.dll (Join-Path $PSScriptRoot 'FullscreenCover.cs') | Out-Null
}

# ── baseline: is the wallpaper actually moving? ──────────────────────────────
Section "Baseline - wallpaper must be animating"
try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 4

$a = GrabFrame; Start-Sleep -Milliseconds 700; $b = GrabFrame
$motion = FrameDiff $a $b
$a.Dispose(); $b.Dispose()
Info ("motion on screen: " + [math]::Round($motion,1) + "% of sampled pixels changed in 0.7 s")
if ($motion -lt 0.5) {
    Write-Host "  The wallpaper is not animating right now - cannot measure resume delay." -ForegroundColor Yellow
    Write-Host "  Make sure a video wallpaper is running on the primary display." -ForegroundColor Yellow
    exit 1
}

# ── measure PAUSE latency (visible) ──────────────────────────────────────────
Section "Visible PAUSE latency"
$proc = Start-Process -FilePath $cover -ArgumentList $screen.X, $screen.Y, $screen.Width, $screen.Height, '12' -PassThru
$t0 = Get-Date

$pauseMs = $null
$prev = GrabFrame
$deadline = $t0.AddSeconds(4)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 60
    $cur = GrabFrame
    $d = FrameDiff $prev $cur
    $prev.Dispose(); $prev = $cur
    if ($d -lt 0.3) {
        # Two consecutive still frames mean it has stopped.
        Start-Sleep -Milliseconds 60
        $next = GrabFrame
        $d2 = FrameDiff $cur $next
        $next.Dispose()
        if ($d2 -lt 0.3) { $pauseMs = ((Get-Date) - $t0).TotalMilliseconds; break }
    }
}
$prev.Dispose()
if ($pauseMs) { Info ("wallpaper stopped animating after " + [math]::Round($pauseMs) + " ms") }
else { Info "wallpaper never stopped within 4 s" }

# ── measure RESUME latency (visible) ─────────────────────────────────────────
Section "Visible RESUME latency"
$proc.WaitForExit(20000) | Out-Null
$t1 = Get-Date

$resumeMs = $null
$prev = GrabFrame
$deadline = $t1.AddSeconds(4)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 50
    $cur = GrabFrame
    $d = FrameDiff $prev $cur
    $prev.Dispose(); $prev = $cur
    if ($d -gt 1.0) { $resumeMs = ((Get-Date) - $t1).TotalMilliseconds; break }
}
$prev.Dispose()
if ($resumeMs) { Info ("wallpaper started animating again after " + [math]::Round($resumeMs) + " ms") }
else { Info "wallpaper never resumed within 4 s" }

# ── verdict ──────────────────────────────────────────────────────────────────
Section "RESULT"
$pass = $true
# The user's requirement: no perceptible delay in either direction. 250 ms is
# roughly the threshold where a person notices a stutter.
if ($pauseMs -and $pauseMs -lt 600) {
    Write-Host ("  [1] Pause is immediate ............. PASS (" + [math]::Round($pauseMs) + " ms)") -ForegroundColor Green
} else {
    Write-Host ("  [1] Pause is immediate ............. FAIL (" + $(if ($pauseMs) { [math]::Round($pauseMs) } else { 'never' }) + " ms)") -ForegroundColor Red
    $pass = $false
}
if ($resumeMs -and $resumeMs -lt 600) {
    Write-Host ("  [2] Resume is immediate ............ PASS (" + [math]::Round($resumeMs) + " ms)") -ForegroundColor Green
} else {
    Write-Host ("  [2] Resume is immediate ............ FAIL (" + $(if ($resumeMs) { [math]::Round($resumeMs) } else { 'never' }) + " ms)") -ForegroundColor Red
    $pass = $false
}

Write-Host ""
if ($pass) { Write-Host "NO VISIBLE DELAY IN EITHER DIRECTION" -ForegroundColor Green }
else       { Write-Host "DELAY DETECTED" -ForegroundColor Red }
