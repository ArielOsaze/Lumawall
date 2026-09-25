# Measures the visible resume delay correctly.
#
# The previous version of this test was wrong, and the app's own instrumentation
# proved it: the page reported a new frame 23 ms after play(), with readyState=4
# and currentTime advancing, yet the screen test claimed 5 seconds.
#
# The flaw: the video resumes from the exact frame it paused on, so the first
# frames after resume are continuous with the frozen frame. In a calm scene the
# difference between consecutive frames is tiny, so a "has motion started" test
# with a 1% threshold misses it for seconds. The measurement was reporting the
# video's content, not the app's latency.
#
# Correct method: keep the frame that was on screen when the desktop reappeared
# as a reference, and watch how the difference from THAT frame grows. A frozen
# screen keeps a difference of 0.0% no matter how slow the scene is; a playing
# video moves away from the reference even if slowly.
#
# The full difference curve is printed, so a slow start can be told apart from a
# real stall.

$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing

function Section($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Info($t)    { Write-Host "   $t" }

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$step = 30

function GrabFrame {
    $bmp = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($screen.X, $screen.Y, 0, 0, $bmp.Size)
    $g.Dispose()
    return $bmp
}

# Difference from a reference frame, as a percentage of sampled pixels.
function DiffFrom($ref, $cur) {
    $changed = 0; $sampled = 0
    for ($y = 0; $y -lt $ref.Height; $y += $step) {
        for ($x = 0; $x -lt $ref.Width; $x += $step) {
            $ca = $ref.GetPixel($x, $y); $cb = $cur.GetPixel($x, $y)
            $sampled++
            if ([math]::Abs($ca.R-$cb.R) + [math]::Abs($ca.G-$cb.G) + [math]::Abs($ca.B-$cb.B) -gt 24) { $changed++ }
        }
    }
    if ($sampled -eq 0) { return 0 }
    return 100 * $changed / $sampled
}

# How much of the frame is near-black: used to tell the cover from the desktop.
function FractionDark($bmp) {
    $dark = 0; $sampled = 0
    for ($y = 0; $y -lt $bmp.Height; $y += 60) {
        for ($x = 0; $x -lt $bmp.Width; $x += 60) {
            $c = $bmp.GetPixel($x, $y); $sampled++
            if (($c.R + $c.G + $c.B) -lt 60) { $dark++ }
        }
    }
    if ($sampled -eq 0) { return 0 }
    return $dark / $sampled
}

Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public class Dz6 {
  [DllImport("user32.dll")] public static extern IntPtr FindWindow(string c, string t);
  [DllImport("user32.dll")] public static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string t);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
}
'@
$dv = [Dz6]::FindWindowEx([Dz6]::FindWindow('Progman', $null), [IntPtr]::Zero, 'SHELLDLL_DefView', $null)
$lv = [Dz6]::FindWindowEx($dv, [IntPtr]::Zero, 'SysListView32', $null)
if ($lv -ne [IntPtr]::Zero) { [Dz6]::ShowWindow($lv, 0) | Out-Null }

$cover = Join-Path $PSScriptRoot 'FullscreenCover.exe'

Section "Baseline"
try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 5
$a = GrabFrame; Start-Sleep -Milliseconds 600; $b = GrabFrame
$base = DiffFrom $a $b; $a.Dispose(); $b.Dispose()
Info ("motion over 0.6 s: " + [math]::Round($base,2) + "%")
if ($base -lt 0.2) { Write-Host "  wallpaper not animating - abort" -ForegroundColor Yellow; exit 1 }

Section "Pause then resume"
$proc = Start-Process -FilePath $cover -ArgumentList $screen.X, $screen.Y, $screen.Width, $screen.Height, '8' -PassThru
Start-Sleep -Seconds 6      # let the pause settle
$proc.WaitForExit(20000) | Out-Null
$tClose = Get-Date

# Wait for the desktop to reappear (the cover is black, the wallpaper is not).
$ref = $null; $tAppear = $null
$deadline = $tClose.AddSeconds(10)
while ((Get-Date) -lt $deadline) {
    $cur = GrabFrame
    if ((FractionDark $cur) -lt 0.45) { $ref = $cur; $tAppear = Get-Date; break }
    $cur.Dispose()
}
if (-not $ref) { Write-Host "  desktop never reappeared" -ForegroundColor Red; exit 1 }
Info ("desktop visible again after " + [math]::Round(((Get-Date) - $tClose).TotalMilliseconds) + " ms")

# Follow the difference from that first visible frame.
Section "Difference from the first visible frame"
$curve = @()
$first = $null
$deadline = $tAppear.AddSeconds(6)
while ((Get-Date) -lt $deadline) {
    $cur = GrabFrame
    $d = DiffFrom $ref $cur
    $cur.Dispose()
    $ms = ((Get-Date) - $tAppear).TotalMilliseconds
    $curve += [pscustomobject]@{ ms = [math]::Round($ms); diff = [math]::Round($d,2) }
    if (-not $first -and $d -gt 0.5) { $first = $ms }
    if ($ms -gt 2500 -and $first) { break }
}
$ref.Dispose()

$curve | ForEach-Object { Info ("  t+" + $_.ms.ToString().PadLeft(5) + " ms   diff " + $_.diff + "%") }

Section "RESULT"
if ($first) {
    Write-Host ("  Wallpaper visibly animating again after " + [math]::Round($first) + " ms") -ForegroundColor Green
    if ($first -lt 400) { Write-Host "  PASS - no perceptible delay" -ForegroundColor Green }
    elseif ($first -lt 1000) { Write-Host "  MARGINAL - slightly noticeable" -ForegroundColor Yellow }
    else { Write-Host "  FAIL - clearly delayed" -ForegroundColor Red }
} else {
    Write-Host "  Wallpaper never moved away from the frozen frame" -ForegroundColor Red
}
