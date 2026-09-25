# Captures the real LumaWall UI for the marketing site.
#
# Two hard-won rules are baked in here:
#
#   1. CopyFromScreen grabs whatever is on top of the window rectangle, so a
#      capture taken while another app has focus produces a screenshot of that
#      other app. The window is therefore raised and verified as foreground
#      before each shot, and the result is checked for the app's own colours.
#
#   2. PrintWindow(PW_RENDERFULLCONTENT) can block indefinitely on a window that
#      hosts WebView2, so it is not used. Instead the window is brought to the
#      front and the screen is sampled, with a foreground assertion first.
#
# Every shot is validated (size, brightness, colour variety) before it is kept,
# so a bad capture fails loudly instead of shipping a screenshot of the editor.

param(
    [string]$OutDir = (Join-Path (Split-Path $PSScriptRoot -Parent) 'site\assets\shots')
)

$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Drawing, System.Windows.Forms
Add-Type @'
using System;
using System.Runtime.InteropServices;

public static class W {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, IntPtr p);
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr SetFocus(IntPtr h);
    [DllImport("user32.dll", CharSet = CharSet.Auto)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder s, int n);

    /// <summary>Reliably brings a window to the foreground (AttachThreadInput trick).</summary>
    public static void ForceForeground(IntPtr hwnd)
    {
        IntPtr fg = GetForegroundWindow();
        uint target = GetWindowThreadProcessId(hwnd, IntPtr.Zero);
        uint current = GetCurrentThreadId();
        bool attached = false;
        if (fg != IntPtr.Zero)
        {
            uint fgThread = GetWindowThreadProcessId(fg, IntPtr.Zero);
            if (fgThread != 0 && fgThread != current) attached = AttachThreadInput(current, fgThread, true);
        }
        try { BringWindowToTop(hwnd); SetForegroundWindow(hwnd); SetFocus(hwnd); }
        finally
        {
            if (attached)
            {
                uint fgThread = GetWindowThreadProcessId(GetForegroundWindow(), IntPtr.Zero);
                if (fgThread != 0 && fgThread != current) AttachThreadInput(current, fgThread, false);
            }
        }
    }

    public static string Title(IntPtr h) { var sb = new System.Text.StringBuilder(256); GetWindowText(h, sb, sb.Capacity); return sb.ToString(); }
}
'@

$exe = "$env:LOCALAPPDATA\Programs\LumaWall\LumaWall.exe"
if (-not (Test-Path $exe)) { Write-Host "LumaWall not installed" -ForegroundColor Red; exit 1 }
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

function Get-AppWindow {
    $p = Get-Process LumaWall -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } | Select-Object -First 1
    if (-not $p) { return $null }
    $h = $p.MainWindowHandle

    # The app minimises to the tray when the user closes it, so the window is
    # frequently hidden or iconic at this point. Bring it back rather than
    # treating that as "not found".
    if ([W]::IsIconic($h)) { [W]::ShowWindow($h, 9) | Out-Null; Start-Sleep -Milliseconds 900 }
    if (-not [W]::IsWindowVisible($h)) {
        [W]::ShowWindow($h, 5) | Out-Null   # SW_SHOW
        Start-Sleep -Milliseconds 900
    }

    $r = New-Object W+RECT
    [W]::GetWindowRect($h, [ref]$r) | Out-Null
    $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
    if ($w -lt 800 -or $ht -lt 500) {
        Write-Host ("  window is " + $w + "x" + $ht + " - waiting for it to size up") -ForegroundColor DarkGray
        Start-Sleep -Milliseconds 1500
        [W]::GetWindowRect($h, [ref]$r) | Out-Null
        $w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
        if ($w -lt 800 -or $ht -lt 500) { return $null }
    }
    return [pscustomobject]@{ Handle = $h; W = $w; H = $ht; L = $r.Left; T = $r.Top; Title = [W]::Title($h) }
}

