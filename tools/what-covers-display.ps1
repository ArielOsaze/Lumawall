# what-covers-display.ps1 - lists every window the app treats as covering a monitor.
#
# Why this exists:
#
# The app pauses a wallpaper when a window covers its monitor. When that is wrong, the
# log only says "paused DISPLAY1" - it never says which window the decision came from,
# so there is no way to tell a real maximised game from a stray overlay the app should
# have ignored.
#
# This reproduces the app's own test: every visible, non-minimised top-level window,
# its rectangle, its class and title, and how much of each monitor it covers. Run it
# while the wallpaper is unexpectedly stopped and the culprit is in the list.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/what-covers-display.ps1

$ErrorActionPreference = 'Continue'

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public class CoverScan
{
    public delegate bool EnumProc(IntPtr h, IntPtr p);

    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern bool IsZoomed(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern IntPtr GetWindowLongPtr64(IntPtr h, int index);
    [DllImport("user32.dll", EntryPoint = "GetWindowLong")] public static extern IntPtr GetWindowLong32(IntPtr h, int index);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    public const int GWL_EXSTYLE = -20;
    public const long WS_EX_TOOLWINDOW = 0x00000080;
    public const long WS_EX_NOACTIVATE = 0x08000000;
    public const long WS_EX_TRANSPARENT = 0x00000020;

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
    public static bool Visible(IntPtr h) { return IsWindowVisible(h); }
    public static bool Minimized(IntPtr h) { return IsIconic(h); }
    public static bool Maximized(IntPtr h) { return IsZoomed(h); }

    public static RECT RectOf(IntPtr h) { RECT r; GetWindowRect(h, out r); return r; }

    public static long ExStyle(IntPtr h)
    {
        // A 64-bit process needs the 64-bit accessor; the 32-bit one truncates.
        if (IntPtr.Size == 8) return GetWindowLongPtr64(h, GWL_EXSTYLE).ToInt64();
        return GetWindowLong32(h, GWL_EXSTYLE).ToInt64();
    }

    public static List<IntPtr> TopLevelWindows()
    {
        var list = new List<IntPtr>();
        EnumWindows(delegate(IntPtr h, IntPtr p) { list.Add(h); return true; }, IntPtr.Zero);
        return list;
    }
}
'@

Add-Type -AssemblyName System.Windows.Forms

$lumaPids = @(Get-Process LumaWall -ErrorAction SilentlyContinue | ForEach-Object { [int]$_.Id })

Write-Host ''
Write-Host '  which windows count as covering a monitor'
Write-Host '   + --------------------------------------------------------'
Write-Host ("  LumaWall pid(s): {0}" -f ($lumaPids -join ', '))
Write-Host ''

$monitors = [System.Windows.Forms.Screen]::AllScreens
Write-Host '  monitors:'
foreach ($m in $monitors) {
    $b = $m.Bounds
    Write-Host ("    {0,-14} {1},{2} {3}x{4}{5}" -f $m.DeviceName, $b.X, $b.Y, $b.Width, $b.Height,
        $(if ($m.Primary) { '  (primary)' } else { '' }))
}

$rows = @()
foreach ($h in [CoverScan]::TopLevelWindows()) {
    if (-not [CoverScan]::Visible($h)) { continue }
    if ([CoverScan]::Minimized($h)) { continue }

    $owner = [int][CoverScan]::PidOf($h)
    $cls = [CoverScan]::ClassOf($h)
    $title = [CoverScan]::TitleOf($h)
    $r = [CoverScan]::RectOf($h)
    $ex = [CoverScan]::ExStyle($h)
    $procName = (Get-Process -Id $owner -ErrorAction SilentlyContinue).ProcessName

    $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
    if ($w -le 0 -or $ht -le 0) { continue }

    # The same tests the app applies, so a window the app would skip is marked as such
    # rather than silently omitted - that is how a wrong skip becomes visible.
    $skip = @()
    if ($lumaPids -contains $owner) { $skip += 'own-process' }
    if ($cls -match '^(Progman|WorkerW|Shell_TrayWnd|Shell_SecondaryTrayWnd|SysShadow|ForegroundStaging|MultitaskingViewFrame|XamlExplorerHostIslandWindow)$') { $skip += 'shell-class' }
    if ($cls -like 'Windows.UI.Composition*' -or $cls -like 'Cua.*') { $skip += 'overlay-class' }
    if (($ex -band [CoverScan]::WS_EX_TOOLWINDOW) -ne 0) { $skip += 'toolwindow' }
    if (($ex -band [CoverScan]::WS_EX_NOACTIVATE) -ne 0) { $skip += 'noactivate' }
    if (($ex -band [CoverScan]::WS_EX_TRANSPARENT) -ne 0) { $skip += 'transparent' }
    if ($title.Length -eq 0) { $skip += 'no-title' }
    if ($procName -in @('explorer', 'SearchHost', 'StartMenuExperienceHost', 'TextInputHost', 'ShellExperienceHost')) { $skip += 'shell-process' }

    foreach ($m in $monitors) {
        $b = $m.Bounds
        $ow = [Math]::Min($r.Right, $b.Right) - [Math]::Max($r.Left, $b.Left)
        $oh = [Math]::Min($r.Bottom, $b.Bottom) - [Math]::Max($r.Top, $b.Top)
        if ($ow -le 0 -or $oh -le 0) { continue }
        $coverW = 100.0 * $ow / $b.Width
        $coverH = 100.0 * $oh / $b.Height

        # The app's rule: at least 98% of both axes, which is what a maximised window
        # covers once its invisible resize border is accounted for.
        $covers = ($coverW -ge 98 -and $coverH -ge 98)

        $rows += [pscustomobject]@{
            Monitor   = $m.DeviceName
            Process   = $procName
            Pid       = $owner
            Class     = $cls
            Title     = if ($title.Length -gt 34) { $title.Substring(0, 34) + '..' } else { $title }
            Rect      = "$($r.Left),$($r.Top) $w`x$ht"
            CoverPct  = ('{0:F0}%x{1:F0}%' -f $coverW, $coverH)
            Counts    = $covers
            Skipped   = ($skip -join ',')
        }
    }
}

if ($rows.Count -eq 0) {
    Write-Host ''
    Write-Host '  no visible top-level windows at all.'
    Write-Host ''
    exit 0
}

Write-Host ''
Write-Host '  windows that COUNT as covering (the app pauses those monitors):'
$covering = @($rows | Where-Object { $_.Counts -and -not $_.Skipped })
if ($covering.Count -eq 0) {
    Write-Host '    (none)'
} else {
    foreach ($r in $covering | Sort-Object Monitor, Process) {
        Write-Host ("    {0,-14} {1,-20} pid {2,-7} {3}" -f $r.Monitor, $r.Process, $r.Pid, $r.Class)
        Write-Host ("      title: {0}" -f $r.Title)
        Write-Host ("      rect:  {0}   covers {1}" -f $r.Rect, $r.CoverPct)
    }
}

Write-Host ''
Write-Host '  windows that cover but are SKIPPED (these should be overlays, not apps):'
$skipped = @($rows | Where-Object { $_.Counts -and $_.Skipped })
if ($skipped.Count -eq 0) {
    Write-Host '    (none)'
} else {
    foreach ($r in $skipped | Sort-Object Monitor, Process) {
        Write-Host ("    {0,-14} {1,-20} pid {2,-7} skip: {3}" -f $r.Monitor, $r.Process, $r.Pid, $r.Skipped)
        Write-Host ("      class: {0}   title: {1}" -f $r.Class, $r.Title)
        Write-Host ("      rect:  {0}   covers {1}" -f $r.Rect, $r.CoverPct)
    }
}

Write-Host ''
Write-Host '  partial covers (below 98%, ignored by the app):'
$partial = @($rows | Where-Object { -not $_.Counts } | Sort-Object Monitor, Process)
if ($partial.Count -eq 0) {
    Write-Host '    (none)'
} else {
    foreach ($r in $partial | Select-Object -First 12) {
        Write-Host ("    {0,-14} {1,-20} {2,-10} {3}" -f $r.Monitor, $r.Process, $r.CoverPct, $r.Title)
    }
}

Write-Host ''
exit 0
