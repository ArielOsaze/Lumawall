# check-cloaked-windows.ps1 - windows that report as visible but are actually hidden.
#
# Why this exists:
#
# Windows leaves windows behind. A UWP app that the user closed - Settings, Photos, the
# Store - can keep its process and its window alive, and that window still answers
# IsWindowVisible with true and still has the full-screen rectangle it had when it was
# open. The Desktop Window Manager knows the truth and marks such a window "cloaked";
# user32 does not report it at all.
#
# An application that decides "is a fullscreen app covering this monitor?" from
# IsWindowVisible alone will therefore see a closed Settings window as a fullscreen app
# and pause the wallpaper on that monitor - forever, because the window never goes away.
# That is a wallpaper that is applied and never animates, with a log that insists the
# pause was correct.
#
# This lists every window whose cloaked state disagrees with its visible state, so the
# culprit can be named instead of guessed at.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/check-cloaked-windows.ps1

$ErrorActionPreference = 'Continue'

Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public class CloakScan
{
    public delegate bool EnumProc(IntPtr h, IntPtr p);

    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("dwmapi.dll")] public static extern int DwmGetWindowAttribute(IntPtr h, int attr, out int value, int size);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    public const int DWMWA_CLOAKED = 14;

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
    public static RECT RectOf(IntPtr h) { RECT r; GetWindowRect(h, out r); return r; }

    /// <summary>
    /// 0 when the window is drawn normally. Non-zero when DWM has cloaked it: 1 means the
    /// application cloaked it itself, 2 means the system did (a closed UWP window), 4
    /// means it is cloaked because its parent is. All three mean "not on screen".
    /// </summary>
    public static int Cloaked(IntPtr h)
    {
        int value;
        int hr = DwmGetWindowAttribute(h, DWMWA_CLOAKED, out value, sizeof(int));
        if (hr != 0) return 0;   // not a DWM-composited window; treat as uncloaked
        return value;
    }

    public static List<IntPtr> TopLevel()
    {
        var list = new List<IntPtr>();
        EnumWindows(delegate(IntPtr h, IntPtr p) { list.Add(h); return true; }, IntPtr.Zero);
        return list;
    }
}
'@

Add-Type -AssemblyName System.Windows.Forms

$monitors = [System.Windows.Forms.Screen]::AllScreens

Write-Host ''
Write-Host '  windows that report visible but are cloaked (really hidden)'
Write-Host '   + --------------------------------------------------------'

$suspects = @()
foreach ($h in [CloakScan]::TopLevel()) {
    if (-not [CloakScan]::Visible($h)) { continue }
    $cloaked = [CloakScan]::Cloaked($h)
    if ($cloaked -eq 0) { continue }

    $r = [CloakScan]::RectOf($h)
    $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
    if ($w -le 0 -or $ht -le 0) { continue }

    $owner = [int][CloakScan]::PidOf($h)
    $proc = Get-Process -Id $owner -ErrorAction SilentlyContinue

    # Which monitors would this window appear to cover?
    $covers = @()
    foreach ($m in $monitors) {
        $b = $m.Bounds
        $ow = [Math]::Min($r.Right, $b.Right) - [Math]::Max($r.Left, $b.Left)
        $oh = [Math]::Min($r.Bottom, $b.Bottom) - [Math]::Max($r.Top, $b.Top)
        if ($ow -le 0 -or $oh -le 0) { continue }
        $pctW = 100.0 * $ow / $b.Width
        $pctH = 100.0 * $oh / $b.Height
        if ($pctW -ge 98 -and $pctH -ge 98) { $covers += $m.DeviceName }
    }

    $suspects += [pscustomobject]@{
        Handle   = $h
        Cloaked  = $cloaked
        Process  = if ($proc) { $proc.ProcessName } else { '?' }
        Pid      = $owner
        Respond  = if ($proc) { $proc.Responding } else { $null }
        Class    = [CloakScan]::ClassOf($h)
        Title    = [CloakScan]::TitleOf($h)
        Size     = "$($w)x$($ht)"
        Minimized = [CloakScan]::Minimized($h)
        Covers   = ($covers -join ',')
    }
}

if ($suspects.Count -eq 0) {
    Write-Host ''
    Write-Host '  none. Every visible window is genuinely on screen, so a pause'
    Write-Host '  decision based on IsWindowVisible is trustworthy right now.'
    Write-Host ''
    exit 0
}

Write-Host ''
foreach ($s in $suspects) {
    Write-Host ("  {0,-22} pid {1,-7} cloaked={2} responding={3} minimized={4}" -f `
        $s.Process, $s.Pid, $s.Cloaked, $s.Respond, $s.Minimized)
    Write-Host ("    class: {0}" -f $s.Class)
    Write-Host ("    title: {0}" -f $s.Title)
    Write-Host ("    size:  {0}" -f $s.Size)
    if ($s.Covers.Length -gt 0) {
        Write-Host ("    WOULD APPEAR TO COVER: {0}" -f $s.Covers) -ForegroundColor Yellow
    }
}

Write-Host ''
$covering = @($suspects | Where-Object { $_.Covers.Length -gt 0 })
if ($covering.Count -gt 0) {
    Write-Host ("  {0} cloaked window(s) would be mistaken for a fullscreen app." -f $covering.Count)
    Write-Host '  Any monitor listed above is being paused for a window the user'
    Write-Host '  cannot see. Checking DWMWA_CLOAKED is what fixes it.'
    Write-Host ''
    exit 1
}

Write-Host '  cloaked windows found, but none covers a whole monitor.'
Write-Host ''
exit 0
