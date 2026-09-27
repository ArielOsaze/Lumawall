# diagnose-wallpaper-windows.ps1 - every window the app owns, and whether video is decoding.
#
# Why this exists:
#
# Two questions decide whether a wallpaper fault is real, and neither can be answered
# from a screenshot:
#
#   1. How many windows does the app own per monitor? One is correct. More than one
#      means a window from an earlier wallpaper was never destroyed, and because they
#      sit at identical coordinates the stale one can cover the live one - the video
#      decodes perfectly and the user sees the old picture, or black.
#
#   2. Is the GPU actually decoding? A wallpaper window can hold a decoded frame and
#      look still, or show a frame while the decoder has stopped. The VideoDecode
#      engine counter for the app's own GPU process answers this without guessing.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/diagnose-wallpaper-windows.ps1

$ErrorActionPreference = 'Continue'

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public class WinInfo
{
    public delegate bool EnumProc(IntPtr h, IntPtr p);

    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr parent, EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern IntPtr GetParent(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr h, uint cmd);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    public const uint GW_HWNDPREV = 3;

    public static string ClassOf(IntPtr h)
    {
        var sb = new StringBuilder(256);
        GetClassName(h, sb, sb.Capacity);
        return sb.ToString();
    }

    public static string TitleOf(IntPtr h)
    {
        var sb = new StringBuilder(256);
        GetWindowTextW(h, sb, sb.Capacity);
        return sb.ToString();
    }

    public static uint PidOf(IntPtr h) { uint p; GetWindowThreadProcessId(h, out p); return p; }
    public static RECT RectOf(IntPtr h) { RECT r; GetWindowRect(h, out r); return r; }
    public static bool Visible(IntPtr h) { return IsWindowVisible(h); }
    public static IntPtr ParentOf(IntPtr h) { return GetParent(h); }
    public static IntPtr PrevOf(IntPtr h) { return GetWindow(h, GW_HWNDPREV); }

    /// <summary>Every window in the process, top-level and child, with its parent chain.</summary>
    public static List<IntPtr> AllWindowsOfPid(uint target)
    {
        var found = new List<IntPtr>();
        var seen = new HashSet<IntPtr>();

        EnumWindows(delegate(IntPtr h, IntPtr p)
        {
            if (PidOf(h) == target && seen.Add(h)) found.Add(h);
            EnumChildWindows(h, delegate(IntPtr c, IntPtr q)
            {
                if (PidOf(c) == target && seen.Add(c)) found.Add(c);
                return true;
            }, IntPtr.Zero);
            return true;
        }, IntPtr.Zero);

        return found;
    }
}
'@

function Get-LumaWallProcesses {
    @(Get-Process LumaWall -ErrorAction SilentlyContinue)
}

Write-Host ''
Write-Host '  windows owned by LumaWall, and where video is decoding'
Write-Host '   + --------------------------------------------------------'

$procs = Get-LumaWallProcesses
if ($procs.Count -eq 0) {
    Write-Host ''
    Write-Host '  LumaWall is not running.'
    Write-Host ''
    exit 2
}

# ── the windows ──────────────────────────────────────────────────────────────
$all = @()
foreach ($p in $procs) {
    foreach ($h in [WinInfo]::AllWindowsOfPid([uint32]$p.Id)) {
        $r = [WinInfo]::RectOf($h)
        $w = $r.Right - $r.Left
        $ht = $r.Bottom - $r.Top
        $parent = [WinInfo]::ParentOf($h)
        $all += [pscustomobject]@{
            Handle  = $h
            Pid     = $p.Id
            Class   = [WinInfo]::ClassOf($h)
            Title   = [WinInfo]::TitleOf($h)
            Width   = $w
            Height  = $ht
            Left    = $r.Left
            Top     = $r.Top
            Parent  = $parent
            Visible = [WinInfo]::Visible($h)
            OnDesktop = ($parent -ne [IntPtr]::Zero)
        }
    }
}

# Only real surfaces: large enough to be a wallpaper, and attached to a shell window.
$surfaces = @($all | Where-Object { $_.Width -ge 320 -and $_.Height -ge 240 -and $_.OnDesktop })

Write-Host ("  {0} window(s) total, {1} large enough to be a wallpaper surface" -f $all.Count, $surfaces.Count)
Write-Host ''
Write-Host '  handle      size          pos            class           parent      visible'
foreach ($s in ($surfaces | Sort-Object Left, Top, Handle)) {
    Write-Host ("  {0,-11} {1,-13} {2,-14} {3,-15} {4,-11} {5}" -f `
        $s.Handle, "$($s.Width)x$($s.Height)", "($($s.Left),$($s.Top))", $s.Class, $s.Parent, $s.Visible)
}

# ── the duplicate check ──────────────────────────────────────────────────────
#
# One wallpaper window per position is correct. Two at the same position is a fault:
# they are stacked, and whichever is on top decides what the user sees - which is how
# a wallpaper that reports itself ready can still be invisible.
$byPosition = $surfaces | Group-Object { "$($_.Left),$($_.Top),$($_.Width)x$($_.Height)" }
$duplicates = @($byPosition | Where-Object { $_.Count -gt 1 })

Write-Host ''
if ($duplicates.Count -gt 0) {
    Write-Host ("  {0} screen position(s) have MORE THAN ONE wallpaper window:" -f $duplicates.Count)
    foreach ($group in $duplicates) {
        Write-Host ("    at {0}: {1} windows" -f $group.Name, $group.Count)
        foreach ($s in $group.Group) {
            # GW_HWNDPREV walks toward the top of the Z-order, so the window with more
            # predecessors is further back and the last one listed is the visible one.
            $behind = [WinInfo]::PrevOf($s.Handle)
            Write-Host ("      handle {0}  behind {1}" -f $s.Handle, $behind)
        }
    }
    Write-Host ''
    Write-Host '  A stacked pair is a leak: an earlier wallpaper window was never'
    Write-Host '  destroyed, and it can cover the window the app believes is live.'
} else {
    Write-Host '  one wallpaper window per screen position - no stacking.'
}

# ── is video decoding? ───────────────────────────────────────────────────────
#
# The GPU engine counters name the process that owns each engine, so the app's own
# decode work can be separated from every other application's.
Write-Host ''
Write-Host '  video decode engines active right now:'
try {
    $engines = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine -ErrorAction Stop |
        Where-Object { $_.Name -like '*VideoDecode*' -and $_.UtilizationPercentage -gt 0 }

    if (-not $engines) {
        Write-Host '    (none - no process is decoding video at this moment)'
    } else {
        foreach ($e in $engines) {
            $owner = if ($e.Name -match 'pid_(\d+)_') { [int]$Matches[1] } else { 0 }
            $name = (Get-Process -Id $owner -ErrorAction SilentlyContinue).ProcessName
            $isOurs = $procs.Id -contains $owner
            # The GPU process is a separate msedgewebview2.exe, so membership in the
            # app's own process tree is what identifies it, not the LumaWall pid.
            $marker = if ($isOurs) { 'LumaWall' } else { '' }
            Write-Host ("    pid {0,-7} {1,-22} {2,3}%  {3}" -f $owner, ($name + ' ' + $marker), $e.UtilizationPercentage, $e.Name)
        }
    }
} catch {
    Write-Host ('    could not read GPU counters: ' + $_.Exception.Message)
}

Write-Host ''
exit 0
