# Verifies the maximize/restore glyph swap by capturing the title bar in both
# window states.
#
# Finds the window through the process's MainWindowHandle (more reliable than
# enumerating, which also matches the hidden helper windows LumaWall creates),
# restores it first, and captures the top-right corner where the controls live.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public static class WinCtl4
{
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);

    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }

    public const int SW_MAXIMIZE = 3;
    public const int SW_RESTORE = 9;
    public const int SW_SHOW = 5;
}
'@

$out = Split-Path $PSScriptRoot -Parent
$proc = Get-Process LumaWall -ErrorAction Stop | Select-Object -First 1
$hwnd = $proc.MainWindowHandle
if ($hwnd -eq [IntPtr]::Zero) { throw 'LumaWall has no main window handle' }
Write-Host ("window handle: " + $hwnd + "  iconic=" + [WinCtl4]::IsIconic($hwnd))

function Capture-TopRight {
    param([string]$Path, [string]$Label)
    # Show and bring forward so the pixels are actually on screen.
    [WinCtl4]::ShowWindow($hwnd, [WinCtl4]::SW_SHOW) | Out-Null
    [WinCtl4]::SetForegroundWindow($hwnd) | Out-Null
    Start-Sleep -Milliseconds 900

    $r = New-Object WinCtl4+RECT
    [WinCtl4]::GetWindowRect($hwnd, [ref]$r) | Out-Null
    $w = $r.Right - $r.Left
    $h = $r.Bottom - $r.Top
    Write-Host ("  {0}: {1}x{2} at {3},{4}" -f $Label, $w, $h, $r.Left, $r.Top)

    $sliceW = [Math]::Min(280, $w)
    $bmp = New-Object System.Drawing.Bitmap($sliceW, 58)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($r.Right - $sliceW, $r.Top, 0, 0, (New-Object System.Drawing.Size($sliceW, 58)))
    $bmp.Save($Path)
    $g.Dispose(); $bmp.Dispose()
    return @{ W = $w; H = $h }
}

Write-Host '=== 1. restored (expect: line / box / X) ==='
[WinCtl4]::ShowWindow($hwnd, [WinCtl4]::SW_RESTORE) | Out-Null
Start-Sleep -Milliseconds 700
$null = Capture-TopRight -Path (Join-Path $out 'controls-restored.png') -Label 'restored'

Write-Host '=== 2. maximized (expect: line / restore-boxes / X) ==='
[WinCtl4]::ShowWindow($hwnd, [WinCtl4]::SW_MAXIMIZE) | Out-Null
Start-Sleep -Milliseconds 700
$null = Capture-TopRight -Path (Join-Path $out 'controls-maximized.png') -Label 'maximized'

# Leave the window restored.
[WinCtl4]::ShowWindow($hwnd, [WinCtl4]::SW_RESTORE) | Out-Null

$a = [System.Drawing.Image]::FromFile((Join-Path $out 'controls-restored.png'))
$b = [System.Drawing.Image]::FromFile((Join-Path $out 'controls-maximized.png'))
# Use -ArgumentList with explicit ints: the bare New-Object form mis-parses the
# arithmetic expression and reports a bogus "argument count: 4".
$sheetW = [int][Math]::Max($a.Width, $b.Width)
$sheetH = [int]($a.Height + $b.Height + 12)
$sheet = New-Object -TypeName System.Drawing.Bitmap -ArgumentList $sheetW, $sheetH
$g2 = [System.Drawing.Graphics]::FromImage($sheet)
$g2.Clear([System.Drawing.Color]::FromArgb(24, 26, 32))
$g2.DrawImage($a, 0, 0)
$g2.DrawImage($b, 0, $a.Height + 12)
$g2.Dispose()
$sheet.Save((Join-Path $out 'controls-compare.png'))
$a.Dispose(); $b.Dispose(); $sheet.Dispose()
Write-Host '  wrote controls-compare.png (top = restored, bottom = maximized)'
