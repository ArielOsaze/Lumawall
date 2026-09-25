# Definitive render check: sample the desktop pixels twice, a second apart.
#
# A playing video changes its pixels every frame; a black/frozen desktop does
# not. This separates "the wallpaper is rendering" from "the window exists and
# is positioned correctly but nothing is drawn into it", which is exactly the
# state the app was in after the Explorer restart.

$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing

function Sample-Screen($bounds) {
    $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($bounds.X, $bounds.Y, 0, 0, $bmp.Size)
    $g.Dispose()
    return $bmp
}

function Stats($bmp, $step) {
    # Sample a grid of pixels; report mean brightness and how many are non-black.
    $sum = 0; $count = 0; $nonBlack = 0
    for ($y = 0; $y -lt $bmp.Height; $y += $step) {
        for ($x = 0; $x -lt $bmp.Width; $x += $step) {
            $c = $bmp.GetPixel($x, $y)
            $lum = ($c.R + $c.G + $c.B) / 3
            $sum += $lum; $count++
            if ($lum -gt 12) { $nonBlack++ }
        }
    }
    return [pscustomobject]@{
        MeanLuma  = [math]::Round($sum / $count, 1)
        NonBlack  = $nonBlack
        Sampled   = $count
        PctColour = [math]::Round(100 * $nonBlack / $count, 1)
    }
}

function DiffPixels($a, $b, $step) {
    $changed = 0; $count = 0
    for ($y = 0; $y -lt $a.Height; $y += $step) {
        for ($x = 0; $x -lt $a.Width; $x += $step) {
            $ca = $a.GetPixel($x, $y); $cb = $b.GetPixel($x, $y)
            $count++
            if ([math]::Abs($ca.R - $cb.R) + [math]::Abs($ca.G - $cb.G) + [math]::Abs($ca.B - $cb.B) -gt 18) { $changed++ }
        }
    }
    return [pscustomobject]@{ Changed = $changed; Sampled = $count; Pct = [math]::Round(100 * $changed / $count, 1) }
}

# Hide desktop icons so they do not pollute the sample.
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public class Dz {
  [DllImport("user32.dll")] public static extern IntPtr FindWindow(string c, string t);
  [DllImport("user32.dll")] public static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string t);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
}
'@
$defView = [Dz]::FindWindowEx([Dz]::FindWindow('Progman', $null), [IntPtr]::Zero, 'SHELLDLL_DefView', $null)
$listView = [Dz]::FindWindowEx($defView, [IntPtr]::Zero, 'SysListView32', $null)
if ($listView -ne [IntPtr]::Zero) { [Dz]::ShowWindow($listView, 0) | Out-Null }

# Minimize everything so only the desktop is visible.
try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 3

$results = @()
foreach ($s in [System.Windows.Forms.Screen]::AllScreens) {
    Write-Host ("== " + $s.DeviceName + " ==") -ForegroundColor Cyan
    $step = 16

    $f1 = Sample-Screen $s.Bounds
    Start-Sleep -Milliseconds 1100
    $f2 = Sample-Screen $s.Bounds

    $s1 = Stats $f1 $step
    $s2 = Stats $f2 $step
    $d  = DiffPixels $f1 $f2 $step

    Write-Host ("   mean luma   : " + $s1.MeanLuma + " -> " + $s2.MeanLuma)
    Write-Host ("   coloured    : " + $s1.PctColour + "% of sampled pixels")
    Write-Host ("   changed     : " + $d.Pct + "% of pixels between frames")

    $verdict = if ($s1.MeanLuma -lt 10 -and $d.Pct -lt 2) { "BLACK / NOT RENDERING" }
               elseif ($d.Pct -ge 2) { "RENDERING (animating)" }
               else { "STATIC IMAGE (not animating)" }
    Write-Host ("   verdict     : " + $verdict) -ForegroundColor $(if ($d.Pct -ge 2) { 'Green' } else { 'Red' })

    $results += [pscustomobject]@{ Display = $s.DeviceName; Luma = $s1.MeanLuma; ColourPct = $s1.PctColour; ChangePct = $d.Pct; Verdict = $verdict }

    $f1.Save((Join-Path $PSScriptRoot ("render-" + ($s.DeviceName -replace '[\\\.]','') + ".png")), [System.Drawing.Imaging.ImageFormat]::Png)
    $f1.Dispose(); $f2.Dispose()
}

Write-Host ""
Write-Host "=== SUMMARY ===" -ForegroundColor Cyan
$results | Format-Table -AutoSize | Out-String | Write-Host

$animating = ($results | Where-Object { $_.Verdict -like 'RENDERING*' }).Count
Write-Host ("$animating of " + $results.Count + " displays are animating")
