# capture-wallpaper-windows.ps1 - captures each wallpaper window's OWN content.
#
# Why this exists:
#
# Every screen-based test has the same blind spot: if a window covers the desktop, the
# screenshot shows the window, not the wallpaper. check-wallpaper-motion.ps1 measures
# the screen, so a covered desktop reads as "frozen" whether the wallpaper is broken or
# merely hidden - and the two need opposite responses.
#
# This asks Windows to draw a specific window into a bitmap, using PrintWindow with
# PW_RENDERFULLCONTENT. That flag exists precisely for DirectComposition surfaces like
# WebView2, which is what this app renders with. The result shows what the wallpaper
# window contains even while it sits behind a maximised browser.
#
# Two captures are compared. Identical bitmaps mean the wallpaper is genuinely frozen;
# different bitmaps mean it is animating and the screen was simply covered.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/capture-wallpaper-windows.ps1
#   ... -GapSeconds 2      time between the two captures
#   ... -KeepImages        keep the PNGs for inspection

param(
    [double]$GapSeconds = 1.5,
    [switch]$KeepImages
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$root = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root 'build'
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

Add-Type -ReferencedAssemblies 'System.Drawing' -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public class WallpaperWindows
{
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr parent, EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
    [DllImport("user32.dll")] static extern IntPtr FindWindow(string cls, string win);
    [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);

    public delegate bool EnumProc(IntPtr h, IntPtr p);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    public const uint PW_RENDERFULLCONTENT = 0x00000002;

    public static string ClassNameOf(IntPtr h)
    {
        var sb = new StringBuilder(256);
        GetClassName(h, sb, sb.Capacity);
        return sb.ToString();
    }

    public static List<IntPtr> ChildrenOf(string className)
    {
        var found = new List<IntPtr>();
        IntPtr parent = FindWindow(className, null);
        if (parent == IntPtr.Zero) return found;
        EnumChildWindows(parent, delegate(IntPtr h, IntPtr p)
        {
            found.Add(h);
            return true;
        }, IntPtr.Zero);
        return found;
    }

    public static uint PidOf(IntPtr h)
    {
        uint pid;
        GetWindowThreadProcessId(h, out pid);
        return pid;
    }

    public static RECT RectOf(IntPtr h)
    {
        RECT r;
        GetWindowRect(h, out r);
        return r;
    }

    public static bool Visible(IntPtr h) { return IsWindowVisible(h); }

    /// <summary>
    /// Draws the window into a fresh bitmap. Returns null when the window is empty or
    /// PrintWindow fails, so the caller can say so rather than reporting a blank image
    /// as a frozen wallpaper.
    /// </summary>
    public static System.Drawing.Bitmap Capture(IntPtr h)
    {
        RECT r = RectOf(h);
        int w = r.Right - r.Left, ht = r.Bottom - r.Top;
        if (w <= 0 || ht <= 0) return null;

        var bmp = new System.Drawing.Bitmap(w, ht);
        using (var g = System.Drawing.Graphics.FromImage(bmp))
        {
            IntPtr dc = g.GetHdc();
            bool ok;
            try { ok = PrintWindow(h, dc, PW_RENDERFULLCONTENT); }
            finally { g.ReleaseHdc(dc); }
            if (!ok) { bmp.Dispose(); return null; }
        }
        return bmp;
    }
}
'@

function Get-LumaWallPids {
    @(Get-Process LumaWall -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
}

# The wallpaper windows live under the shell's WorkerW, and belong to LumaWall's process.
# Both facts are checked: WorkerW has other children, and LumaWall has other windows.
function Find-WallpaperWindows {
    $pids = Get-LumaWallPids
    if ($pids.Count -eq 0) { return @() }

    $found = @()
    foreach ($cls in @('WorkerW', 'Progman')) {
        foreach ($h in [WallpaperWindows]::ChildrenOf($cls)) {
            $ownerPid = [WallpaperWindows]::PidOf($h)
            if ($pids -contains [int]$ownerPid) {
                $r = [WallpaperWindows]::RectOf($h)
                $w = $r.Right - $r.Left
                $ht = $r.Bottom - $r.Top
                # Skip the 1x1 helper windows the app creates; only real surfaces count.
                if ($w -ge 320 -and $ht -ge 240) {
                    $found += [pscustomobject]@{
                        Handle = $h
                        Pid    = [int]$ownerPid
                        Class  = [WallpaperWindows]::ClassNameOf($h)
                        Width  = $w
                        Height = $ht
                        Left   = $r.Left
                        Top    = $r.Top
                        Visible = [WallpaperWindows]::Visible($h)
                    }
                }
            }
        }
    }
    return $found
}

# How different are two bitmaps? Mean absolute channel difference, 0-255 per channel.
# A frozen video gives 0; a playing video gives several units; anything above ~1 means
# something in the window is changing.
function Compare-Bitmaps($a, $b) {
    if ($null -eq $a -or $null -eq $b) { return $null }
    if ($a.Width -ne $b.Width -or $a.Height -ne $b.Height) { return $null }

    $w = $a.Width; $h = $a.Height
    # Sample on a grid rather than every pixel: a 1080p window is 2M pixels and the
    # GetPixel calls dominate the runtime.
    $stepX = [Math]::Max(1, [int]($w / 120))
    $stepY = [Math]::Max(1, [int]($h / 80))

    $total = 0.0; $count = 0; $changed = 0
    for ($y = 0; $y -lt $h; $y += $stepY) {
        for ($x = 0; $x -lt $w; $x += $stepX) {
            $pa = $a.GetPixel($x, $y); $pb = $b.GetPixel($x, $y)
            $d = [Math]::Abs($pa.R - $pb.R) + [Math]::Abs($pa.G - $pb.G) + [Math]::Abs($pa.B - $pb.B)
            $total += $d
            $count++
            if ($d -gt 12) { $changed++ }
        }
    }
    if ($count -eq 0) { return $null }
    return [pscustomobject]@{
        MeanDifference = [Math]::Round($total / $count, 2)
        ChangedPercent = [Math]::Round(100.0 * $changed / $count, 1)
        Samples        = $count
    }
}

# Is the bitmap a single flat colour? A wallpaper window that never received content
# renders as black, and that is worth distinguishing from a frozen frame of a video.
function Get-Flatness($bmp) {
    if ($null -eq $bmp) { return $null }
    $w = $bmp.Width; $h = $bmp.Height
    $stepX = [Math]::Max(1, [int]($w / 60)); $stepY = [Math]::Max(1, [int]($h / 40))
    $min = 999; $max = -1; $sum = 0.0; $n = 0
    for ($y = 0; $y -lt $h; $y += $stepY) {
        for ($x = 0; $x -lt $w; $x += $stepX) {
            $p = $bmp.GetPixel($x, $y)
            $lum = ($p.R + $p.G + $p.B) / 3.0
            if ($lum -lt $min) { $min = $lum }
            if ($lum -gt $max) { $max = $lum }
            $sum += $lum; $n++
        }
    }
    if ($n -eq 0) { return $null }
    return [pscustomobject]@{
        MeanLuminance = [Math]::Round($sum / $n, 1)
        Range         = [Math]::Round($max - $min, 1)
    }
}

Write-Host ''
Write-Host '  what the wallpaper windows contain'
Write-Host '   + --------------------------------------------------------'

$windows = Find-WallpaperWindows
if ($windows.Count -eq 0) {
    Write-Host ''
    Write-Host '  no wallpaper windows found. Either the app is not running, or it'
    Write-Host '  has not attached anything to the desktop yet.'
    Write-Host ''
    exit 2
}

Write-Host ("  found {0} wallpaper window(s)" -f $windows.Count)
foreach ($w in $windows) {
    Write-Host ("    handle {0,-10} pid {1,-7} {2}x{3} at ({4},{5}) visible={6}" -f `
        $w.Handle, $w.Pid, $w.Width, $w.Height, $w.Left, $w.Top, $w.Visible)
}

Write-Host ''
Write-Host ("  capturing twice, {0}s apart ..." -f $GapSeconds)

$first = @{}
foreach ($w in $windows) { $first[$w.Handle] = [WallpaperWindows]::Capture($w.Handle) }

Start-Sleep -Seconds $GapSeconds

$results = @()
foreach ($w in $windows) {
    $a = $first[$w.Handle]
    $b = [WallpaperWindows]::Capture($w.Handle)

    if ($null -eq $a -or $null -eq $b) {
        $results += [pscustomobject]@{
            Handle = $w.Handle; Size = "$($w.Width)x$($w.Height)"
            Motion = $null; Changed = $null; Flat = $null
            Verdict = 'PrintWindow returned nothing'
        }
        continue
    }

    $diff = Compare-Bitmaps $a $b
    $flat = Get-Flatness $b

    $verdict = if ($null -eq $diff) {
        'sizes changed between captures'
    } elseif ($diff.MeanDifference -lt 0.5) {
        if ($null -ne $flat -and $flat.Range -lt 6) { 'FLAT - no content at all' }
        else { 'FROZEN - content present but not changing' }
    } else {
        'ANIMATING'
    }

    $results += [pscustomobject]@{
        Handle  = $w.Handle
        Position = "$($w.Left),$($w.Top)"
        Size    = "$($w.Width)x$($w.Height)"
        Motion  = $diff.MeanDifference
        Changed = $diff.ChangedPercent
        Flat    = if ($null -ne $flat) { "$($flat.MeanLuminance)/$($flat.Range)" } else { '-' }
        Verdict = $verdict
    }

    if ($KeepImages) {
        $name = Join-Path $outDir ("wallpaper-{0}-a.png" -f $w.Handle)
        $a.Save($name, [System.Drawing.Imaging.ImageFormat]::Png)
        $name = Join-Path $outDir ("wallpaper-{0}-b.png" -f $w.Handle)
        $b.Save($name, [System.Drawing.Imaging.ImageFormat]::Png)
    }

    $a.Dispose(); $b.Dispose()
}

Write-Host ''
Write-Host '  handle       position      size          motion  changed  luminance/range   verdict'
foreach ($r in $results) {
    $m = if ($null -eq $r.Motion) { '  -   ' } else { '{0,6:F2}' -f $r.Motion }
    $c = if ($null -eq $r.Changed) { '   -  ' } else { '{0,5:F1}%' -f $r.Changed }
    $f = if ($null -eq $r.Flat) { '-' } else { $r.Flat }
    Write-Host ("  {0,-12} {1,-13} {2,-13} {3}  {4}  {5,-17} {6}" -f $r.Handle, $r.Position, $r.Size, $m, $c, $f, $r.Verdict)
}

# The verdict that matters is per SCREEN POSITION, not per window. Each monitor has a
# WinForms host window and a WebView2 child at the same coordinates; the child is the one
# that paints. Grouping by position and asking "is any window here animating?" is what
# answers the user's question - and it also exposes the case where a stale window sits on
# top of a live one and wins the pixels.
Write-Host ''
Write-Host '  per screen position:'
$byPosition = $results | Group-Object Position
foreach ($group in $byPosition) {
    $animatingHere = @($group.Group | Where-Object { $_.Verdict -eq 'ANIMATING' })
    $flatHere = @($group.Group | Where-Object { $_.Verdict -like 'FLAT*' })
    $state = if ($animatingHere.Count -gt 0) { 'ANIMATING' }
             elseif ($flatHere.Count -eq $group.Count) { 'NO CONTENT' }
             else { 'STILL' }
    Write-Host ("    {0,-14} {1,-13} {2} window(s)  ->  {3}" -f $group.Name, $group.Group[0].Size, $group.Count, $state)
}

# What the app itself believes, so a frozen window can be compared with the app's
# intent: if the app thinks it is playing and the window is frozen, that is a bug; if
# the app knows it paused, a still window is correct.
$logPath = Join-Path $env:LOCALAPPDATA 'LumaWall\logs\lumawall.log'
if (Test-Path $logPath) {
    $lastPlayback = Get-Content $logPath -Tail 400 |
        Where-Object { $_ -match 'Playback updated|pause-ack|resumed' } |
        Select-Object -Last 1
    if ($lastPlayback) {
        Write-Host ''
        Write-Host ('  the app last decided: ' + ($lastPlayback -replace '^\S+ \S+ \[\d+\] ', ''))
    }
}

$animating = @($results | Where-Object { $_.Verdict -eq 'ANIMATING' })
$frozen    = @($results | Where-Object { $_.Verdict -like 'FROZEN*' })
$flat      = @($results | Where-Object { $_.Verdict -like 'FLAT*' })

Write-Host ''
if ($flat.Count -gt 0) {
    Write-Host ("  {0} window(s) have no content at all - the wallpaper never rendered." -f $flat.Count)
    Write-Host '  That is a real fault: the page reported ready but drew nothing.'
} elseif ($frozen.Count -gt 0) {
    Write-Host ("  {0} window(s) hold content but are not changing." -f $frozen.Count)
    Write-Host '  Compare with the app decision above: if it says paused, this is'
    Write-Host '  correct behaviour; if it says playing, the wallpaper is stuck.'
} elseif ($animating.Count -gt 0) {
    Write-Host ("  {0} window(s) are animating." -f $animating.Count)
    Write-Host '  The wallpaper is running, whatever the screen shows - any cover'
    Write-Host '  by other windows is just occlusion, not a fault.'
} else {
    Write-Host '  nothing conclusive - see the per-window rows above.'
}
Write-Host ''

if ($flat.Count -gt 0) { exit 1 }
exit 0