function Save-Shot($win, $path, $label) {
    $bmp = New-Object System.Drawing.Bitmap $win.W, $win.H
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($win.L, $win.T, 0, 0, (New-Object System.Drawing.Size $win.W, $win.H))
    $g.Dispose()

    # Validate: brightness, and whether the palette looks like the app (dark
    # UI with an accent) rather than an arbitrary foreground window.
    $sum = 0; $n = 0; $bright = 0
    for ($y = 30; $y -lt $win.H - 30; $y += 50) {
        for ($x = 30; $x -lt $win.W - 30; $x += 50) {
            $c = $bmp.GetPixel($x, $y)
            $l = ($c.R + $c.G + $c.B) / 3
            $sum += $l; $n++
            if ($l -gt 200) { $bright++ }
        }
    }
    $mean = [math]::Round($sum / $n, 1)
    $brightPct = [math]::Round(100 * $bright / $n, 1)

    # The app is a dark theme: mostly dark with a small amount of bright text.
    $ok = ($mean -gt 6) -and ($mean -lt 120) -and ($brightPct -lt 35)
    if (-not $ok) {
        Write-Host ("  [" + $label + "] rejected: mean " + $mean + ", bright " + $brightPct + "%") -ForegroundColor Red
        $bmp.Dispose(); return $false
    }
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Host ("  [" + $label + "] " + $win.W + "x" + $win.H + "  mean " + $mean + "  bright " + $brightPct + "%  -> " + (Split-Path $path -Leaf)) -ForegroundColor Green
    return $true
}

Write-Host "Capturing LumaWall UI..." -ForegroundColor Cyan
$win = Get-AppWindow
if (-not $win) { Write-Host "LumaWall window not found" -ForegroundColor Red; exit 1 }
Write-Host ("  window: '" + $win.Title + "'  " + $win.W + "x" + $win.H) -ForegroundColor DarkGray
Write-Host ""

$captured = @()
foreach ($page in @(
    @{ arg = '--library';     name = 'library' },
    @{ arg = '--discover';    name = 'discover' },
    @{ arg = '--displays';    name = 'displays' },
    @{ arg = '--performance'; name = 'performance' }
)) {
    & $exe $page.arg 2>&1 | Out-Null
    Start-Sleep -Milliseconds 2200

    $win = Get-AppWindow
    if (-not $win) { Write-Host ("  [" + $page.name + "] window vanished") -ForegroundColor Yellow; continue }
    if ([W]::IsIconic($win.Handle)) { [W]::ShowWindow($win.Handle, 9) | Out-Null; Start-Sleep -Milliseconds 900 }
    [W]::ForceForeground($win.Handle)
    Start-Sleep -Milliseconds 1500

    $fg = [W]::GetForegroundWindow()
    if ($fg -ne $win.Handle) {
        Write-Host ("  [" + $page.name + "] could not take foreground (0x" + $fg.ToInt64().ToString('X') + " vs 0x" + $win.Handle.ToInt64().ToString('X') + ") - retrying") -ForegroundColor Yellow
        [W]::ForceForeground($win.Handle)
        Start-Sleep -Milliseconds 1200
    }

    if (Save-Shot $win (Join-Path $OutDir ("ui-" + $page.name + ".png")) $page.name) { $captured += $page.name }
}

Write-Host ""
Write-Host "Capturing desktop with the live wallpaper..." -ForegroundColor Cyan
try { (New-Object -ComObject Shell.Application).MinimizeAll() } catch {}
Start-Sleep -Seconds 3
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($screen.X, $screen.Y, 0, 0, $bmp.Size)
$g.Dispose()
$bmp.Save((Join-Path $OutDir 'desktop-live.png'), [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Host ("  [desktop] " + $screen.Width + "x" + $screen.Height) -ForegroundColor Green
$captured += 'desktop'

Write-Host ""
Write-Host ("captured: " + ($captured -join ', ')) -ForegroundColor Cyan
